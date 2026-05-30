## ADDED Requirements

### Requirement: Service Impact Search MCP Tool

The system SHALL provide an MCP tool `search_service_impact` in `codegraph-mcp/codegraph-server.py` that accepts `commandId` or `flowId` as parameters and returns a list of all files impacted by traversing the ER relationships across 13 tables in the service network.

**ER Traversal Paths (13 Tables):**

*Forward Traversal:*
```
service_entry
  ├──[chain_id]──→ logics
  │                 ├──[chain_id]──→ logic_steps
  │                 └──[chain_id]──→ bridges
  │                                ├── before_beans (FQN) ──→ beans.bean_class
  │                                └── after_beans  (FQN) ──→ beans.bean_class
  │                                                          └── java_classes.java_path
  ├──[flow_id]──→ flows
  │                 └──[flow_id]──→ states
  │                               ├── activities.logic ──→ logics.chain_id
  │                               └── transitions
  │                                     ├── next_target ──→ states.state_name
  │                                     └── state_name ──→ states
  ├──[bean_ref]──→ beans.bean_id ──→ java_classes.java_path
  └──[context_name]──→ interceptors.context_name ──→ bean_ref ──→ beans
```

*Backward Traversal:*
```
service_entry (target)
  ├─ 哪些 service_entry.flow_id → flows.flow_id 指向当前
  ├─ 哪些 service_entry.chain_id → logics.chain_id 指向当前
  ├─ 哪些 activities.logic → logics.chain_id 指向当前
  ├─ 哪些 flow_tasks.logic → logics.chain_id 指向当前
  ├─ 哪些 transitions.next_target → states.state_name 指向当前 state
  └─ 哪些 bridges.before_beans / after_beans → beans.bean_class 指向当前 bean
```

#### Scenario: Search by commandId with forward direction
- **WHEN** the client calls `search_service_impact(schema="1.0_Base", commandId="CMD_CREATE_ORDER", direction="forward")`
- **THEN** the system SHALL traverse the ER graph starting from the service entry with `command_id=CMD_CREATE_ORDER`, follow `flow_id` and `chain_id` relationships to downstream nodes across all 13 tables, and return all unique file paths from beans and xml_path fields

#### Scenario: Search by flowId with backward direction
- **WHEN** the client calls `search_service_impact(schema="1.0_Base", flowId="ORDER_FLOW", direction="backward")`
- **THEN** the system SHALL find all upstream references (service_entries, activities, flow_tasks, transitions) that point to the target flow and return their associated file paths

#### Scenario: Search by flowId with both directions
- **WHEN** the client calls `search_service_impact(schema="1.0_Base", flowId="ORDER_FLOW", direction="both")`
- **THEN** the system SHALL return both upstream and downstream impacted files in a single response

#### Scenario: maxDepth limits traversal depth
- **WHEN** the client calls `search_service_impact(schema="1.0_Base", commandId="CMD_CREATE_ORDER", maxDepth=3)`
- **THEN** the system SHALL stop traversing after reaching depth 3 and return only files within that depth

#### Scenario: Circular dependency detection
- **WHEN** the traversal encounters a node already visited in the current path
- **THEN** the system SHALL skip that node to prevent infinite loop and MAY include a warning in the response indicating circular path detected

---

### Requirement: Impact Chain Documentation

The system SHALL return a complete impact chain showing the relationship edges between nodes across all 13 tables (service_entries → flows → states → transitions → activities → flow_tasks → logics → logic_steps → bridges → beans → java_classes → interceptors → java_methods), so that clients can understand the full propagation path.

#### Scenario: Impact chain includes all hops
- **WHEN** the client requests impact search for `CMD_CREATE_ORDER`
- **THEN** the response SHALL include an `impactChain` array where each entry contains `from` and `to` fields describing the node type and identifier for each hop in the traversal across all 13 tables

---

### Requirement: File Deduplication

The system SHALL return a deduplicated list of files, where each file path appears at most once in the `files` array.

#### Scenario: Same file referenced by multiple paths appears once
- **WHEN** the traversal reaches a bean that is referenced by multiple bridges
- **THEN** the system SHALL include that bean's file path only once in the `files` array

---

### Requirement: Response Format

The system SHALL return a JSON response conforming to the following structure:
```json
{
  "entryPoint": "string",
  "direction": "forward|backward|both",
  "totalImpacted": 0,
  "files": [
    {
      "path": "string",
      "type": "java|xml"
    }
  ],
  "impactChain": [
    {
      "from": "string",
      "to": "string"
    }
  ],
  "warnings": ["string"]
}
```

#### Scenario: Response structure is correct
- **WHEN** the client sends a valid impact search request
- **THEN** the response SHALL contain exactly the fields: `entryPoint`, `direction`, `totalImpacted`, `files`, `impactChain`, and optionally `warnings`

#### Scenario: Response with warnings when circular path detected
- **WHEN** the traversal detects a circular dependency
- **THEN** the response SHALL include a `warnings` array containing a message describing the circular path

---

### Requirement: Parameter Validation

The system SHALL validate that at least one of `commandId` or `flowId` is provided, and raise an error when neither is supplied.

#### Scenario: Missing both commandId and flowId raises error
- **WHEN** the client calls `search_service_impact(schema="1.0_Base")` without commandId or flowId
- **THEN** the system SHALL raise an error with message: `"At least one of commandId or flowId must be provided"`

#### Scenario: Invalid direction raises error
- **WHEN** the client calls `search_service_impact(schema="1.0_Base", commandId="CMD_CREATE_ORDER", direction="invalid")`
- **THEN** the system SHALL raise an error with message: `"direction must be one of: forward, backward, both"`
