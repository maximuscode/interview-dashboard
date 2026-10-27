/** Inline error shown above content that is still on screen. */
export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3"
    >
      <p className="text-sm text-amber-900">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="ml-auto rounded-md border border-amber-400 px-3 py-1 text-sm font-medium text-amber-900 hover:bg-amber-100"
        >
          Retry
        </button>
      )}
    </div>
  )
}
