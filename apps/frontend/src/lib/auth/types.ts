export interface User {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
  provider: 'google' | 'github' | 'microsoft';
}

export interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
}

export type OAuthProvider = 'google' | 'github' | 'microsoft';

export interface OAuthProviderConfig {
  name: OAuthProvider;
  displayName: string;
  brandColor: string;
  icon: React.ComponentType<{ className?: string }>;
}

export interface AuthTokens {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string;
  user: User;
}

export interface AuthError {
  code: string;
  message: string;
  provider?: OAuthProvider;
}

export interface OAuthCallbackParams {
  code?: string;
  state?: string;
  error?: string;
  error_description?: string;
}

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
  login: (provider: OAuthProvider) => void;
  logout: () => Promise<void>;
  clearError: () => void;
  checkAuthStatus: () => Promise<void>;
}