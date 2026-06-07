"""ENTRY_RESOLVERS registry — external identifiers to root nodes."""

from codegraph_core.graph.node_specs import NODE_SPECS
from codegraph_core.graph.types import EntryResolver, RegistryError

ENTRY_RESOLVERS: tuple[EntryResolver, ...] = (
    EntryResolver("commandId", "service_entry", "command_id"),
    EntryResolver("flowId", "flow", "flow_id"),
)


def get_resolver(kind: str) -> EntryResolver | None:
    for resolver in ENTRY_RESOLVERS:
        if resolver.kind == kind:
            return resolver
    return None


def _validate_entry_resolvers(node_specs: dict | None = None) -> None:
    specs = NODE_SPECS if node_specs is None else node_specs
    for resolver in ENTRY_RESOLVERS:
        if resolver.node_type not in specs:
            raise RegistryError(
                f"EntryResolver {resolver.kind!r} references unknown "
                f"node_type {resolver.node_type!r}"
            )
        if not resolver.match_column:
            raise RegistryError(f"EntryResolver {resolver.kind!r} missing match_column")
