import { SessionSummary } from '@/lib/api/types';

export function getSessionBadgeVariant(session: SessionSummary) {
  if (session.conversation_state === 'failed') return 'failed';
  if (session.conversation_complete) return 'completed';
  if (session.conversation_state === 'processing_answer' || session.conversation_state === 'generating_questions') {
    return 'processing';
  }
  return 'active';
}

export function getSessionStatusText(session: SessionSummary): string {
  if (session.conversation_complete) return 'Completed';
  if (session.conversation_state === 'failed') return 'Failed';
  return 'Active';
}

export function getSessionButtonText(session: SessionSummary): string {
  if (session.conversation_complete) return 'View Details';
  return 'Continue';
}
