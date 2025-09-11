"""
Streaming SQL Generator with Real-Time Thinking Pad.

This module provides real-time streaming of both LLM thinking process
and SQL generation for improved user experience and reduced perceived latency.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterator, Dict, Optional, Tuple, Any
from queue import Queue
import threading

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class StreamType(Enum):
    """Types of content being streamed."""
    THINKING = "thinking"
    SQL = "sql"
    VALIDATION = "validation"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class StreamChunk:
    """A chunk of streamed content."""
    type: StreamType
    content: str
    metadata: Dict[str, Any] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.metadata is None:
            self.metadata = {}


class ThinkingStages:
    """Manages the stages of LLM thinking process."""
    
    STAGES = [
        ("understanding", "🎯 Understanding your request", 0.1),
        ("analyzing_schema", "📊 Analyzing database schema", 0.2),
        ("identifying_tables", "🔍 Identifying relevant tables", 0.3),
        ("building_query", "🛠️ Building query structure", 0.5),
        ("adding_filters", "🔧 Adding filters and conditions", 0.6),
        ("optimizing", "⚡ Optimizing query performance", 0.8),
        ("validating", "✅ Validating SQL syntax", 0.9),
        ("complete", "🎉 Query ready", 1.0)
    ]
    
    def __init__(self):
        self.current_stage = 0
        self.stage_content = {}
    
    def get_current_stage(self) -> Tuple[str, str, float]:
        """Get current stage info."""
        if self.current_stage < len(self.STAGES):
            return self.STAGES[self.current_stage]
        return self.STAGES[-1]
    
    def advance(self, content: str = "") -> StreamChunk:
        """Advance to next stage."""
        stage_id, stage_label, progress = self.get_current_stage()
        
        chunk = StreamChunk(
            type=StreamType.THINKING,
            content=f"{stage_label}\n{content}" if content else stage_label,
            metadata={
                "stage": stage_id,
                "progress": progress,
                "stage_number": self.current_stage + 1,
                "total_stages": len(self.STAGES)
            }
        )
        
        self.stage_content[stage_id] = content
        self.current_stage = min(self.current_stage + 1, len(self.STAGES) - 1)
        
        return chunk


class StreamingSQLGenerator:
    """
    Generates SQL with real-time streaming of thinking process and SQL construction.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        model: str = "meta-llama-3.1-8b-instruct",
        profile: str = "balanced"
    ):
        """
        Initialize streaming SQL generator.
        
        Args:
            base_url: LM Studio API endpoint
            model: Model identifier
            profile: Configuration profile (fast/balanced/thorough)
        """
        self.base_url = base_url
        self.model = model
        self.profile = profile
        
        # Async client for streaming
        self.async_client = AsyncOpenAI(
            base_url=base_url,
            api_key="not-needed"
        )
        
        # Configuration profiles
        self.profiles = {
            "fast": {
                "temperature": 0.1,
                "max_tokens": 500,
                "timeout": 3.0,
                "thinking_depth": "minimal",
                "stream_delay": 0.05  # 50ms between chunks
            },
            "balanced": {
                "temperature": 0.3,
                "max_tokens": 1500,
                "timeout": 8.0,
                "thinking_depth": "standard",
                "stream_delay": 0.1  # 100ms between chunks
            },
            "thorough": {
                "temperature": 0.5,
                "max_tokens": 3000,
                "timeout": 15.0,
                "thinking_depth": "comprehensive",
                "stream_delay": 0.15  # 150ms between chunks
            }
        }
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self.profiles.get(self.profile, self.profiles["balanced"])
    
    async def generate_with_streaming(
        self,
        natural_language_query: str,
        schema_context: Dict[str, Any],
        system_prompt: str
    ) -> AsyncIterator[StreamChunk]:
        """
        Generate SQL with streaming thinking pad and SQL construction.
        
        Args:
            natural_language_query: User's natural language query
            schema_context: Database schema information
            system_prompt: System prompt for SQL generation
            
        Yields:
            StreamChunk objects with thinking or SQL content
        """
        config = self.get_config()
        thinking_stages = ThinkingStages()
        
        try:
            # Start with understanding stage
            yield thinking_stages.advance(f"Query: '{natural_language_query}'")
            await asyncio.sleep(config["stream_delay"])
            
            # Analyze schema
            table_names = list(schema_context.keys())[:5]  # Show first 5 tables
            schema_summary = f"Found {len(schema_context)} tables: {', '.join(table_names)}"
            yield thinking_stages.advance(schema_summary)
            await asyncio.sleep(config["stream_delay"])
            
            # Build enhanced prompt for streaming
            streaming_prompt = self._build_streaming_prompt(
                natural_language_query,
                schema_context,
                system_prompt,
                config["thinking_depth"]
            )
            
            # Start SQL generation with streaming
            response_stream = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": streaming_prompt},
                    {"role": "user", "content": natural_language_query}
                ],
                max_tokens=config["max_tokens"],
                temperature=config["temperature"],
                stream=True
            )
            
            # Process streaming response
            sql_buffer = []
            current_section = "thinking"
            
            async for chunk in response_stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    
                    # Detect section transitions
                    if "```sql" in content.lower():
                        current_section = "sql"
                        # Advance to building query stage
                        yield thinking_stages.advance("Starting SQL construction...")
                        continue
                    elif "```" in content and current_section == "sql":
                        current_section = "complete"
                        continue
                    
                    # Stream appropriate content
                    if current_section == "thinking":
                        # Parse thinking content for stage advancement
                        if any(keyword in content.lower() for keyword in ["filter", "where"]):
                            yield thinking_stages.advance(content)
                        elif any(keyword in content.lower() for keyword in ["join", "combine"]):
                            yield thinking_stages.advance(content)
                    elif current_section == "sql":
                        sql_buffer.append(content)
                        yield StreamChunk(
                            type=StreamType.SQL,
                            content=content,
                            metadata={"partial": True}
                        )
                    
                    await asyncio.sleep(config["stream_delay"] / 2)  # Faster for SQL chunks
            
            # Final validation stage
            yield thinking_stages.advance("Query generation complete!")
            
            # Send complete SQL
            complete_sql = ''.join(sql_buffer).strip()
            yield StreamChunk(
                type=StreamType.COMPLETE,
                content=complete_sql,
                metadata={
                    "thinking_stages": thinking_stages.stage_content,
                    "generation_time": time.time()
                }
            )
            
        except Exception as e:
            logger.error(f"Streaming generation error: {str(e)}")
            yield StreamChunk(
                type=StreamType.ERROR,
                content=str(e),
                metadata={"error_type": type(e).__name__}
            )
        finally:
            # Ensure any pending async operations are properly handled
            # (Do not close client as it may be reused)
            pass
    
    def _build_streaming_prompt(
        self,
        query: str,
        schema: Dict[str, Any],
        base_prompt: str,
        thinking_depth: str
    ) -> str:
        """Build prompt optimized for streaming generation."""
        
        depth_instructions = {
            "minimal": "Briefly explain your approach, then generate SQL.",
            "standard": "Explain your thinking process step by step, then generate SQL.",
            "comprehensive": "Provide detailed reasoning for each decision, explain alternatives considered, then generate optimized SQL."
        }
        
        prompt = f"""{base_prompt}

## Streaming Instructions
{depth_instructions.get(thinking_depth, depth_instructions["standard"])}

First, explain your thinking process for this query.
Then, generate the SQL query wrapped in ```sql``` tags.

## Schema Information
{self._format_schema_for_prompt(schema)}

## Query
{query}
"""
        return prompt
    
    def _format_schema_for_prompt(self, schema: Dict[str, Any]) -> str:
        """Format schema information for the prompt."""
        lines = []
        for table_name, table_info in list(schema.items())[:10]:  # Limit to 10 tables
            lines.append(f"Table: {table_name}")
            if hasattr(table_info, 'columns'):
                cols = [f"  - {col.name} ({col.type})" for col in table_info.columns[:5]]
                lines.extend(cols)
                if len(table_info.columns) > 5:
                    lines.append(f"  ... and {len(table_info.columns) - 5} more columns")
        return '\n'.join(lines)


class DualStreamCoordinator:
    """
    Coordinates dual streaming of thinking pad and SQL generation
    for optimal user experience.
    """
    
    def __init__(self, generator: StreamingSQLGenerator):
        self.generator = generator
        self.thinking_queue = Queue()
        self.sql_queue = Queue()
        self.background_task = None
        
    async def dual_stream_generate(
        self,
        natural_language_query: str,
        schema_context: Dict[str, Any],
        system_prompt: str
    ) -> Tuple[Queue, Queue]:
        """
        Generate with dual streaming queues.
        
        Returns:
            Tuple of (thinking_queue, sql_queue)
        """
        # Start streaming in background with proper task tracking
        self.background_task = asyncio.create_task(
            self._stream_worker(
                natural_language_query,
                schema_context,
                system_prompt
            )
        )
        
        return self.thinking_queue, self.sql_queue
    
    async def _stream_worker(
        self,
        query: str,
        schema: Dict[str, Any],
        prompt: str
    ):
        """Background worker for streaming."""
        try:
            async for chunk in self.generator.generate_with_streaming(query, schema, prompt):
                if chunk.type == StreamType.THINKING:
                    self.thinking_queue.put(chunk)
                elif chunk.type == StreamType.SQL:
                    self.sql_queue.put(chunk)
                elif chunk.type == StreamType.COMPLETE:
                    # Signal completion to both queues
                    self.thinking_queue.put(chunk)
                    self.sql_queue.put(chunk)
                elif chunk.type == StreamType.ERROR:
                    # Send error to both queues
                    self.thinking_queue.put(chunk)
                    self.sql_queue.put(chunk)
        except Exception as e:
            error_chunk = StreamChunk(
                type=StreamType.ERROR,
                content=str(e)
            )
            self.thinking_queue.put(error_chunk)
            self.sql_queue.put(error_chunk)
    
    def cleanup(self):
        """Clean up background tasks."""
        if self.background_task and not self.background_task.done():
            self.background_task.cancel()
    
    def __del__(self):
        """Ensure cleanup on destruction."""
        try:
            self.cleanup()
        except:
            pass