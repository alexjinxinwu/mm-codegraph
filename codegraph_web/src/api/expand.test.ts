import { describe, expect, it, vi, beforeEach } from 'vitest'
import { expandNode } from './expand'

describe('expandNode', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('posts expand request with schema and node', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          nodes: [{ type: 'flow', id: 2, title: 'F' }],
          edges: [],
        }),
    } as Response)

    await expandNode('S', { type: 'flow', id: 1 })

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/expand', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schema: 'S', node: { type: 'flow', id: 1 } }),
    })
  })

  it('parses ExpandResponse JSON', async () => {
    const body = {
      nodes: [{ type: 'state', id: 3, title: 'S1', subtitle: 'flow' }],
      edges: [
        {
          ruleId: 'flow.states',
          from: { type: 'flow', id: 1 },
          to: { type: 'state', id: 3 },
          label: 'states',
        },
      ],
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(body),
    } as Response)

    const result = await expandNode('S', { type: 'flow', id: 1 })
    expect(result).toEqual(body)
  })
})
