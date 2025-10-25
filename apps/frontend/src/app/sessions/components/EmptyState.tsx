import { Button } from '@/components/ui/Button';
import { FiFileText } from 'react-icons/fi';
import { useRouter } from 'next/navigation';

export function EmptyState() {
  const router = useRouter();

  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <FiFileText className="w-20 h-20 text-deep-indigo-200 mb-6" aria-hidden="true" />
      <h2 className="text-2xl font-semibold text-deep-indigo-500 mb-2">No sessions yet</h2>
      <p className="text-base text-deep-indigo-400 mb-8 text-center max-w-md">
        Start your first interview with your AI Business Analyst to get organized, code-ready specifications
      </p>
      <Button onClick={() => router.push('/interview/new')} variant="primary" size="lg">
        Create Your First Session
      </Button>
    </div>
  );
}
