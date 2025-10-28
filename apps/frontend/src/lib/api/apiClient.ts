/**
 * API Client with automatic token refresh
 *
 * This client wraps fetch to provide:
 * - Automatic token refresh on 401 errors
 * - Token rotation for security
 * - Centralized error handling
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

/**
 * Refresh the access token using the refresh token cookie
 */
async function refreshAccessToken(): Promise<boolean> {
  // If already refreshing, wait for that to complete
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }

  isRefreshing = true;
  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        credentials: 'include', // Send cookies (refresh token)
      });

      if (!response.ok) {
        // Refresh failed - clear tokens and redirect to login
        localStorage.removeItem('current-interview-session');
        if (typeof window !== 'undefined') {
          window.location.href = '/';
        }
        return false;
      }

      // Refresh succeeded - new tokens are in cookies
      return true;
    } catch (error) {
      console.error('Token refresh failed:', error);
      return false;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * Enhanced fetch with automatic token refresh
 */
export async function apiFetch<T = unknown>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

  // Ensure credentials are included
  const fetchOptions: RequestInit = {
    ...options,
    credentials: 'include',
    headers: {
      ...options.headers,
    },
  };

  // First attempt
  let response = await fetch(url, fetchOptions);

  // If 401 (Unauthorized), try refreshing token
  if (response.status === 401) {
    const refreshed = await refreshAccessToken();

    if (refreshed) {
      // Retry the original request with new token
      response = await fetch(url, fetchOptions);
    } else {
      // Refresh failed - throw error
      throw new ApiError(
        'Authentication failed. Please log in again.',
        401,
        'auth_failed'
      );
    }
  }

  // Handle other error responses
  if (!response.ok) {
    const errorText = await response.text();
    let errorData: { message?: string; error?: string; detail?: string } | null = null;

    try {
      errorData = JSON.parse(errorText);
    } catch {
      // Response is not JSON
    }

    // Special handling for 429 (Rate Limit/Quota Exceeded)
    if (response.status === 429) {
      const message = errorData?.detail || errorData?.message ||
        "You've reached your quota limit. Please wait or upgrade to Pro.";

      throw new ApiError(
        message,
        429,
        'quota_exceeded'
      );
    }

    throw new ApiError(
      errorData?.detail || errorData?.message || `API Error: ${response.status} ${errorText}`,
      response.status,
      errorData?.error || 'api_error'
    );
  }

  // Success - parse and return JSON
  return response.json();
}

/**
 * Convenience methods for common HTTP verbs
 */
export const apiClient = {
  get: <T = unknown>(endpoint: string, options?: RequestInit) =>
    apiFetch<T>(endpoint, { ...options, method: 'GET' }),

  post: <T = unknown>(endpoint: string, data?: unknown, options?: RequestInit) =>
    apiFetch<T>(endpoint, {
      ...options,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      body: data ? JSON.stringify(data) : undefined,
    }),

  put: <T = unknown>(endpoint: string, data?: unknown, options?: RequestInit) =>
    apiFetch<T>(endpoint, {
      ...options,
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      body: data ? JSON.stringify(data) : undefined,
    }),

  delete: <T = unknown>(endpoint: string, options?: RequestInit) =>
    apiFetch<T>(endpoint, { ...options, method: 'DELETE' }),
};
