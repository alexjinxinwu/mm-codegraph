import { describe, expect, it, vi, beforeEach } from 'vitest'
import { listSchemas } from './schemas'
import * as client from './client'

describe('listSchemas', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('returns string array from /api/v1/schemas', async () => {
    vi.spyOn(client, 'apiGet').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(['schema_a', 'schema_b']),
    } as unknown as Response)

    const schemas = await listSchemas()
    expect(schemas).toEqual(['schema_a', 'schema_b'])
    expect(client.apiGet).toHaveBeenCalledWith('/api/v1/schemas')
  })
})
