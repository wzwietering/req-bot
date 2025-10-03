import { User, OAuthProvider, AuthError } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export class AuthApiError extends Error {
  constructor(
    message: string,
    public code: string,
    public status?: number,
    public provider?: OAuthProvider
  ) {
    super(message);
    this.name = 'AuthApiError';
  }
}

export const authApi = {
  async getCurrentUser(): Promise<User | null> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.status === 401) {
        return null;
      }

      if (!response.ok) {
        throw new AuthApiError(
          'Failed to fetch user profile',
          'fetch_user_failed',
          response.status
        );
      }

      return await response.json();
    } catch (error) {
      if (error instanceof AuthApiError) {
        throw error;
      }

      throw new AuthApiError(
        'Network error while fetching user profile',
        'network_error'
      );
    }
  },

  initiateOAuthLogin(provider: OAuthProvider): void {
    const state = generateRandomState();

    if (typeof window !== 'undefined') {
      sessionStorage.setItem('oauth_state', state);
      window.location.href = `${API_BASE_URL}/api/v1/auth/login/${provider}`;
    }
  },

  async logout(): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });

      if (!response.ok && response.status !== 200) {
        console.warn('Logout request failed, but proceeding with local cleanup');
      }
    } catch (error) {
      console.warn('Logout request failed, but proceeding with local cleanup:', error);
    }
  },

  async refreshToken(): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      return response.ok;
    } catch (error) {
      console.error('Token refresh failed:', error);
      return false;
    }
  },

  async getAuthStatus(): Promise<{
    service_status: string;
    providers: Record<string, string>;
    available_providers: string[];
  }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/status`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new AuthApiError(
          'Failed to fetch auth status',
          'auth_status_failed',
          response.status
        );
      }

      return await response.json();
    } catch (error) {
      if (error instanceof AuthApiError) {
        throw error;
      }

      throw new AuthApiError(
        'Network error while fetching auth status',
        'network_error'
      );
    }
  },
};

export function generateRandomState(): string {
  const array = new Uint8Array(16);
  if (typeof window !== 'undefined' && window.crypto) {
    window.crypto.getRandomValues(array);
  } else {
    for (let i = 0; i < array.length; i++) {
      array[i] = Math.floor(Math.random() * 256);
    }
  }
  return btoa(String.fromCharCode.apply(null, Array.from(array)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}

export function validateOAuthState(returnedState: string | null): boolean {
  if (typeof window === 'undefined') {
    return false;
  }

  const storedState = sessionStorage.getItem('oauth_state');

  if (!returnedState || !storedState) {
    return false;
  }

  const isValid = returnedState === storedState;

  if (isValid) {
    sessionStorage.removeItem('oauth_state');
  }

  return isValid;
}

export function parseOAuthError(params: URLSearchParams): AuthError | null {
  const error = params.get('error');
  const errorDescription = params.get('error_description');

  if (!error) {
    return null;
  }

  const errorMessages: Record<string, string> = {
    access_denied: 'You cancelled the login process. Please try again.',
    invalid_request: 'Invalid login request. Please try again.',
    unauthorized_client: 'Login configuration error. Please contact support.',
    unsupported_response_type: 'Login configuration error. Please contact support.',
    invalid_scope: 'Login configuration error. Please contact support.',
    server_error: 'Authentication service error. Please try again.',
    temporarily_unavailable: 'Authentication service is temporarily unavailable. Please try again.',
  };

  return {
    code: error,
    message: errorMessages[error] || errorDescription || 'An unknown error occurred during login.',
  };
}