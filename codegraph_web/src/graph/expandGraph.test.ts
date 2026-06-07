import { describe, expect, it, vi } from 'vitest'
import { createFromSeed } from './graphStore'
import { expandGraphNode, prepareRetry } from './expandGraph'

describe('expandGraphNode', () => {
  it('merges neighbors and marks expanded', async () => {
    const state = createFromSeed({ type: 'flow', id: 1, title: 'F1' })
    const expandFn = vi.fn().mockResolvedValue({
      nodes: [
        { type: 'flow', id: 1, title: 'F1' },
        { type: 'state', id: 2, title: 'S1' },
      ],
      edges: [
        {
          ruleId: 'flow.states',
          from: { type: 'flow', id: 1 },
          to: { type: 'state', id: 2 },
          label: 'states',
        },
      ],
    })

    const result = await expandGraphNode(state, 'S', 'flow:1', expandFn)

    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.state.nodes.size).toBe(2)
      expect(result.state.nodes.get('flow:1')?.expanded).toBe(true)
    }
    expect(expandFn).toHaveBeenCalledWith('S', expect.objectContaining({ type: 'flow', id: 1 }))
  })

  it('dedupes duplicate nodes in response', async () => {
    const state = createFromSeed({ type: 'flow', id: 1, title: 'F1' })
    state.nodes.set('state:2', { type: 'state', id: 2, title: 'Existing' })

    const result = await expandGraphNode(
      state,
      'S',
      'flow:1',
      vi.fn().mockResolvedValue({
        nodes: [
          { type: 'state', id: 2, title: 'Dup' },
          { type: 'state', id: 3, title: 'New' },
        ],
        edges: [],
      }),
    )

    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.state.nodes.size).toBe(3)
    }
  })

  it('skips expand when node already expanded', async () => {
    const state = createFromSeed({ type: 'flow', id: 1, title: 'F1' })
    state.nodes.set('flow:1', { type: 'flow', id: 1, title: 'F1', expanded: true })
    const expandFn = vi.fn()

    const result = await expandGraphNode(state, 'S', 'flow:1', expandFn)

    expect(result.ok).toBe(true)
    expect(expandFn).not.toHaveBeenCalled()
  })

  it('returns error state on failure', async () => {
    const state = createFromSeed({ type: 'flow', id: 1, title: 'F1' })
    const result = await expandGraphNode(
      state,
      'S',
      'flow:1',
      vi.fn().mockRejectedValue(new Error('fail')),
    )

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.state.expandPhase.get('flow:1')).toBe('error')
    }
  })

  it('prepareRetry clears expanded flag', () => {
    const state = createFromSeed({ type: 'flow', id: 1, title: 'F1' })
    state.nodes.set('flow:1', { type: 'flow', id: 1, title: 'F1', expanded: true })
    state.expandPhase.set('flow:1', 'error')

    const next = prepareRetry(state, 'flow:1')
    expect(next.nodes.get('flow:1')?.expanded).toBe(false)
    expect(next.expandPhase.get('flow:1')).toBe('idle')
  })
})
