import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  applyEdgeChanges,
  applyNodeChanges,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  type NodeMouseHandler,
} from '@xyflow/react'
import { expandNode } from '../api/expand'
import type { GraphNode } from '../types/graph'
import { expandGraphNode, prepareRetry } from './expandGraph'
import { edgeKey, nodeKey } from './keys'
import { createFromSeed, type GraphState } from './graphStore'

function toFlowNodes(state: GraphState): Node[] {
  return [...state.nodes.entries()].map(([id, node]) => {
    const pos = state.positions.get(id) ?? { x: 0, y: 0 }
    return {
      id,
      type: 'codegraph',
      position: pos,
      data: {
        title: node.title,
        subtitle: node.subtitle,
        nodeType: node.type,
        nodeId: node.id,
        expanded: node.expanded,
        phase: state.expandPhase.get(id) ?? 'idle',
      },
    }
  })
}

function toFlowEdges(state: GraphState): Edge[] {
  return [...state.edges.entries()].map(([id, edge]) => ({
    id,
    source: nodeKey(edge.from),
    target: nodeKey(edge.to),
    label: edge.label,
  }))
}

export function useGraphCanvas(schema: string, seed: GraphNode | null) {
  const [nodes, setNodes] = useState<Node[]>([])
  const [edges, setEdges] = useState<Edge[]>([])
  const graphRef = useRef<GraphState | null>(null)
  const inFlightRef = useRef<Set<string>>(new Set())

  const syncFlow = useCallback((state: GraphState) => {
    graphRef.current = state
    setNodes(toFlowNodes(state))
    setEdges(toFlowEdges(state))
  }, [])

  useEffect(() => {
    if (!seed) {
      graphRef.current = null
      setNodes([])
      setEdges([])
      inFlightRef.current.clear()
      return
    }
    syncFlow(createFromSeed(seed))
  }, [seed, syncFlow])

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setNodes((current) => applyNodeChanges(changes, current))
  }, [])

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    setEdges((current) => applyEdgeChanges(changes, current))
  }, [])

  const runExpand = useCallback(
    async (nodeId: string) => {
      if (!schema || !graphRef.current) return
      if (inFlightRef.current.has(nodeId)) return

      const node = graphRef.current.nodes.get(nodeId)
      if (!node || node.expanded) return

      inFlightRef.current.add(nodeId)
      const loading = structuredClone(graphRef.current)
      loading.expandPhase.set(nodeId, 'loading')
      syncFlow(loading)

      const result = await expandGraphNode(
        graphRef.current,
        schema,
        nodeId,
        expandNode,
      )
      syncFlow(result.state)
      inFlightRef.current.delete(nodeId)
    },
    [schema, syncFlow],
  )

  const onRetry = useCallback(
    (nodeId: string) => {
      if (!graphRef.current) return
      syncFlow(prepareRetry(graphRef.current, nodeId))
      void runExpand(nodeId)
    },
    [runExpand, syncFlow],
  )

  const onNodeClick: NodeMouseHandler = useCallback(
    (_, node) => {
      void runExpand(node.id)
    },
    [runExpand],
  )

  const nodesWithHandlers = useMemo(
    () =>
      nodes.map((node) => ({
        ...node,
        data: {
          ...node.data,
          onRetry: () => onRetry(node.id),
        },
      })),
    [nodes, onRetry],
  )

  return {
    nodes: nodesWithHandlers,
    edges,
    onNodesChange,
    onEdgesChange,
    onNodeClick,
    runExpand,
    onRetry,
  }
}

export { nodeKey, edgeKey }
