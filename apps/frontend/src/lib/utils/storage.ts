/**
 * Safe wrapper around localStorage that handles errors gracefully.
 * Useful for environments where localStorage may not be available
 * (e.g., private browsing, quota exceeded, SSR).
 */

export interface StorageResult<T = string> {
  success: boolean;
  data?: T;
  error?: string;
}

/**
 * Safely sets an item in localStorage.
 *
 * @param key - The storage key
 * @param value - The value to store
 * @returns Result object with success status and optional error
 *
 * @example
 * const result = safeLocalStorage.setItem('session-id', '123');
 * if (!result.success) {
 *   console.error('Failed to save:', result.error);
 * }
 */
function setItem(key: string, value: string): StorageResult {
  try {
    localStorage.setItem(key, value);
    return { success: true };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error(`localStorage.setItem failed for key "${key}":`, errorMessage);
    return {
      success: false,
      error: errorMessage
    };
  }
}

/**
 * Safely retrieves an item from localStorage.
 *
 * @param key - The storage key
 * @returns Result object with success status and optional data
 *
 * @example
 * const result = safeLocalStorage.getItem('session-id');
 * if (result.success) {
 *   console.log('Session ID:', result.data);
 * }
 */
function getItem(key: string): StorageResult {
  try {
    const data = localStorage.getItem(key);
    return { success: true, data: data || undefined };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error(`localStorage.getItem failed for key "${key}":`, errorMessage);
    return {
      success: false,
      error: errorMessage
    };
  }
}

/**
 * Safely removes an item from localStorage.
 *
 * @param key - The storage key
 * @returns Result object with success status
 */
function removeItem(key: string): StorageResult {
  try {
    localStorage.removeItem(key);
    return { success: true };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error(`localStorage.removeItem failed for key "${key}":`, errorMessage);
    return {
      success: false,
      error: errorMessage
    };
  }
}

/**
 * Safely clears all items from localStorage.
 *
 * @returns Result object with success status
 */
function clear(): StorageResult {
  try {
    localStorage.clear();
    return { success: true };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('localStorage.clear failed:', errorMessage);
    return {
      success: false,
      error: errorMessage
    };
  }
}

export const safeLocalStorage = {
  setItem,
  getItem,
  removeItem,
  clear,
};
