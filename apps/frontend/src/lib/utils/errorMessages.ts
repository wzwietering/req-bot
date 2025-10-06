/**
 * Maps technical error messages to user-friendly messages
 */
export function getUserFriendlyErrorMessage(error: string | Error): string {
  const errorMessage = typeof error === 'string' ? error : error.message;
  const lowerError = errorMessage.toLowerCase();

  // Network errors
  if (lowerError.includes('failed to fetch') || lowerError.includes('network')) {
    return 'Unable to connect to the server. Please check your internet connection and try again.';
  }

  // Authentication errors
  if (lowerError.includes('401') || lowerError.includes('unauthorized')) {
    return 'Your session has expired. Please log in again.';
  }

  if (lowerError.includes('403') || lowerError.includes('forbidden')) {
    return 'You don\'t have permission to access this resource.';
  }

  // Not found errors
  if (lowerError.includes('404') || lowerError.includes('not found')) {
    return 'The requested resource could not be found.';
  }

  // Server errors
  if (lowerError.includes('500') || lowerError.includes('internal server')) {
    return 'A server error occurred. Please try again later.';
  }

  if (lowerError.includes('503') || lowerError.includes('service unavailable')) {
    return 'The service is temporarily unavailable. Please try again in a few moments.';
  }

  // Timeout errors
  if (lowerError.includes('timeout')) {
    return 'The request took too long to complete. Please try again.';
  }

  // CORS errors
  if (lowerError.includes('cors')) {
    return 'A connection error occurred. Please contact support if this persists.';
  }

  // Storage errors
  if (lowerError.includes('storage') || lowerError.includes('quota')) {
    return 'Browser storage is full or unavailable. Please clear your browser data and try again.';
  }

  // Validation errors (pass through as they're usually user-friendly)
  if (lowerError.includes('invalid') || lowerError.includes('required')) {
    return errorMessage;
  }

  // Default fallback
  return errorMessage || 'An unexpected error occurred. Please try again.';
}
