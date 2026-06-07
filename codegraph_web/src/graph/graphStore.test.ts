import { describe, expect, it } from 'vitest'
import { createFromSeed, mergeExpandResult } from './graphStore'
import { nodeKey } from './keys'

describe('graphStore', () => {
  it('creates single-node seed graph without edges', () => {
    const state = createFromSeed({
      type: 'flow',
      id: 1,
      title: 'F1',
      subtitle: 'main',
    })

    expect(state.nodes.size).toBe(1)
    expect(state.edges.size).toBe(0)
    expect(state.positions.get('flow:1')).toEqual({ x: 0, y: 0 })
  })

  it('merges new nodes and edges', () => {
    let state = createFromSeed({ type: 'flow', id: 1, title: 'F1' })
    const result = mergeExpandResult(state, 'flow:1', {
      nodes: [
        { type: 'flow', id: 1, title: 'F1' },
        { type: 'state', id: 2, title: 'S1', subtitle: 'st' },
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
    state = result.state

    expect(state.nodes.size).toBe(2)
    expect(state.edges.size).toBe(1)
    expect(state.nodes.get('flow:1')?.expanded).toBe(true)
    expect(result.addedNodeKeys).toEqual(['state:2'])
  })

  it('skips duplicate nodes', () => {
    let state = createFromSeed({ type: 'flow', id: 1, title: 'F1' })
    state.nodes.set('state:2', { type: 'state', id: 2, title: 'Existing' })

    const result = mergeExpandResult(state, 'flow:1', {
      nodes: [
        { type: 'state', id: 2, title: 'Updated' },
        { type: 'state', id: 3, title: 'New' },
      ],
      edges: [],
    })

    expect(result.state.nodes.size).toBe(3)
    expect(result.addedNodeKeys).toEqual(['state:3'])
  })

  it('skips duplicate edges', () => {
    let state = createFromSeed({ type: 'flow', id: 1 })
    const edge = {
      ruleId: 'flow.states',
      from: { type: 'flow', id: 1 },
      to: { type: 'state', id: 2 },
      label: 'states',
    }
    state.edges.set('flow.states:flow:1:state:2', edge)

    const result = mergeExpandResult(state, 'flow:1', {
      nodes: [{ type: 'state', id: 2, title: 'S' }],
      edges: [edge],
    })

    expect(result.state.edges.size).toBe(1)
    expect(result.addedEdgeKeys).toEqual([])
  })

  it('marks source expanded', () => {
    const state = createFromSeed({ type: 'flow', id: 1 })
    const merged = mergeExpandResult(state, nodeKey({ type: 'flow', id: 1 }), {
      nodes: [{ type: 'state', id: 2, title: 'S' }],
      edges: [],
    })
    expect(merged.state.nodes.get('flow:1')?.expanded).toBe(true)
  })
})
