export type GraphNode = {
  type: string
  id: number
  title?: string | null
  subtitle?: string | null
}

export type ResolveStatus = 'notFound' | 'found' | 'multiple'

export type ResolveResponse = {
  status: ResolveStatus
  roots: GraphNode[]
  candidates: GraphNode[]
}
