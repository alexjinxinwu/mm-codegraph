## ADDED Requirements

### Requirement: QueryEngine interface provides query primitives

The `QueryEngine` interface in `codegraph-core` MUST expose the following primitives as method calls: `get_pool()`, `q()`, `_schema()`, and `out()`. Both the MCP stdio adapter and the HTTP server MUST call these methods directly — no transport-specific query logic is allowed outside `codegraph-core`.

#### Scenario: get_pool returns current pool state
- **WHEN** a client calls `get_pool()` on `QueryEngine`
- **THEN** it returns the current pool state including active connections, idle connections, and pool configuration

#### Scenario: q executes a query and returns results
- **WHEN** a client calls `q(query_string)` on `QueryEngine`
- **THEN** it executes the query against the code graph and returns results with identical behavior regardless of whether the caller is MCP or HTTP transport

#### Scenario: _schema returns schema information
- **WHEN** a client calls `_schema()` on `QueryEngine`
- **THEN** it returns the current schema definition used for validation

#### Scenario: out formats and returns output
- **WHEN** a client calls `out(results, format)` on `QueryEngine`
- **THEN** it formats results according to the specified format with behavior consistent across all transports

---

### Requirement: PoolManager manages SQLite connection pool

`PoolManager` in `codegraph-core` MUST manage the SQLite connection pool. Both MCP server process and HTTP server process MUST obtain connections from this single shared pool instance.

#### Scenario: PoolManager is lazily initialized
- **WHEN** the first query request arrives from any transport
- **THEN** `PoolManager` is initialized with configuration from the environment or config file

#### Scenario: Connection pool is shared across transports
- **WHEN** MCP server requests a connection and HTTP server requests a connection
- **THEN** both receive connections from the same pool, with no duplicate pool instances

---

### Requirement: SchemaValidator enforces schema consistency

All schema validation MUST happen in `SchemaValidator` within `codegraph-core` before query execution. No transport-specific validation logic is allowed.

#### Scenario: SchemaValidator rejects invalid queries
- **WHEN** a query is submitted that violates the schema
- **THEN** `SchemaValidator` rejects it with a consistent error code, regardless of transport (MCP stdio or HTTP)

#### Scenario: Schema validation happens before execution
- **WHEN** a valid query is submitted
- **THEN** schema validation occurs in `SchemaValidator` before the query reaches `QueryEngine` execution