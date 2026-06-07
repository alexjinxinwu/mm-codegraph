import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { StatusPanel } from './StatusPanel'

describe('StatusPanel', () => {
  it('shows loading state', () => {
    render(
      <StatusPanel
        phase="loading"
        candidates={[]}
        onSelectCandidate={vi.fn()}
        onRetry={vi.fn()}
      />,
    )
    expect(screen.getByTestId('loading-state')).toHaveTextContent('Searching')
  })

  it('shows empty state for notFound', () => {
    render(
      <StatusPanel
        phase="notFound"
        candidates={[]}
        onSelectCandidate={vi.fn()}
        onRetry={vi.fn()}
      />,
    )
    expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    expect(screen.queryByTestId('error-state')).not.toBeInTheDocument()
  })

  it('shows candidate list for multiple', () => {
    render(
      <StatusPanel
        phase="multiple"
        candidates={[
          { type: 'flow', id: 1, title: 'F1', subtitle: 'main' },
          { type: 'flow', id: 2, title: 'F2', subtitle: 'draft' },
        ]}
        onSelectCandidate={vi.fn()}
        onRetry={vi.fn()}
      />,
    )

    expect(screen.getAllByTestId('candidate-title')).toHaveLength(2)
    expect(screen.getAllByTestId('candidate-subtitle')).toHaveLength(2)
  })

  it('shows error state with retry', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()

    render(
      <StatusPanel
        phase="error"
        candidates={[]}
        errorMessage="HTTP 500"
        onSelectCandidate={vi.fn()}
        onRetry={onRetry}
      />,
    )

    expect(screen.getByTestId('error-state')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalled()
  })
})
