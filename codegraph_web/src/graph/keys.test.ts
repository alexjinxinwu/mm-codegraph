import { describe, expect, it } from 'vitest'
import { edgeKey, nodeKey } from './keys'

describe('keys', () => {
  it('builds stable node and edge keys', () => {
    expect(nodeKey({ type: 'flow', id: 1 })).toBe('flow:1')
    expect(
      edgeKey({
        ruleId: 'flow.states',
        from: { type: 'flow', id: 1 },
        to: { type: 'state', id: 2 },
        label: 'states',
      }),
    ).toBe('flow.states:flow:1:state:2')
  })
})
