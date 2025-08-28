
---

# DuckDB Analytics Dashboard Optimization - Product Requirements Document (PRD)

## Goals and Background Context

### Goals
- **Enhance LM-Studio Integration**: Improve schema context and prompt engineering for better SQL generation accuracy
- **Fix Critical Bugs**: Resolve NoneType error when copying queries to editor
- **Optimize UI/UX**: Clean up SQL editor interface for better usability
- **Improve Tab Functionality**: Optimize Analytics, Visualizations, and Data Explorer tabs for project purpose
- **System Performance**: Streamline SQL query execution and result processing
- **Developer Experience**: Make debugging and troubleshooting easier

### Background Context

The DuckDB Analytics Dashboard is a Streamlit-based application that enables users to analyze CSV and Parquet files using natural language queries converted to SQL via LM-Studio integration. While the core functionality works, several optimization opportunities exist to improve reliability, usability, and performance. These enhancements focus on fixing existing bugs, improving the AI integration context, and optimizing the user interface for better workflow efficiency.

### Change Log
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Dec 2024 | PM Agent | Initial brownfield PRD for system optimization |

## Existing System Analysis

### Current Technology Stack
- **Frontend**: Streamlit (Python web framework)
- **Database**: DuckDB (embedded analytical database)
- **AI Integration**: LM-Studio (local LLM for SQL generation)
- **APIs**: OpenAI client library for LM-Studio communication
- **File Processing**: CSV and Parquet file support
- **Dependencies**: pandas, httpx, plotly for visualizations

### Current System Capabilities
- Natural language to SQL conversion via LM-Studio
- Schema extraction and formatting for LLM context
- SQL query execution with result caching
- File upload and registration as DuckDB tables
- Multiple UI tabs for different analytics workflows
- Chat-based interaction history

### Known Issues and Pain Points
1. **NoneType Error**: Copy-to-editor functionality fails with "'NoneType' object has no attribute 'df'"
2. **Limited Schema Context**: LM-Studio receives insufficient schema information for accurate SQL generation
3. **UI Clutter**: SQL editor interface needs cleanup and better organization
4. **Tab Optimization**: Analytics, Visualizations, and Data Explorer tabs not fully optimized for use cases
5. **Error Handling**: Inadequate error messages and debugging information

## Epic Approach

**Epic Structure Decision**: Single epic for system-wide optimizations with logically sequenced stories to minimize risk to the existing system. Each story will be self-contained with clear rollback procedures.

## Epic 1: DuckDB Analytics Dashboard System Optimization

**Epic Goal**: Enhance the overall system reliability, usability, and performance while maintaining all existing functionality and ensuring backward compatibility.

**Integration Requirements**: All changes must maintain compatibility with existing data files, preserve chat history functionality, and ensure no regression in current features.

### Story 1.1: Fix NoneType Error in Copy-to-Editor Functionality

**As a** data analyst,
**I want** the copy-to-editor button to work reliably,
**so that** I can easily transfer generated SQL queries to the editor for modification.

**Acceptance Criteria:**
1. Investigate root cause of NoneType error in query result handling
2. Implement proper null checking and error handling
3. Ensure query results are properly stored in session state
4. Add fallback mechanism for missing dataframe references
5. Display user-friendly error messages when issues occur

**Integration Verification:**
- IV1: Existing SQL execution flow remains unchanged
- IV2: Session state management doesn't break other features
- IV3: Performance impact is negligible (<100ms added latency)

**Technical Notes:**
- Check `st.session_state` management for query results
- Verify dataframe initialization in query execution path
- Add defensive programming patterns throughout

### Story 1.2: Enhance LM-Studio Context and Prompt Engineering

**As a** user writing natural language queries,
**I want** the LLM to receive comprehensive schema context,
**so that** it generates more accurate SQL queries on first attempt.

**Acceptance Criteria:**
1. Enhance schema extraction to include:
   - Column data types and constraints
   - Sample data values (configurable)
   - Table relationships and foreign keys
   - Row counts and statistics
2. Optimize prompt template in `SQL_SYSTEM_PROMPT`
3. Implement context window management (max tokens)
4. Add schema caching with smart invalidation
5. Include query validation against actual schema

**Integration Verification:**
- IV1: Existing SQL generation endpoint remains compatible
- IV2: Schema extraction doesn't impact query performance
- IV3: Cache invalidation works correctly on table changes

**Technical Implementation:**
- Enhance `SchemaExtractor.format_for_llm()` method
- Implement intelligent context truncation for large schemas
- Add configuration for context detail level

### Story 1.3: Optimize SQL Query Execution Pipeline

**As a** user executing SQL queries,
**I want** faster and more reliable query processing,
**so that** I get results quickly with clear feedback on issues.

**Acceptance Criteria:**
1. Implement query result streaming for large datasets
2. Add progress indicators for long-running queries
3. Improve error handling with actionable messages
4. Optimize result caching strategy
5. Add query execution metrics and logging

**Integration Verification:**
- IV1: All existing query types continue to work
- IV2: Cache functionality remains backward compatible
- IV3: No regression in query execution times

### Story 1.4: SQL Editor UI Cleanup and Enhancement

**As a** SQL developer,
**I want** a clean and efficient SQL editor interface,
**so that** I can write and modify queries productively.

**Acceptance Criteria:**
1. Reorganize SQL editor layout for better space utilization
2. Add syntax highlighting for SQL code
3. Implement query history with quick access
4. Add keyboard shortcuts for common actions
5. Create collapsible sections for schema viewer
6. Improve copy/paste functionality
7. Add query formatting/beautification option

**Integration Verification:**
- IV1: Existing query submission flow unchanged
- IV2: Chat history display remains functional
- IV3: All current editor features still accessible

### Story 1.5: Optimize Analytics Tab Functionality

**As a** data analyst,
**I want** the Analytics tab to provide meaningful insights quickly,
**so that** I can understand my data without writing SQL.

**Acceptance Criteria:**
1. Add pre-built analytics templates for common analyses
2. Implement smart summary statistics based on data types
3. Add data profiling capabilities
4. Create interactive filter/aggregation builder
5. Optimize performance for large datasets

**Integration Verification:**
- IV1: Existing analytics functions continue working
- IV2: Tab switching doesn't lose state
- IV3: Query engine integration remains stable

### Story 1.6: Enhance Visualizations Tab

**As a** user analyzing data,
**I want** better visualization options and controls,
**so that** I can create meaningful charts from query results.

**Acceptance Criteria:**
1. Add more chart types (heatmaps, treemaps, etc.)
2. Implement smart chart type recommendations
3. Add interactive chart configuration panel
4. Enable chart export in multiple formats
5. Implement dashboard-style multi-chart layouts

**Integration Verification:**
- IV1: Existing Plotly integrations remain functional
- IV2: Chart rendering performance maintained
- IV3: Data pipeline to charts unchanged

### Story 1.7: Improve Data Explorer Tab

**As a** user exploring datasets,
**I want** an intuitive data exploration interface,
**so that** I can quickly understand table contents and relationships.

**Acceptance Criteria:**
1. Add advanced filtering UI with multiple conditions
2. Implement column-level search and filtering
3. Add data export with format options
4. Create table relationship visualizer
5. Implement pagination for large tables

**Integration Verification:**
- IV1: Existing table display functionality preserved
- IV2: DuckDB query generation remains compatible
- IV3: Performance acceptable for large datasets

## Technical Considerations

### Performance Requirements
- SQL generation response time < 3 seconds
- Query execution for 100K rows < 2 seconds
- UI interactions respond within 200ms
- Schema caching reduces repeated extraction by 80%

### Security Considerations
- Sanitize all SQL inputs to prevent injection
- Validate file paths for security
- Implement query timeout limits
- Add rate limiting for LM-Studio requests

### Testing Strategy
- Unit tests for each modified function
- Integration tests for story workflows
- Performance benchmarks before/after
- User acceptance testing for UI changes

## Risk Mitigation Strategy

### Primary Risks
1. **Breaking existing functionality during refactoring**
   - Mitigation: Comprehensive test coverage, feature flags for new functionality
   - Rollback: Git-based version control with tagged releases

2. **Performance degradation from new features**
   - Mitigation: Performance testing, profiling, and optimization
   - Rollback: Configuration flags to disable new features

3. **LM-Studio compatibility issues**
   - Mitigation: Version pinning, fallback to basic prompts
   - Rollback: Keep original prompt templates available

## Success Metrics
- NoneType error occurrence reduced to 0%
- SQL generation accuracy improved by 30%
- Average query execution time reduced by 25%
- User satisfaction score increased (via feedback)
- 90% of queries succeed on first attempt

## Implementation Notes

### Development Approach
- Implement stories sequentially to minimize risk
- Each story should be independently deployable
- Maintain backward compatibility throughout
- Use feature flags for gradual rollout
- Document all changes in changelog

### Dependencies
- No new major dependencies required
- Consider adding `sqlparse` for SQL formatting
- May need `streamlit-ace` for better code editing

## Next Steps

1. **Review and approve this PRD** - Confirm the epic structure and story sequence
2. **Create technical architecture** if needed for complex integrations
3. **Begin story implementation** starting with Story 1.1 (NoneType fix)
4. **Set up testing environment** with sample data
5. **Establish rollback procedures** for each story

---

