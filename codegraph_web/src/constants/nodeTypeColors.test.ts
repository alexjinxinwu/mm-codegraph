import { describe, expect, it } from 'vitest'
import { colorForNodeType } from './nodeTypeColors'

describe('nodeTypeColors', () => {
  it('assigns different colors to distinct types', () => {
    expect(colorForNodeType('service_entry')).not.toBe(colorForNodeType('flow'))
  })
})
