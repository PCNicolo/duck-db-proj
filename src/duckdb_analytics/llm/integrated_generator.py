"""
Integrated SQL Generator with Streaming and Advanced Configuration.

This module integrates streaming generation, advanced configuration,
and the existing enhanced SQL generator for a complete solution.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Tuple, Any, Callable
import streamlit as st
from dataclasses import dataclass

from .enhanced_sql_generator import EnhancedSQLGenerator
from .streaming_generator import (
    StreamingSQLGenerator,
    DualStreamCoordinator,
    StreamChunk,
    StreamType
)
from .model_config import (
    ModelConfigManager,
    ModelProfile,
    GenerationMode,
    AdaptiveModelSelector
)

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Result from SQL generation."""
    sql: Optional[str]
    thinking_process: str
    metadata: Dict[str, Any]
    profile_used: str
    generation_time: float
    confidence: float = 0.0
    error: Optional[str] = None


class IntegratedSQLGenerator:
    """
    Unified SQL generator with streaming, configuration, and enhanced features.
    """
    
    def __init__(
        self,
        duckdb_conn,
        base_url: str = "http://localhost:1234/v1",
        enable_streaming: bool = True,
        enable_adaptive: bool = True
    ):
        """
        Initialize integrated SQL generator.
        
        Args:
            duckdb_conn: DuckDB connection
            base_url: LM Studio API endpoint
            enable_streaming: Enable streaming generation
            enable_adaptive: Enable adaptive model selection
        """
        self.duckdb_conn = duckdb_conn
        self.base_url = base_url
        self.enable_streaming = enable_streaming
        self.enable_adaptive = enable_adaptive
        
        # Initialize configuration manager
        self.config_manager = ModelConfigManager()
        
        # Initialize adaptive selector
        self.adaptive_selector = AdaptiveModelSelector(self.config_manager) if enable_adaptive else None
        
        # Initialize enhanced generator (fallback for non-streaming)
        self.enhanced_generator = EnhancedSQLGenerator(
            duckdb_conn=duckdb_conn,
            base_url=base_url
        )
        
        # Initialize streaming generator
        if enable_streaming:
            active_profile = self.config_manager.get_active_profile()
            self.streaming_generator = StreamingSQLGenerator(
                base_url=base_url,
                model=active_profile.model_id if active_profile else "meta-llama-3.1-8b-instruct",
                profile="balanced"
            )
            self.dual_coordinator = DualStreamCoordinator(self.streaming_generator)
        else:
            self.streaming_generator = None
            self.dual_coordinator = None
        
        # Session metrics
        self.generation_count = 0
        self.total_generation_time = 0.0
        self.cache_hits = 0
    
    def generate_sql(
        self,
        natural_language_query: str,
        mode: Optional[GenerationMode] = None,
        stream_callback: Optional[Callable] = None
    ) -> GenerationResult:
        """
        Generate SQL with optimal configuration.
        
        Args:
            natural_language_query: User's query
            mode: Force specific generation mode
            stream_callback: Callback for streaming updates
            
        Returns:
            GenerationResult with SQL and metadata
        """
        start_time = time.time()
        
        # Select profile based on query or mode
        if mode:
            # Find profile matching mode
            profile = self._get_profile_for_mode(mode)
        elif self.enable_adaptive:
            # Adaptive selection based on query
            schema = self.enhanced_generator.schema_extractor.extract_schema_optimized()
            profile = self.adaptive_selector.select_profile(
                natural_language_query,
                len(schema)
            )
        else:
            # Use active profile
            profile = self.config_manager.get_active_profile()
        
        if not profile:
            # Fallback to default
            profile = self.config_manager.profiles.get("lm_studio_default")
        
        # Apply profile to enhanced generator
        self._apply_profile_to_generator(profile)
        
        # Generate SQL based on streaming preference
        if self.enable_streaming and stream_callback:
            result = self._generate_with_streaming(
                natural_language_query,
                profile,
                stream_callback
            )
        else:
            result = self._generate_traditional(
                natural_language_query,
                profile
            )
        
        # Update metrics
        self.generation_count += 1
        generation_time = time.time() - start_time
        self.total_generation_time += generation_time
        
        # Add timing to result
        result.generation_time = generation_time
        result.profile_used = profile.name
        
        return result
    
    def _generate_traditional(
        self,
        query: str,
        profile: ModelProfile
    ) -> GenerationResult:
        """Generate SQL using traditional (non-streaming) method."""
        try:
            # Use enhanced generator with explanation
            sql, metadata = self.enhanced_generator.generate_sql_with_explanation(
                natural_language_query=query,
                context_level=profile.thinking_depth,
                return_metrics=True,
                include_llm_feedback=profile.use_self_reflection
            )
            
            # Extract thinking process from explanation
            thinking_process = ""
            if "explanation" in metadata and isinstance(metadata["explanation"], dict):
                thinking_process = metadata["explanation"].get("explanation", "")
                confidence = metadata["explanation"].get("confidence", 0.5)
            else:
                confidence = 0.5
            
            return GenerationResult(
                sql=sql,
                thinking_process=thinking_process,
                metadata=metadata,
                profile_used=profile.name,
                generation_time=0.0,  # Will be set by caller
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Traditional generation failed: {e}")
            return GenerationResult(
                sql=None,
                thinking_process=f"Error during generation: {str(e)}",
                metadata={},
                profile_used=profile.name,
                generation_time=0.0,
                error=str(e)
            )
    
    def _generate_with_streaming(
        self,
        query: str,
        profile: ModelProfile,
        stream_callback: Callable
    ) -> GenerationResult:
        """Generate SQL with streaming."""
        try:
            # Get schema for context
            schema = self.enhanced_generator.schema_extractor.extract_schema_optimized()
            
            # Create async event loop if not exists
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run streaming generation with proper task cleanup
            try:
                result = loop.run_until_complete(
                    self._async_streaming_generate(
                        query,
                        schema,
                        profile,
                        stream_callback
                    )
                )
            finally:
                # Cancel any remaining tasks to prevent warnings
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    if not task.done():
                        task.cancel()
                # Wait for tasks to be cancelled
                if pending:
                    loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            
            return result
            
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            # Fallback to traditional generation
            return self._generate_traditional(query, profile)
    
    async def _async_streaming_generate(
        self,
        query: str,
        schema: Dict,
        profile: ModelProfile,
        stream_callback: Callable
    ) -> GenerationResult:
        """Async streaming generation."""
        thinking_parts = []
        sql_parts = []
        metadata = {}
        
        try:
            # Configure streaming generator with profile
            self.streaming_generator.profile = self._profile_to_streaming_profile(profile)
            
            # Generate with streaming
            async for chunk in self.streaming_generator.generate_with_streaming(
                natural_language_query=query,
                schema_context=schema,
                system_prompt=self._get_system_prompt(profile)
            ):
                # Process chunk
                if chunk.type == StreamType.THINKING:
                    thinking_parts.append(chunk.content)
                    stream_callback({
                        "type": "thinking",
                        "content": chunk.content,
                        "metadata": chunk.metadata
                    })
                    
                elif chunk.type == StreamType.SQL:
                    sql_parts.append(chunk.content)
                    stream_callback({
                        "type": "sql",
                        "content": chunk.content,
                        "metadata": chunk.metadata
                    })
                    
                elif chunk.type == StreamType.COMPLETE:
                    metadata = chunk.metadata or {}
                    stream_callback({
                        "type": "complete",
                        "content": chunk.content,
                        "metadata": metadata
                    })
                    
                elif chunk.type == StreamType.ERROR:
                    raise Exception(chunk.content)
            
            # Combine results
            thinking_process = "\n".join(thinking_parts)
            sql = "".join(sql_parts).strip()
            
            # Calculate confidence based on generation
            confidence = self._calculate_confidence(sql, thinking_process, metadata)
            
            return GenerationResult(
                sql=sql,
                thinking_process=thinking_process,
                metadata=metadata,
                profile_used=profile.name,
                generation_time=0.0,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Async streaming failed: {e}")
            return GenerationResult(
                sql=None,
                thinking_process=f"Streaming error: {str(e)}",
                metadata={},
                profile_used=profile.name,
                generation_time=0.0,
                error=str(e)
            )
    
    def _apply_profile_to_generator(self, profile: ModelProfile):
        """Apply profile settings to enhanced generator."""
        if not self.enhanced_generator:
            return
        
        # Update generator settings
        self.enhanced_generator.model = profile.model_id
        
        # Update query explainer settings
        if hasattr(self.enhanced_generator, 'query_explainer'):
            explainer = self.enhanced_generator.query_explainer
            # Configure based on profile
            explainer.cache_size = 100 if profile.cache_similar_queries else 0
    
    def _get_profile_for_mode(self, mode: GenerationMode) -> Optional[ModelProfile]:
        """Get profile matching a generation mode."""
        # Map mode to thinking depth
        depth_map = {
            GenerationMode.FAST: "minimal",
            GenerationMode.BALANCED: "standard",
            GenerationMode.THOROUGH: "comprehensive",
            GenerationMode.CREATIVE: "comprehensive",
            GenerationMode.PRECISE: "standard"
        }
        
        target_depth = depth_map.get(mode, "standard")
        
        # Find matching profile
        for name, profile in self.config_manager.profiles.items():
            if profile.thinking_depth == target_depth:
                return profile
        
        return None
    
    def _profile_to_streaming_profile(self, profile: ModelProfile) -> str:
        """Convert ModelProfile to streaming profile name."""
        if profile.thinking_depth == "minimal":
            return "fast"
        elif profile.thinking_depth == "comprehensive":
            return "thorough"
        else:
            return "balanced"
    
    def _get_system_prompt(self, profile: ModelProfile) -> str:
        """Get system prompt based on profile."""
        from .config import SQL_SYSTEM_PROMPT
        
        # Enhance prompt based on profile settings
        prompt = SQL_SYSTEM_PROMPT
        
        if profile.use_chain_of_thought:
            prompt += "\n\n## Chain of Thought\nExplain your reasoning step by step before generating SQL."
        
        if profile.show_alternatives:
            prompt += "\n\n## Alternatives\nConsider alternative approaches and explain why you chose this one."
        
        if profile.show_optimization_notes:
            prompt += "\n\n## Optimization\nNote any performance optimizations applied to the query."
        
        # Add few-shot examples if available
        if profile.use_few_shot and profile.few_shot_examples:
            prompt += "\n\n## Examples\n"
            for example in profile.few_shot_examples[:3]:  # Limit to 3 examples
                prompt += f"Query: {example['query']}\nSQL: {example['sql']}\n\n"
        
        return prompt
    
    def _calculate_confidence(
        self,
        sql: str,
        thinking_process: str,
        metadata: Dict
    ) -> float:
        """Calculate confidence score for generation."""
        confidence = 0.5  # Base confidence
        
        # Factors that increase confidence
        if sql and len(sql) > 10:
            confidence += 0.1
        
        if thinking_process and len(thinking_process) > 100:
            confidence += 0.1
        
        if metadata.get("thinking_stages"):
            confidence += 0.1
        
        # Check SQL complexity
        sql_lower = sql.lower() if sql else ""
        if "select" in sql_lower and "from" in sql_lower:
            confidence += 0.1
        
        if "join" not in sql_lower:  # Simpler queries are more confident
            confidence += 0.1
        
        # Cap at 1.0
        return min(confidence, 1.0)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get generation metrics."""
        avg_time = (
            self.total_generation_time / self.generation_count
            if self.generation_count > 0
            else 0
        )
        
        return {
            "total_generations": self.generation_count,
            "average_generation_time": avg_time,
            "cache_hit_rate": (
                self.cache_hits / self.generation_count
                if self.generation_count > 0
                else 0
            ),
            "streaming_enabled": self.enable_streaming,
            "adaptive_enabled": self.enable_adaptive,
            "active_profile": (
                self.config_manager.active_profile
                if self.config_manager
                else None
            )
        }
    
    def optimize_for_current_session(self):
        """Optimize settings based on current session metrics."""
        metrics = self.get_metrics()
        
        # If average generation time is too high, optimize for latency
        if metrics["average_generation_time"] > 10.0:
            logger.info("High latency detected, optimizing for speed...")
            if self.config_manager.active_profile:
                self.config_manager.optimize_for_latency(
                    self.config_manager.active_profile
                )
        
        # If cache hit rate is high, we can afford more quality
        elif metrics["cache_hit_rate"] > 0.5:
            logger.info("High cache hit rate, optimizing for quality...")
            if self.config_manager.active_profile:
                self.config_manager.optimize_for_quality(
                    self.config_manager.active_profile
                )