type Props = {
  message?: string | null
  onRetry: () => void
}

export function ErrorState({ message, onRetry }: Props) {
  return (
    <div data-testid="error-state" className="status-error" role="alert">
      <p>{message ?? 'Something went wrong while searching.'}</p>
      <button type="button" onClick={onRetry}>
        Retry
      </button>
    </div>
  )
}
