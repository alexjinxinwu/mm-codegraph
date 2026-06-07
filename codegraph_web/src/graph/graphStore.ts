import type { ExpandResponse, GraphNode } from '../types/graph'
import { edgeKey, nodeKey } from './keys'

export type GraphNodeState = GraphNode & { expanded?: boolean }

export type GraphState = {
  nodes: Map<string, GraphNodeState>
  edges: Map<string, ExpandResponse['edges'][number]>
  positions: Map<string, { x: number; y: number }>
  expandPhase: Map<string, 'idle' | 'loading' | 'error'>
}

export function emptyGraphState(): GraphState {
  return {
    nodes: new Map(),
    edges: new Map(),
    positions: new Map(),
    expandPhase: new Map(),
  }
}

export function createFromSeed(seed: GraphNode): GraphState {
  const state = emptyGraphState()
  const key = nodeKey(seed)
  state.nodes.set(key, { ...seed, expanded: false })
  state.positions.set(key, { x: 0, y: 0 })
  state.expandPhase.set(key, 'idle')
  return state
}

export function mergeExpandResult(
  state: GraphState,
  sourceKey: string,
  response: ExpandResponse,
): { state: GraphState; addedNodeKeys: string[]; addedEdgeKeys: string[] } {
  const addedNodeKeys: string[] = []
  const addedEdgeKeys: string[] = []

  for (const node of response.nodes) {
    const key = nodeKey(node)
    const existing = state.nodes.get(key)
    if (existing) {
      state.nodes.set(key, {
        ...existing,
        title: node.title ?? existing.title,
        subtitle: node.subtitle ?? existing.subtitle,
      })
    } else {
      state.nodes.set(key, { ...node, expanded: false })
      if (!state.expandPhase.has(key)) {
        state.expandPhase.set(key, 'idle')
      }
      addedNodeKeys.push(key)
    }
  }

  for (const edge of response.edges) {
    const key = edgeKey(edge)
    if (!state.edges.has(key)) {
      state.edges.set(key, edge)
      addedEdgeKeys.push(key)
    }
  }

  const source = state.nodes.get(sourceKey)
  if (source) {
    state.nodes.set(sourceKey, { ...source, expanded: true })
  }
  state.expandPhase.set(sourceKey, 'idle')

  return { state, addedNodeKeys, addedEdgeKeys }
}

export function setExpandPhase(
  state: GraphState,
  nodeKeyStr: string,
  phase: 'idle' | 'loading' | 'error',
): GraphState {
  state.expandPhase.set(nodeKeyStr, phase)
  return state
}
