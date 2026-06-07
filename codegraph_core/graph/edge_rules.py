"""Forward EDGE_RULES registry — 19 out edges."""

from codegraph_core.graph.node_specs import NODE_SPECS
from codegraph_core.graph.types import EdgeRule, RegistryError

GUARD_EDGE_IDS = frozenset({"bridge.beans"})

EDGE_RULES: tuple[EdgeRule, ...] = (
    EdgeRule("service_entry.flow", "service_entry", "flow", "flow", (("flow_id", "flow_id"),)),
    EdgeRule(
        "service_entry.logic", "service_entry", "logic", "logic", (("chain_id", "chain_id"),)
    ),
    EdgeRule(
        "service_entry.bean", "service_entry", "bean", "bean", (("bean_ref", "bean_id"),)
    ),
    EdgeRule("flow.states", "flow", "state", "states", (("flow_id", "flow_id"),)),
    EdgeRule("flow.flow_tasks", "flow", "flow_task", "flow_tasks", (("flow_id", "flow_id"),)),
    EdgeRule("flow.activities", "flow", "activity", "activities", (("flow_id", "flow_id"),)),
    EdgeRule(
        "flow.transitions", "flow", "transition", "transitions", (("flow_id", "flow_id"),)
    ),
    EdgeRule(
        "activity.transitions",
        "activity",
        "transition",
        "transitions",
        (("activity_id", "activity_id"),),
    ),
    EdgeRule(
        "logic.logic_steps", "logic", "logic_step", "logic_steps", (("chain_id", "chain_id"),)
    ),
    EdgeRule("logic.bridges", "logic", "bridge", "bridges", (("chain_id", "chain_id"),)),
    EdgeRule(
        "logic_step.bridges", "logic_step", "bridge", "bridges", (("chain_id", "chain_id"),)
    ),
    EdgeRule(
        "bean.java_class",
        "bean",
        "java_class",
        "java_class",
        (("bean_class", "full_qualified_name"),),
    ),
    EdgeRule(
        "bean.interceptors", "bean", "interceptor", "interceptors", (("bean_id", "bean_ref"),)
    ),
    EdgeRule(
        "java_class.java_methods",
        "java_class",
        "java_method",
        "java_methods",
        (("full_qualified_name", "class_fqn"),),
    ),
    EdgeRule(
        "state.activities",
        "state",
        "activity",
        "activities",
        (("flow_id", "flow_id"), ("state_name", "state_name")),
    ),
    EdgeRule(
        "state.transitions",
        "state",
        "transition",
        "transitions",
        (("flow_id", "flow_id"), ("state_name", "state_name")),
    ),
    EdgeRule(
        "logic.activities",
        "logic",
        "activity",
        "activities",
        (("chain_id", "logic"),),
        assumption="假设 activities.logic 存 chain_id,待校验",
    ),
    EdgeRule(
        "logic.flow_tasks",
        "logic",
        "flow_task",
        "flow_tasks",
        (("chain_id", "logic"),),
        assumption="假设 flow_tasks.logic 存 chain_id,待校验",
    ),
    EdgeRule(
        "bridge.beans",
        "bridge",
        "bean",
        "beans",
        (("before_beans", "bean_id"),),
        guard="按逗号拆分 before_beans 后逐项匹配 bean_id",
    ),
)


def get_edge_rule(rule_id: str) -> EdgeRule | None:
    for rule in EDGE_RULES:
        if rule.id == rule_id:
            return rule
    return None


def get_edges_from(from_type: str) -> list[EdgeRule]:
    return [rule for rule in EDGE_RULES if rule.from_type == from_type]


def _validate_edge_rules(
    node_specs: dict,
    rules: tuple[EdgeRule, ...] | None = None,
) -> None:
    registry = EDGE_RULES if rules is None else rules
    seen_ids: set[str] = set()
    for rule in registry:
        if rule.id in seen_ids:
            raise RegistryError(f"Duplicate edge rule id: {rule.id!r}")
        seen_ids.add(rule.id)

        if rule.from_type not in node_specs:
            raise RegistryError(
                f"Edge rule {rule.id!r} references unknown from_type {rule.from_type!r}"
            )
        if rule.to_type not in node_specs:
            raise RegistryError(
                f"Edge rule {rule.id!r} references unknown to_type {rule.to_type!r}"
            )

        if rule.id in GUARD_EDGE_IDS and not rule.guard:
            raise RegistryError(f"Guard edge {rule.id!r} missing guard declaration")

        if rule.guard is not None and not rule.guard.strip():
            raise RegistryError(f"Edge rule {rule.id!r} has empty guard declaration")
