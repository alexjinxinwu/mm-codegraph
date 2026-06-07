import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ReactFlowProvider, type NodeProps } from '@xyflow/react'
import { CodegraphNode, type CodegraphNodeData } from './CodegraphNode'

function TestNode(props: { data: CodegraphNodeData }) {
  const Node = CodegraphNode as React.ComponentType<NodeProps>
  return (
    <ReactFlowProvider>
      <Node
        id="flow:1"
        type="codegraph"
        data={props.data}
        selected={false}
        dragging={false}
        zIndex={0}
        isConnectable
        positionAbsoluteX={0}
        positionAbsoluteY={0}
      />
    </ReactFlowProvider>
  )
}

describe('CodegraphNode', () => {
  it('renders title and subtitle', () => {
    render(
      <TestNode
        data={{
          nodeType: 'flow',
          nodeId: 1,
          title: 'MyFlow',
          subtitle: 'main',
          phase: 'idle',
        }}
      />,
    )

    expect(screen.getByTestId('seed-title')).toHaveTextContent('MyFlow')
    expect(screen.getByTestId('seed-subtitle')).toHaveTextContent('main')
  })

  it('shows loading overlay', () => {
    render(
      <TestNode
        data={{ nodeType: 'flow', nodeId: 1, title: 'F', phase: 'loading' }}
      />,
    )
    expect(screen.getByTestId('node-loading')).toBeInTheDocument()
  })

  it('shows error overlay with retry', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()

    render(
      <TestNode
        data={{
          nodeType: 'flow',
          nodeId: 1,
          title: 'F',
          phase: 'error',
          onRetry,
        }}
      />,
    )
    await user.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalled()
  })
})
