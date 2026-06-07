## 1. Create codegraph-core module structure
- [ ] 1.1 Create `codegraph-core/` directory as a Python module (add `__init__.py`)
- [ ] 1.2 Add `QueryEngine` interface with `get_pool()`, `q()`, `_schema()`, `out()` methods
- [ ] 1.3 Add `PoolManager` class managing SQLite connection pool (lazy initialization, shared across transports)
- [ ] 1.4 Add `SchemaValidator` class for centralized schema validation before query execution
- [ ] 1.5 Move data models (Symbol, Edge, FileNode) into `codegraph-core/`

## 2. Move analyzer_compat.py to codegraph-core
- [ ] 2.1 Audit `analyzer_compat.py` for MCP-specific dependencies
- [ ] 2.2 Extract any MCP-specific logic from `analyzer_compat.py` (move to `codegraph-mcp`)
- [ ] 2.3 Move `analyzer_compat.py` into `codegraph-core/`
- [ ] 2.4 Verify import works from both `codegraph-mcp` and future `codegraph-server`

## 3. Create codegraph-mcp module
- [ ] 3.1 Create `codegraph-mcp/` directory as a Python module (add `__init__.py`)
- [ ] 3.2 Extract stdio transport adapter code from current MCP server into `codegraph-mcp/`
- [ ] 3.3 Extract MCP protocol parsing code into `codegraph-mcp/`
- [ ] 3.4 Refactor MCP server to delegate all query calls to `QueryEngine` from `codegraph-core`
- [ ] 3.5 Remove duplicate query logic from `codegraph-mcp` (confirm only delegation remains)
- [ ] 3.6 Verify MCP server still works — query behavior unchanged

## 4. Create codegraph-server module
- [ ] 4.1 Create `codegraph-server/` as a Python package (add `__init__.py`)
- [ ] 4.2 Set up FastAPI or Flask project depending on `codegraph-core`
- [ ] 4.3 Create HTTP endpoints mapping to `QueryEngine` primitives (`get_pool`, `q`, `_schema`, `out`)
- [ ] 4.4 Import `analyzer_compat.py` from `codegraph-core` in server analysis functions
- [ ] 4.5 Verify server and MCP produce identical query results for same query

## 5. Verification
- [ ] 5.1 Run existing MCP tests to confirm query behavior unchanged
- [ ] 5.2 Verify `analyzer_compat.py` imports without errors from both MCP and server
- [ ] 5.3 Confirm no duplicate query logic exists in `codegraph-mcp` (only delegation)