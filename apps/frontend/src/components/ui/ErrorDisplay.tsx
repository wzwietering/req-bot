import { Button } from './Button';
import { FiAlertCircle } from 'react-icons/fi';

interface ErrorDisplayProps {
  error: string;
  onRetry?: () => void;
}

export function ErrorDisplay({ error, onRetry }: ErrorDisplayProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <FiAlertCircle className="w-16 h-16 text-jasper-red-500 mb-4" aria-hidden="true" />
      <h2 className="text-2xl font-bold text-deep-indigo-500 mb-2">Unable to load sessions</h2>
      <p className="text-base text-deep-indigo-400 mb-6 text-center max-w-md">{error}</p>
      {onRetry && (
        <Button onClick={onRetry} variant="primary" size="md">
          Try Again
        </Button>
      )}
    </div>
  );
}
