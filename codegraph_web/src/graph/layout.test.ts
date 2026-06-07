import { describe, expect, it } from 'vitest'
import { createFromSeed, mergeExpandResult } from './graphStore'
import { layoutNewNodes, snapshotPositions } from './layout'

describe('layoutNewNodes', () => {
  it('keeps anchor position stable', () => {
    const state = createFromSeed({ type: 'flow', id: 1, title: 'F1' })
    state.positions.set('flow:1', { x: 120, y: 80 })

    const positions = layoutNewNodes(state, 'flow:1', ['state:2', 'state:3'])

    expect(positions.get('flow:1')).toEqual({ x: 120, y: 80 })
  })

  it('places new nodes near anchor', () => {
    const state = createFromSeed({ type: 'flow', id: 1 })
    const positions = layoutNewNodes(state, 'flow:1', ['state:2'])

    const anchor = positions.get('flow:1')!
    const child = positions.get('state:2')!
    const distance = Math.hypot(child.x - anchor.x, child.y - anchor.y)
    expect(distance).toBeLessThan(400)
    expect(distance).toBeGreaterThan(0)
  })

  it('does not move existing nodes when merging layout', () => {
    let state = createFromSeed({ type: 'flow', id: 1 })
    state.positions.set('flow:1', { x: 50, y: 50 })
    state.positions.set('state:2', { x: 250, y: 50 })

    const before = snapshotPositions(state.positions, ['flow:1', 'state:2'])

    const merged = mergeExpandResult(state, 'flow:1', {
      nodes: [{ type: 'state', id: 3, title: 'S3' }],
      edges: [
        {
          ruleId: 'flow.states',
          from: { type: 'flow', id: 1 },
          to: { type: 'state', id: 3 },
          label: 'states',
        },
      ],
    })

    const positions = layoutNewNodes(merged.state, 'flow:1', merged.addedNodeKeys)
    const after = snapshotPositions(positions, ['flow:1', 'state:2'])

    expect(after).toEqual(before)
  })
})
