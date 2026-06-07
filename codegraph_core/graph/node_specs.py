"""NodeSpec registry — 14 ER node types."""

from codegraph_core.graph.types import NodeSpec, RegistryError

EXPECTED_NODE_TYPES = frozenset({
    "service_entry",
    "flow",
    "logic",
    "bean",
    "state",
    "flow_task",
    "activity",
    "transition",
    "logic_step",
    "bridge",
    "java_class",
    "interceptor",
    "java_method",
    "module_parameter",
})

NODE_SPECS: dict[str, NodeSpec] = {
    "service_entry": NodeSpec(
        "service_entry", "service_entries", "id", "name", "entry_type"
    ),
    "flow": NodeSpec("flow", "flows", "id", "flow_id", "flow_type"),
    "logic": NodeSpec("logic", "logics", "id", "chain_id", "context_id"),
    "bean": NodeSpec("bean", "beans", "id", "bean_id", "bean_class"),
    "state": NodeSpec("state", "states", "id", "state_name", "flow_id"),
    "flow_task": NodeSpec("flow_task", "flow_tasks", "id", "task_type", "logic"),
    "activity": NodeSpec(
        "activity", "activities", "id", "activity_name", "activity_id"
    ),
    "transition": NodeSpec(
        "transition", "transitions", "id", "trans_type", "next_target"
    ),
    "logic_step": NodeSpec(
        "logic_step", "logic_steps", "id", "logic_type", "chain_id"
    ),
    "bridge": NodeSpec("bridge", "bridges", "id", "bridge_id", "logic_type"),
    "java_class": NodeSpec(
        "java_class", "java_classes", "id", "class_name", "package_name"
    ),
    "interceptor": NodeSpec(
        "interceptor", "interceptors", "id", "stack_name", "bean_ref"
    ),
    "java_method": NodeSpec(
        "java_method", "java_methods", "id", "method_name", "class_fqn"
    ),
    "module_parameter": NodeSpec(
        "module_parameter",
        "module_parameters",
        "id",
        "parameter_name",
        "param_key",
    ),
}


def get_node_spec(node_type: str) -> NodeSpec | None:
    return NODE_SPECS.get(node_type)


def _validate_node_specs(specs: dict[str, NodeSpec] | None = None) -> None:
    registry = NODE_SPECS if specs is None else specs
    if set(registry.keys()) != EXPECTED_NODE_TYPES:
        missing = EXPECTED_NODE_TYPES - set(registry.keys())
        extra = set(registry.keys()) - EXPECTED_NODE_TYPES
        raise RegistryError(
            f"NODE_SPECS must contain exactly 14 types; missing={missing!r}, extra={extra!r}"
        )
    for node_type, spec in registry.items():
        if not spec.table:
            raise RegistryError(f"NodeSpec {node_type!r} missing table")
        if not spec.id_column:
            raise RegistryError(f"NodeSpec {node_type!r} missing id_column")
