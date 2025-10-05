'use client';

import { useRouter } from 'next/navigation';
import { SessionSummary } from '@/lib/api/types';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { formatDate } from '@/lib/utils/dates';
import { getSessionBadgeVariant, getSessionStatusText, getSessionButtonText } from '../utils/sessionStatus';
import { useSessionDelete } from '../hooks/useSessionDelete';

interface SessionCardProps {
  session: SessionSummary;
  onDelete: (id: string) => Promise<void>;
}

export function SessionCard({ session, onDelete }: SessionCardProps) {
  const router = useRouter();
  const { isDeleting, deleteError, showConfirm, handleDelete, setShowConfirm } = useSessionDelete();

  const handleCardClick = () => {
    router.push(`/interview/${session.id}`);
  };

  const cardClassName = !session.conversation_complete
    ? 'border-l-4 border-l-benzol-green-500'
    : '';

  return (
    <>
      <Card padding="md" hover className={cardClassName}>
        <div className="space-y-3">
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-lg font-semibold text-deep-indigo-500 truncate" title={session.project}>
              {session.project}
            </h3>
            <Badge variant={getSessionBadgeVariant(session)}>{getSessionStatusText(session)}</Badge>
          </div>

          <div className="text-sm space-y-1">
            <p className="text-deep-indigo-500 font-medium">Updated {formatDate(session.updated_at)}</p>
            <p className="text-deep-indigo-400">Created {formatDate(session.created_at)}</p>
          </div>

          {!session.conversation_complete && session.questions_count > 0 && (
            <div className="space-y-2">
              <ProgressBar value={session.answers_count} max={session.questions_count} showPercentage />
              <p className="text-xs text-deep-indigo-400">
                {session.answers_count}/{session.questions_count} questions •{' '}
                <span title="Requirements identified so far">{session.requirements_count} requirements</span>
              </p>
            </div>
          )}

          <div className="flex gap-2 pt-2">
            <Button onClick={handleCardClick} variant="secondary" size="md" className="flex-1">
              {getSessionButtonText(session)}
            </Button>
            <Button
              onClick={(e) => {
                e.stopPropagation();
                setShowConfirm(true);
              }}
              variant="danger"
              size="md"
              disabled={isDeleting}
            >
              {isDeleting ? 'Deleting...' : 'Delete'}
            </Button>
          </div>
        </div>
      </Card>

      <ConfirmDialog
        isOpen={showConfirm}
        title="Delete Session"
        message={`Are you sure you want to delete "${session.project}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        onConfirm={() => handleDelete(onDelete, session.id)}
        onCancel={() => setShowConfirm(false)}
        error={deleteError}
        isLoading={isDeleting}
      />
    </>
  );
}
