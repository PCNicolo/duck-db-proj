---

# Natural Language to SQL Chat Interface - Brownfield Enhancement

## Epic Goal
Enable users to query DuckDB data using natural language through a chat interface that generates and displays SQL queries, enhancing the existing analytics dashboard with AI-powered query assistance.

## Epic Description

**Existing System Context:**
- Current functionality: DuckDB Analytics Dashboard with SQL editor, data explorer, and visualizations
- Technology stack: Python, Streamlit, DuckDB, Pandas, Plotly
- Integration points: SQL Editor tab in `app.py`, DuckDB query engine in `src/duckdb_analytics/core/`

**Enhancement Details:**
- What's being added: Natural language chat interface for SQL generation
- How it integrates: New chat component in SQL Editor tab, local LLM for query translation
- Success criteria: Users can describe data needs in plain English and receive executable SQL

## Stories

### Story 1: Add Chat UI Component to SQL Editor
**Brief**: Implement a thin rectangular chat input bar in the SQL Editor tab where users can type natural language queries. The component should display the user's question and the generated SQL response in a clean, readable format.

### Story 2: Integrate Local LLM for SQL Generation
**Brief**: Set up local LLM integration (LM Studio or Hugging Face) with a SQL-optimized model. Create a service that accepts natural language input and DuckDB schema context, returning appropriate SQL queries.

### Story 3: Connect Chat to DuckDB Schema Context
**Brief**: Implement schema extraction from DuckDB to provide table structures to the LLM. Ensure generated SQL is validated against actual tables/columns before display. Add error handling for invalid queries.

## Compatibility Requirements
- [x] Existing SQL editor functionality remains unchanged
- [x] Database operations remain backward compatible
- [x] UI changes follow existing Streamlit patterns
- [x] Performance impact is minimal (local model inference)

## Risk Mitigation
- **Primary Risk:** LLM generates invalid or potentially harmful SQL
- **Mitigation:** SQL validation layer, read-only query enforcement, query preview before execution
- **Rollback Plan:** Chat interface can be disabled via config flag without affecting core functionality

## Definition of Done
- [x] All stories completed with acceptance criteria met
- [x] Existing SQL editor functionality verified through testing
- [x] Chat interface successfully generates SQL for common queries
- [x] Documentation updated with setup instructions for local LLM
- [x] No regression in existing dashboard features

---

## 📋 Story Manager Handoff

**Story Manager Handoff:**

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is an enhancement to an existing Streamlit dashboard running Python/DuckDB
- Integration points: SQL Editor tab in `app.py`, query engine in `src/duckdb_analytics/core/`
- Existing patterns to follow: Streamlit component patterns, current UI layout
- Critical compatibility requirements: Must not break existing SQL editor or query functionality
- Each story must include verification that existing functionality remains intact

The epic should maintain system integrity while delivering natural language SQL query generation."

---

## ✅ Epic Validation Checklist

**Scope Validation:**
- ✅ Epic can be completed in 3 stories maximum
- ✅ No architectural documentation required (using existing patterns)
- ✅ Enhancement follows existing Streamlit/Python patterns
- ✅ Integration complexity is manageable

**Risk Assessment:**
- ✅ Risk to existing system is low (additive feature)
- ✅ Rollback plan is feasible (feature flag)
- ✅ Testing approach covers existing functionality
- ✅ Team has sufficient knowledge of Streamlit/DuckDB

**Completeness Check:**
- ✅ Epic goal is clear and achievable
- ✅ Stories are properly scoped
- ✅ Success criteria are measurable
- ✅ Dependencies identified (local LLM setup)

