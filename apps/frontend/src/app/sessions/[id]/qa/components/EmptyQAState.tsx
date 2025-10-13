import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';

interface EmptyQAStateProps {
  sessionId: string;
}

export function EmptyQAState({ sessionId }: EmptyQAStateProps) {
  const router = useRouter();

  return (
    <div className="text-center py-12 max-w-md mx-auto">
      <p className="text-deep-indigo-500 font-medium mb-2 text-lg">No Questions Yet</p>
      <p className="text-deep-indigo-400 mb-4">
        Questions will appear here after you start your interview session.
      </p>
      <Button onClick={() => router.push(`/interview/${sessionId}`)} variant="primary" size="md">
        Start Interview
      </Button>
    </div>
  );
}
