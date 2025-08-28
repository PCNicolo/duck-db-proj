# Frontend Tech Stack

## Technology Stack Table

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| Framework | Streamlit | 1.29+ | Web UI framework | Python-native, ideal for data apps, existing implementation |
| UI Library | Streamlit Components | Built-in | UI widgets and layouts | Native components optimized for data visualization |
| State Management | st.session_state | Built-in | Session data persistence | Streamlit's native state management system |
| Routing | Streamlit Pages | Built-in | Multi-page navigation | Native page routing via file structure |
| Build Tool | Python/pip | 3.11+ | Package management | Standard Python tooling, no JS bundler needed |
| Styling | Streamlit Theme + Custom CSS | Built-in | Visual customization | Theme config + CSS injection for branding |
| Testing | pytest + Streamlit Testing | 7.0+ | Unit and integration tests | Python testing framework with Streamlit test utilities |
| Component Library | streamlit-extras | Latest | Extended components | Additional UI components beyond core Streamlit |
| Form Handling | Streamlit Forms | Built-in | User input collection | Native form submission with batched updates |
| Animation | CSS Animations | CSS3 | UI transitions | Limited animation via custom CSS |
| Dev Tools | Streamlit CLI | Built-in | Development server | Hot reload development server |
