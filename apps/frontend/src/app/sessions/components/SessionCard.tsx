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

interface SessionCardProps {
  session: SessionSummary;
  onDelete: (id: string) => Promise<void>;
}

export function SessionCard({ session, onDelete }: SessionCardProps) {
  const router = useRouter();
  const [isDeleting, setIsDeleting] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const getBadgeVariant = () => {
    if (session.conversation_state === 'failed') return 'failed';
    if (session.conversation_complete) return 'completed';
    if (session.conversation_state === 'processing_answer' || session.conversation_state === 'generating_questions') {
      return 'processing';
    }
    return 'active';
  };

  const getStatusText = () => {
    if (session.conversation_complete) return 'Completed';
    if (session.conversation_state === 'failed') return 'Failed';
    return 'Active';
  };

  const getButtonText = () => {
    if (session.conversation_complete) return 'View Details';
    return 'Continue';
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onDelete(session.id);
    } catch {
      alert('Failed to delete session');
    } finally {
      setIsDeleting(false);
      setShowConfirm(false);
    }
  };

  const handleCardClick = () => {
    localStorage.setItem('current-interview-session', session.id);
    router.push('/interview/new');
  };

  return (
    <>
      <Card padding="md" hover>
        <div className="space-y-3">
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-lg font-semibold text-deep-indigo-500 truncate">{session.project}</h3>
            <Badge variant={getBadgeVariant()}>{getStatusText()}</Badge>
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
              {getButtonText()}
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
        onConfirm={handleDelete}
        onCancel={() => setShowConfirm(false)}
      />
    </>
  );
}
