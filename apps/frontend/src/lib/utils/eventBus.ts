/**
 * Typed event bus for application-wide events.
 *
 * This module provides type-safe event dispatching and listening for custom events.
 * Currently supports:
 * - 'quota-update': Fired when user's quota usage changes (e.g., after creating a session)
 */

/**
 * Dispatch a quota-update event to notify the UI to refetch quota data.
 *
 * This should be called after any action that changes quota usage:
 * - After successfully creating a new interview session
 * - After generating AI questions
 * - After any operation that consumes quota
 *
 * @example
 * // In your session creation code:
 * const session = await createSession();
 * dispatchQuotaUpdate();
 */
export function dispatchQuotaUpdate(): void {
  if (typeof window === "undefined") return;

  const event = new CustomEvent("quota-update");
  window.dispatchEvent(event);
}

/**
 * Listen for quota-update events.
 *
 * @param callback - Function to call when quota is updated
 * @returns Cleanup function to remove the event listener
 *
 * @example
 * useEffect(() => {
 *   const cleanup = onQuotaUpdate(() => {
 *     refetchQuotaData();
 *   });
 *   return cleanup;
 * }, []);
 */
export function onQuotaUpdate(callback: () => void): () => void {
  if (typeof window === "undefined") return () => {};

  const handler = () => callback();
  window.addEventListener("quota-update", handler);

  return () => {
    window.removeEventListener("quota-update", handler);
  };
}
