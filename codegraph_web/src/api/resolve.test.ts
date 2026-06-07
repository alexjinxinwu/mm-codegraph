import { describe, expect, it, vi, beforeEach } from 'vitest'
import { resolveEntry } from './resolve'
import * as client from './client'

describe('resolveEntry', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('builds resolve URL with encoded params', async () => {
    const mockJson = vi.fn().mockResolvedValue({
      status: 'found',
      roots: [{ type: 'service_entry', id: 1 }],
      candidates: [],
    })
    vi.spyOn(client, 'apiGet').mockResolvedValue({
      ok: true,
      json: mockJson,
    } as unknown as Response)

    await resolveEntry('S', 'commandId', 'Cmd 1')

    expect(client.apiGet).toHaveBeenCalledWith(
      '/api/v1/resolve?schema=S&kind=commandId&value=Cmd+1',
    )
  })

  it('parses ResolveResponse JSON', async () => {
    const body = {
      status: 'found' as const,
      roots: [{ type: 'flow', id: 3, title: 'F1', subtitle: 'main' }],
      candidates: [],
    }
    vi.spyOn(client, 'apiGet').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(body),
    } as unknown as Response)

    const result = await resolveEntry('S', 'flowId', 'F1')
    expect(result).toEqual(body)
  })

  it('throws ApiError on non-ok response', async () => {
    vi.spyOn(client, 'apiGet').mockResolvedValue({
      ok: false,
      status: 422,
      text: () => Promise.resolve('validation error'),
    } as unknown as Response)

    await expect(resolveEntry('S', 'bad', 'x')).rejects.toMatchObject({
      status: 422,
    })
  })
})
