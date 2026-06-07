import { apiGet, ApiError } from './client'

export async function listSchemas(): Promise<string[]> {
  const res = await apiGet('/api/v1/schemas')
  if (!res.ok) {
    throw new ApiError(res.status, await res.text())
  }
  return res.json() as Promise<string[]>
}
