import { ANSWER_CHARACTER_LIMIT, QUESTION_CHARACTER_LIMIT } from '@/types/form';

export function sanitizeInput(text: string): string {
  return text.trim().replace(/[\x00-\x1F\x7F]/g, '');
}

export interface ValidationResult {
  isValid: boolean;
  error: string | null;
}

export function validateAnswer(text: string): ValidationResult {
  const sanitized = sanitizeInput(text);

  if (sanitized.length === 0) {
    return { isValid: false, error: 'Answer cannot be empty' };
  }

  if (sanitized.length > ANSWER_CHARACTER_LIMIT.max) {
    return {
      isValid: false,
      error: `Answer exceeds maximum length of ${ANSWER_CHARACTER_LIMIT.max} characters`,
    };
  }

  return { isValid: true, error: null };
}

export function validateQuestion(text: string): ValidationResult {
  const sanitized = sanitizeInput(text);

  if (sanitized.length === 0) {
    return { isValid: false, error: 'Question cannot be empty' };
  }

  if (sanitized.length > QUESTION_CHARACTER_LIMIT.max) {
    return {
      isValid: false,
      error: `Question exceeds maximum length of ${QUESTION_CHARACTER_LIMIT.max} characters`,
    };
  }

  return { isValid: true, error: null };
}
