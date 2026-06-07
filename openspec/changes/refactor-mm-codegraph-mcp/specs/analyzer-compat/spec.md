## ADDED Requirements

### Requirement: analyzer_compat.py is importable from codegraph-core

`analyzer_compat.py` MUST be located in `codegraph-core` and MUST be importable by both `codegraph-mcp` and `codegraph-server` without modification. It MUST NOT contain MCP-specific assumptions that prevent reuse.

#### Scenario: analyzer_compat.py is importable by MCP
- **WHEN** `codegraph-mcp` imports `analyzer_compat` from `codegraph-core`
- **THEN** it imports successfully and all compatibility functions work as before

#### Scenario: analyzer_compat.py is importable by HTTP server
- **WHEN** `codegraph-server` imports `analyzer_compat` from `codegraph-core`
- **THEN** it imports successfully and all compatibility functions work as they do for MCP

---

### Requirement: analyzer_compat.py has no MCP transport dependencies

`analyzer_compat.py` MUST NOT import or depend on any MCP-specific modules, stdio transport code, or MCP protocol handling. Any MCP-specific compatibility logic MUST be extracted before the move to `codegraph-core`.

#### Scenario: analyzer_compat.py has no stdio dependencies
- **WHEN** `codegraph-core` is imported in a context without MCP stdio
- **THEN** `analyzer_compat.py` does not fail due to missing MCP transport dependencies

#### Scenario: analyzer_compat.py compatibility functions are pure
- **WHEN** a compatibility function in `analyzer_compat.py` is called
- **THEN** it performs only data transformation and analysis logic, with no side effects related to MCP transport