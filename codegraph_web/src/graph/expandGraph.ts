import type { ExpandResponse, GraphNode } from '../types/graph'
import { parseNodeKey } from './keys'
import {
  mergeExpandResult,
  setExpandPhase,
  type GraphState,
} from './graphStore'
import { layoutNewNodes } from './layout'

export type ExpandGraphResult =
  | { ok: true; state: GraphState }
  | { ok: false; state: GraphState; error: true }

export async function expandGraphNode(
  state: GraphState,
  schema: string,
  nodeId: string,
  expandFn: (schema: string, node: GraphNode) => Promise<ExpandResponse>,
): Promise<ExpandGraphResult> {
  const node = state.nodes.get(nodeId)
  if (!node || node.expanded) {
    return { ok: true, state }
  }

  const loading = structuredClone(state)
  setExpandPhase(loading, nodeId, 'loading')

  try {
    const response = await expandFn(schema, {
      type: node.type,
      id: node.id,
      title: node.title,
      subtitle: node.subtitle,
    })
    let next = structuredClone(loading)
    const { state: merged, addedNodeKeys } = mergeExpandResult(next, nodeId, response)
    merged.positions = layoutNewNodes(merged, nodeId, addedNodeKeys)
    return { ok: true, state: merged }
  } catch {
    const errorState = structuredClone(loading)
    setExpandPhase(errorState, nodeId, 'error')
    return { ok: false, state: errorState, error: true }
  }
}

export function prepareRetry(state: GraphState, nodeId: string): GraphState {
  const next = structuredClone(state)
  setExpandPhase(next, nodeId, 'idle')
  const node = next.nodes.get(nodeId)
  if (node) {
    next.nodes.set(nodeId, { ...node, expanded: false })
  }
  return next
}

export function parseNodeKeyRef(nodeId: string) {
  return parseNodeKey(nodeId)
}
