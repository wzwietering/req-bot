import { useEffect, useRef } from 'react';

function getFocusableElements(container: HTMLElement) {
  const elements = container.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  const firstElement = elements[0] as HTMLElement;
  const lastElement = elements[elements.length - 1] as HTMLElement;
  return { firstElement, lastElement };
}

function handleShiftTab(firstElement: HTMLElement, lastElement: HTMLElement) {
  if (document.activeElement === firstElement) {
    lastElement?.focus();
    return true;
  }
  return false;
}

function handleForwardTab(firstElement: HTMLElement, lastElement: HTMLElement) {
  if (document.activeElement === lastElement) {
    firstElement?.focus();
    return true;
  }
  return false;
}

function createTabHandler(firstElement: HTMLElement, lastElement: HTMLElement) {
  return (e: KeyboardEvent) => {
    if (e.key !== 'Tab') return;

    const isShiftTab = e.shiftKey;
    const shouldWrap = isShiftTab
      ? handleShiftTab(firstElement, lastElement)
      : handleForwardTab(firstElement, lastElement);

    if (shouldWrap) {
      e.preventDefault();
    }
  };
}

export function useFocusTrap(isOpen: boolean, dialogRef: React.RefObject<HTMLDivElement | null>) {
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    previousFocusRef.current = document.activeElement as HTMLElement;

    const dialog = dialogRef.current;
    if (!dialog) return;

    const { firstElement, lastElement } = getFocusableElements(dialog);
    firstElement?.focus();

    const handleTab = createTabHandler(firstElement, lastElement);
    document.addEventListener('keydown', handleTab);

    return () => {
      document.removeEventListener('keydown', handleTab);
      previousFocusRef.current?.focus();
    };
  }, [isOpen, dialogRef]);
}
