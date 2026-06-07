import { ApiError } from './client'
import type { ExpandResponse, NodeRef } from '../types/graph'

export async function expandNode(
  schema: string,
  node: NodeRef,
): Promise<ExpandResponse> {
  const res = await fetch('/api/v1/expand', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ schema, node }),
  })
  if (!res.ok) {
    throw new ApiError(res.status, await res.text())
  }
  return res.json() as Promise<ExpandResponse>
}
