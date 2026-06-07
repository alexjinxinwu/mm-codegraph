import type { GraphNode } from '../types/graph'
import type { Phase } from '../hooks/useResolveSearch'
import { CandidateList } from './CandidateList'
import { EmptyState } from './EmptyState'
import { ErrorState } from './ErrorState'

type Props = {
  phase: Phase
  candidates: GraphNode[]
  errorMessage?: string | null
  onSelectCandidate: (node: GraphNode) => void
  onRetry: () => void
}

export function StatusPanel({
  phase,
  candidates,
  errorMessage,
  onSelectCandidate,
  onRetry,
}: Props) {
  if (phase === 'loading') {
    return (
      <div data-testid="loading-state" aria-busy="true">
        Searching…
      </div>
    )
  }

  if (phase === 'notFound') {
    return <EmptyState />
  }

  if (phase === 'multiple') {
    return <CandidateList candidates={candidates} onSelect={onSelectCandidate} />
  }

  if (phase === 'error') {
    return <ErrorState message={errorMessage} onRetry={onRetry} />
  }

  return null
}
