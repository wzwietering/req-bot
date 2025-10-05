'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { SessionSummary } from '@/lib/api/types';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { formatDate } from '@/lib/utils/dates';
import { safeLocalStorage } from '@/lib/utils/storage';
import { getSessionBadgeVariant, getSessionStatusText, getSessionButtonText } from '../utils/sessionStatus';
import { useSessionDelete } from '../hooks/useSessionDelete';

interface SessionCardProps {
  session: SessionSummary;
  onDelete: (id: string) => Promise<void>;
}

export function SessionCard({ session, onDelete }: SessionCardProps) {
  const router = useRouter();
  const { isDeleting, deleteError, showConfirm, handleDelete, setShowConfirm } = useSessionDelete();
  const [storageError, setStorageError] = useState<string | null>(null);

  const handleCardClick = () => {
    const result = safeLocalStorage.setItem('current-interview-session', session.id);

    if (!result.success) {
      setStorageError(
        'Unable to save session. Please check your browser settings and try again.'
      );
      return;
    }

    router.push('/interview/new');
  };

  return (
    <>
      <Card padding="md" hover>
        <div className="space-y-3">
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-lg font-semibold text-deep-indigo-500 truncate">{session.project}</h3>
            <Badge variant={getSessionBadgeVariant(session)}>{getSessionStatusText(session)}</Badge>
          </div>

          <div className="text-sm text-deep-indigo-400 space-y-1">
            <p>Created {formatDate(session.created_at)}</p>
            <p>Updated {formatDate(session.updated_at)}</p>
          </div>

          {!session.conversation_complete && session.questions_count > 0 && (
            <div className="space-y-2">
              <ProgressBar value={session.answers_count} max={session.questions_count} />
              <p className="text-xs text-deep-indigo-400">
                {session.answers_count}/{session.questions_count} questions • {session.requirements_count}{' '}
                requirements
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
              variant="outline"
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

      <ConfirmDialog
        isOpen={!!storageError}
        title="Storage Error"
        message={storageError || ''}
        confirmText="OK"
        onConfirm={() => setStorageError(null)}
        onCancel={() => setStorageError(null)}
        isLoading={false}
      />
    </>
  );
}
