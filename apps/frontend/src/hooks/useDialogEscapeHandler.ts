import { useEffect } from 'react';

export function useDialogEscapeHandler(
  isOpen: boolean,
  isLoading: boolean,
  onCancel: () => void
) {
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isLoading) {
        onCancel();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, isLoading, onCancel]);
}
