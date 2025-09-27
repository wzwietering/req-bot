export function PlusIcon({ className = "w-6 h-6" }: { className?: string }) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" className={className}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
    </svg>
  );
}