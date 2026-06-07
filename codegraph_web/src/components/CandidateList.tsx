import type { GraphNode } from '../types/graph'

type Props = {
  candidates: GraphNode[]
  onSelect: (node: GraphNode) => void
}

export function CandidateList({ candidates, onSelect }: Props) {
  return (
    <div data-testid="candidate-list" className="candidate-list">
      <p>Multiple matches — choose one:</p>
      <ul>
        {candidates.map((node) => (
          <li key={`${node.type}-${node.id}`}>
            <button type="button" onClick={() => onSelect(node)}>
              <span data-testid="candidate-title">{node.title ?? node.type}</span>
              {node.subtitle != null && node.subtitle !== '' && (
                <span data-testid="candidate-subtitle"> — {node.subtitle}</span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
