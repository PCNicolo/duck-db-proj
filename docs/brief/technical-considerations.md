# Technical Considerations

## Platform Requirements
- **Target Platforms:** macOS (Apple Silicon and Intel), Windows 10/11, Linux (Ubuntu, Fedora)
- **Browser/OS Support:** Native desktop application, no browser dependency
- **Performance Requirements:** Handle 100GB datasets, sub-second queries for common operations, 60fps UI responsiveness

## Technology Preferences
- **Frontend:** React with Electron or Tauri for desktop packaging
- **Backend:** Node.js or Rust for application logic and DuckDB bindings
- **Database:** DuckDB as the core analytical engine
- **Hosting/Infrastructure:** Local-only for MVP, GitHub for distribution

## Architecture Considerations
- **Repository Structure:** Monorepo with clear separation of UI, backend, and LLM components
- **Service Architecture:** Modular design with clear interfaces between chat, SQL engine, and visualization
- **Integration Requirements:** File system access, optional LLM API connections, export to common formats
- **Security/Compliance:** Sandboxed execution, encrypted local storage option, no telemetry without consent
