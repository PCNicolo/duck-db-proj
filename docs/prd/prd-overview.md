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

## Epics

- [Epic 1: DuckDB Analytics Dashboard System Optimization](epic-1-system-optimization.md)

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