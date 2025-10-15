export const FEEDBACK_DURATIONS = {
  SUCCESS: 2000,
  ERROR: 3000,
  INFO: 3000,
} as const;

export const MAX_DISPLAY_LENGTH = {
  QUESTION_TRUNCATE: 80,
} as const;

export const UNSAVED_CHANGES_THRESHOLD = 50;

export const CHAR_COUNT_COLOR_CLASSES = {
  gray: 'text-deep-indigo-400',
  amber: 'text-amber-600 font-medium',
  red: 'text-jasper-red-600 font-semibold',
} as const;
