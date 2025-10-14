export type CharCountColor = 'gray' | 'amber' | 'red';

export interface CharacterLimit {
  max: number;
  warningThreshold: number;
}

export const ANSWER_CHARACTER_LIMIT: CharacterLimit = {
  max: 5000,
  warningThreshold: 4500,
};

export const QUESTION_CHARACTER_LIMIT: CharacterLimit = {
  max: 1000,
  warningThreshold: 900,
};

export function getCharCountColor(count: number, limit: CharacterLimit): CharCountColor {
  if (count > limit.max) return 'red';
  if (count > limit.warningThreshold) return 'amber';
  return 'gray';
}
