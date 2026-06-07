import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { GraphCanvas } from './GraphCanvas'

vi.mock('../graph/useGraphCanvas', () => ({
  useGraphCanvas: () => ({
    nodes: [
      {
        id: 'flow:1',
        type: 'codegraph',
        position: { x: 0, y: 0 },
        data: { title: 'F1', nodeType: 'flow', nodeId: 1, phase: 'idle' },
      },
    ],
    edges: [],
    onNodesChange: vi.fn(),
    onEdgesChange: vi.fn(),
    onNodeClick: vi.fn(),
  }),
}))

describe('GraphCanvas', () => {
  it('shows empty state without seed', () => {
    render(<GraphCanvas schema="S" seed={null} />)
    expect(screen.getByTestId('canvas-empty')).toBeInTheDocument()
  })

  it('renders graph canvas with seed', () => {
    render(
      <GraphCanvas
        schema="S"
        seed={{ type: 'flow', id: 1, title: 'F1', subtitle: 'main' }}
      />,
    )
    expect(screen.getByTestId('graph-canvas')).toBeInTheDocument()
  })
})
