import dagre from '@dagrejs/dagre'
import type { GraphState } from './graphStore'
import { nodeKey } from './keys'

const NODE_WIDTH = 180
const NODE_HEIGHT = 72

export function layoutNewNodes(
  state: GraphState,
  anchorKey: string,
  newNodeKeys: string[],
): Map<string, { x: number; y: number }> {
  const positions = new Map(state.positions)
  if (newNodeKeys.length === 0) {
    return positions
  }

  const anchorPos = positions.get(anchorKey) ?? { x: 0, y: 0 }
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'LR', nodesep: 60, ranksep: 90 })

  const subgraphKeys = new Set([anchorKey, ...newNodeKeys])
  for (const key of subgraphKeys) {
    g.setNode(key, { width: NODE_WIDTH, height: NODE_HEIGHT })
  }

  for (const edge of state.edges.values()) {
    const from = nodeKey(edge.from)
    const to = nodeKey(edge.to)
    if (subgraphKeys.has(from) && subgraphKeys.has(to)) {
      g.setEdge(from, to)
    }
  }

  if (g.edgeCount() === 0 && newNodeKeys.length > 0) {
    for (const key of newNodeKeys) {
      g.setEdge(anchorKey, key)
    }
  }

  dagre.layout(g)

  const anchorLayout = g.node(anchorKey)
  const dx = anchorPos.x - anchorLayout.x
  const dy = anchorPos.y - anchorLayout.y

  for (const key of newNodeKeys) {
    const layoutNode = g.node(key)
    positions.set(key, { x: layoutNode.x + dx, y: layoutNode.y + dy })
  }

  return positions
}

export function snapshotPositions(
  positions: Map<string, { x: number; y: number }>,
  keys: string[],
): Record<string, { x: number; y: number }> {
  const out: Record<string, { x: number; y: number }> = {}
  for (const key of keys) {
    const pos = positions.get(key)
    if (pos) out[key] = { ...pos }
  }
  return out
}
