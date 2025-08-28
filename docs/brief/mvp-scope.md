# MVP Scope

## Core Features (Must Have)
- **Chat Interface:** Natural language query input with SQL generation and explanation
- **DuckDB Integration:** Full DuckDB engine with support for CSV, Parquet, and JSON files
- **Data Import:** Drag-and-drop file import with automatic schema detection
- **Basic Visualizations:** Table views, basic charts (line, bar, scatter, pie)
- **Query History:** Searchable history with ability to re-run and modify past queries
- **Export Capabilities:** Export results to CSV, JSON, or clipboard
- **Local LLM Integration:** Offline-capable language model for query translation

## Out of Scope for MVP
- Team collaboration features
- Cloud storage integrations
- Advanced statistical functions
- Custom visualization builders
- Scheduled or automated queries
- Database connections (PostgreSQL, MySQL, etc.)
- Mobile applications
- Plugin system

## MVP Success Criteria

The MVP will be considered successful when:
- 100 beta users complete at least 10 queries each
- 85% success rate in natural language to SQL translation
- Zero data leaves the local machine during operation
- Application runs smoothly on machines with 8GB RAM
- Core workflow (import → query → visualize → export) takes under 5 minutes
