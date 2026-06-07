import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { expandGraphNode } from '../graph/expandGraph'
import { createFromSeed } from '../graph/graphStore'
import * as expandApi from '../api/expand'

vi.mock('../graph/expandGraph', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../graph/expandGraph')>()
  return {
    ...actual,
    expandGraphNode: vi.fn(actual.expandGraphNode),
  }
})

describe('Graph canvas expand flow', () => {
  beforeEach(() => {
    vi.mocked(expandGraphNode).mockRestore()
    vi.restoreAllMocks()
  })

  it('expand merges neighbors without duplicates', async () => {
    vi.spyOn(expandApi, 'expandNode').mockResolvedValue({
      nodes: [
        { type: 'flow', id: 1, title: 'F1' },
        { type: 'state', id: 2, title: 'S1', subtitle: 'st' },
        { type: 'flow', id: 1, title: 'F1' },
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

    const state = createFromSeed({ type: 'flow', id: 1, title: 'F1', subtitle: 'main' })
    const result = await expandGraphNode(state, 'S', 'flow:1', expandApi.expandNode)

    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.state.nodes.size).toBe(2)
    }
  })

  it('shows error state on failure', async () => {
    vi.spyOn(expandApi, 'expandNode').mockRejectedValue(new Error('boom'))
    const state = createFromSeed({ type: 'flow', id: 1, title: 'F1' })
    const result = await expandGraphNode(state, 'S', 'flow:1', expandApi.expandNode)

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.state.expandPhase.get('flow:1')).toBe('error')
    }
  })

  it('distinguishes node types in graph state', async () => {
    vi.spyOn(expandApi, 'expandNode').mockResolvedValue({
      nodes: [
        { type: 'flow', id: 1, title: 'F1' },
        { type: 'state', id: 2, title: 'S1' },
      ],
      edges: [],
    })

    const state = createFromSeed({ type: 'flow', id: 1, title: 'F1' })
    const result = await expandGraphNode(state, 'S', 'flow:1', expandApi.expandNode)

    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.state.nodes.get('flow:1')?.type).toBe('flow')
      expect(result.state.nodes.get('state:2')?.type).toBe('state')
    }
  })
})

describe('GraphCanvas UI', () => {
  it('renders canvas with mocked hook', async () => {
    const { GraphCanvas } = await import('./GraphCanvas')
    render(
      <GraphCanvas
        schema="S"
        seed={{ type: 'flow', id: 1, title: 'F1', subtitle: 'main' }}
      />,
    )
    await waitFor(() => {
      expect(screen.getByTestId('graph-canvas')).toBeInTheDocument()
    })
  })
})
