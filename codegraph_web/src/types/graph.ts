export type GraphNode = {
  type: string
  id: number
  title?: string | null
  subtitle?: string | null
}

export type NodeRef = {
  type: string
  id: number
}

export type GraphEdge = {
  ruleId: string
  from: NodeRef
  to: NodeRef
  label: string
}

export type ExpandResponse = {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export type ResolveStatus = 'notFound' | 'found' | 'multiple'

export type ResolveResponse = {
  status: ResolveStatus
  roots: GraphNode[]
  candidates: GraphNode[]
}

export type ExpandPhase = 'idle' | 'loading' | 'error'
