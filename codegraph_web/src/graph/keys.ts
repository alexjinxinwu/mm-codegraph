import type { GraphEdge, NodeRef } from '../types/graph'

export function nodeKey(n: NodeRef): string {
  return `${n.type}:${n.id}`
}

export function edgeKey(e: GraphEdge): string {
  return `${e.ruleId}:${e.from.type}:${e.from.id}:${e.to.type}:${e.to.id}`
}

export function parseNodeKey(key: string): NodeRef {
  const idx = key.indexOf(':')
  const type = key.slice(0, idx)
  const id = Number(key.slice(idx + 1))
  return { type, id }
}
