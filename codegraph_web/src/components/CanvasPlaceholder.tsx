import type { GraphNode } from '../types/graph'

type Props = {
  seed: GraphNode | null
}

export function CanvasPlaceholder({ seed }: Props) {
  if (!seed) {
    return (
      <div data-testid="canvas-empty" className="canvas-empty">
        Select an entry to begin
      </div>
    )
  }

  return (
    <div data-testid="canvas-seed" className="canvas-seed">
      <span data-testid="seed-type">{seed.type}</span>
      <span data-testid="seed-id">{seed.id}</span>
      {seed.title != null && seed.title !== '' && (
        <span data-testid="seed-title">{seed.title}</span>
      )}
      {seed.subtitle != null && seed.subtitle !== '' && (
        <span data-testid="seed-subtitle">{seed.subtitle}</span>
      )}
    </div>
  )
}
