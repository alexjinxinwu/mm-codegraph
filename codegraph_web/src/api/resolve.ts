import { apiGet, ApiError } from './client'
import type { ResolveResponse } from '../types/graph'

export async function resolveEntry(
  schema: string,
  kind: string,
  value: string,
): Promise<ResolveResponse> {
  const params = new URLSearchParams({ schema, kind, value })
  const res = await apiGet(`/api/v1/resolve?${params}`)
  if (!res.ok) {
    throw new ApiError(res.status, await res.text())
  }
  return res.json() as Promise<ResolveResponse>
}
