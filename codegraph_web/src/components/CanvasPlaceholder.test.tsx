import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CanvasPlaceholder } from './CanvasPlaceholder'

describe('CanvasPlaceholder', () => {
  it('shows empty placeholder when seed is null', () => {
    render(<CanvasPlaceholder seed={null} />)
    expect(screen.getByTestId('canvas-empty')).toBeInTheDocument()
  })

  it('shows seed summary when seed is set', () => {
    render(
      <CanvasPlaceholder
        seed={{
          type: 'service_entry',
          id: 12,
          title: 'MyCmd',
          subtitle: 'command',
        }}
      />,
    )

    expect(screen.getByTestId('seed-type')).toHaveTextContent('service_entry')
    expect(screen.getByTestId('seed-id')).toHaveTextContent('12')
    expect(screen.getByTestId('seed-title')).toHaveTextContent('MyCmd')
    expect(screen.getByTestId('seed-subtitle')).toHaveTextContent('command')
  })
})
