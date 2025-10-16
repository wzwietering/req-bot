import { useDialogEscapeHandler } from './useDialogEscapeHandler';
import { useFocusTrap } from './useFocusTrap';

export function useDialogAccessibility(
  isOpen: boolean,
  dialogRef: React.RefObject<HTMLDivElement | null>,
  onClose: () => void,
  isLoading: boolean = false
) {
  useDialogEscapeHandler(isOpen, isLoading, onClose);
  useFocusTrap(isOpen, dialogRef);
}
