import { useState } from 'react';

interface UseSessionDeleteResult {
  isDeleting: boolean;
  deleteError: string | null;
  showConfirm: boolean;
  handleDelete: (onDelete: (id: string) => Promise<void>, sessionId: string) => Promise<void>;
  setShowConfirm: (show: boolean) => void;
}

export function useSessionDelete(): UseSessionDeleteResult {
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleDelete = async (onDelete: (id: string) => Promise<void>, sessionId: string) => {
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await onDelete(sessionId);
      setShowConfirm(false);
    } catch (error) {
      console.error('Failed to delete session:', error);
      setDeleteError(error instanceof Error ? error.message : 'Failed to delete session');
    } finally {
      setIsDeleting(false);
    }
  };

  return {
    isDeleting,
    deleteError,
    showConfirm,
    handleDelete,
    setShowConfirm,
  };
}
