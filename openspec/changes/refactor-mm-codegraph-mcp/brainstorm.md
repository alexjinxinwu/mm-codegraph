## Design Summary

Refactor the mm-codegraph MCP project into two modules:
- **codegraph-core**: Common utility functions shared across the codebase
- **codegraph-server**: A user-facing web application for graph browsing and analysis

## Alternatives Considered

### Alternative A: Single Monolithic Module (Current Structure)
- **Approach**: Keep the existing single-module structure with all functionality bundled together
- **Pros**: Simple to start, no modularization overhead
- **Cons**: Hard to reuse core functions in other projects; server and core concerns tightly coupled
- **Why not chosen**: The project needs to support both programmatic API (MCP) and user-facing UI, which have different deployment and usage patterns

### Alternative B: Modular Structure (codegraph-core + codegraph-server)
- **Approach**: Split into two Maven modules — core for shared logic, server for the web UI
- **Pros**: Clean separation of concerns; core can be reused independently; server focuses on user experience
- **Cons**: Slightly more complex build configuration; requires module coordination
- **Why chosen**: Matches the stated goal of separating generic functions from the user-facing tool

### Alternative C: Multi-Module with Shared Kernel
- **Approach**: Introduce an additional `codegraph-kernel` base module that both core and server depend on
- **Pros**: Maximum flexibility and reuse
- **Cons**: Over-engineering for the current scope; adds unnecessary indirection
- **Why not chosen**: Not needed yet — we can refactor to kernel later if more shared patterns emerge

## Agreed Approach

**Alternative B: Modular Structure (codegraph-core + codegraph-server)**

Rationale: The user's intent is clear — extract generic functions into `codegraph-core` and build a user-facing tool in `codegraph-server`. This is a straightforward two-module split that achieves the separation goal without over-engineering.

Implementation:
- `codegraph-core`: Contains all shared logic — data structures, search utilities, graph algorithms, database access helpers
- `codegraph-server`: A Spring Boot web application that exposes REST APIs and a web UI for browsing and analyzing code graphs

## Key Decisions

1. **Maven multi-module project**: Root POM manages both `codegraph-core` and `codegraph-server` as modules
2. **Core has no web dependencies**: `codegraph-core` remains a pure Java library with no HTTP/server concerns
3. **Server depends on core**: `codegraph-server` depends on `codegraph-core` and adds Spring Boot for web UI
4. **Shared data models**: Entity classes (Symbol, Edge, FileNode) live in core and are used by both MCP and server
5. **MCP lives in core**: The MCP server implementation remains in core, enabling programmatic access

## Open Questions

1. Should `codegraph-server` provide its own persistence layer or reuse the existing SQLite indexing from the current codebase?
2. What web framework should `codegraph-server` use — Spring MVC with Thymeleaf, or a separate React/Vue frontend?
3. Should the server expose the same search/browse APIs that the MCP provides, or a different user-facing API surface?