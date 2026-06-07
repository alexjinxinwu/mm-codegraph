import { describe, expect, it } from 'vitest'
import { ENTRY_KINDS } from './entryKinds'

describe('ENTRY_KINDS', () => {
  it('includes commandId and flowId', () => {
    const values = ENTRY_KINDS.map((k) => k.value)
    expect(values).toContain('commandId')
    expect(values).toContain('flowId')
  })
})
