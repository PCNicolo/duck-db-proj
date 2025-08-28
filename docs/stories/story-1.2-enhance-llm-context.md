# Story 1.2: Enhance LM-Studio Context and Prompt Engineering

**Status**: ✅ READY FOR DEVELOPMENT  
**Epic**: Epic 1 - System Optimization  
**Priority**: HIGH  
**Estimated Points**: 5  

## User Story

**As a** user writing natural language queries,  
**I want** the LLM to receive comprehensive schema context,  
**So that** it generates more accurate SQL queries on first attempt.

## Background & Context

The current LLM integration provides basic schema information, resulting in suboptimal SQL generation that often requires multiple attempts. By enhancing the context provided to the LLM, we can significantly improve first-attempt accuracy and user satisfaction.

## Acceptance Criteria

- [ ] Schema extraction includes column data types and constraints
- [ ] Sample data values are provided (configurable number of samples)
- [ ] Table relationships and foreign keys are included in context
- [ ] Row counts and basic statistics are provided
- [ ] SQL_SYSTEM_PROMPT template is optimized for better results
- [ ] Context window management prevents token overflow
- [ ] Schema caching reduces redundant processing
- [ ] Query validation against actual schema is implemented

## Technical Tasks

### 1. Enhance Schema Extraction
- [ ] Modify `SchemaExtractor` class to gather comprehensive metadata
- [ ] Extract column data types, constraints, and nullable flags
- [ ] Identify and document foreign key relationships
- [ ] Gather table statistics (row counts, cardinality)
- [ ] Implement sample data extraction with configurable limits

### 2. Optimize Prompt Engineering
- [ ] Review and enhance `SQL_SYSTEM_PROMPT` template
- [ ] Add examples of common query patterns
- [ ] Include schema context formatting guidelines
- [ ] Implement dynamic prompt construction based on query type
- [ ] Add query validation instructions to prompt

### 3. Implement Context Window Management
- [ ] Calculate token usage for schema information
- [ ] Implement intelligent truncation for large schemas
- [ ] Prioritize most relevant tables based on query context
- [ ] Add configuration for max context tokens
- [ ] Implement context compression strategies

### 4. Add Schema Caching
- [ ] Design cache key structure (database + tables hash)
- [ ] Implement in-memory schema cache
- [ ] Add cache invalidation on table modifications
- [ ] Implement TTL-based cache expiration
- [ ] Add cache warming on application startup

### 5. Query Validation System
- [ ] Parse generated SQL for table/column references
- [ ] Validate against actual schema before execution
- [ ] Provide helpful error messages for schema mismatches
- [ ] Suggest corrections for common mistakes
- [ ] Log validation results for analysis

### 6. Configuration Management
- [ ] Add settings for sample data row count
- [ ] Configure context detail levels (minimal/standard/comprehensive)
- [ ] Add toggle for schema caching
- [ ] Configure max tokens for context
- [ ] Add debug mode for prompt inspection

## Integration Verification

- [ ] **IV1**: Existing SQL generation endpoint remains compatible
- [ ] **IV2**: Schema extraction doesn't impact query performance
- [ ] **IV3**: Cache invalidation works correctly on table changes
- [ ] **IV4**: LLM API calls remain within rate limits
- [ ] **IV5**: Backward compatibility with existing queries

## Technical Implementation Notes

### Key Components to Modify

```python
# SchemaExtractor enhancements
class SchemaExtractor:
    def format_for_llm(self):
        # Include:
        # - Column types and constraints
        # - Sample data (configurable rows)
        # - Foreign key relationships
        # - Table statistics
        # - Indexes and performance hints
        pass
```

### Context Structure Example

```yaml
tables:
  users:
    columns:
      - name: id
        type: INTEGER
        constraints: PRIMARY KEY, NOT NULL
      - name: email
        type: VARCHAR(255)
        constraints: UNIQUE, NOT NULL
    sample_data:
      - [1, "user@example.com"]
      - [2, "admin@example.com"]
    statistics:
      row_count: 10000
      avg_row_size: 256
    relationships:
      - foreign_key: orders.user_id -> users.id
```

### Caching Strategy

1. Cache key: `hash(database_name + table_list + modification_times)`
2. Cache storage: In-memory with optional Redis backing
3. Invalidation: On DDL operations or manual refresh
4. TTL: Configurable, default 1 hour

## Definition of Done

- [ ] All acceptance criteria met
- [ ] SQL generation accuracy improved by >30%
- [ ] Context token usage optimized and documented
- [ ] Cache hit ratio >80% in normal operation
- [ ] Unit tests for all new functionality
- [ ] Integration tests with LM-Studio
- [ ] Performance benchmarks documented
- [ ] Configuration guide created

## Dependencies

- LM-Studio API documentation
- DuckDB metadata query capabilities
- Token counting library for context management
- Existing SQL generation pipeline

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Token limit exceeded | HIGH | Implement smart truncation and prioritization |
| Cache invalidation complexity | MEDIUM | Conservative TTL and manual refresh option |
| Performance overhead | MEDIUM | Asynchronous schema extraction |
| LLM API changes | LOW | Abstract LLM interface for flexibility |

---
**Story Validated**: ✅ Ready for Development