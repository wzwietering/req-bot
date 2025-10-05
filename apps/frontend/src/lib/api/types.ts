import { components } from '@req-bot/shared-types';

export type Session = components['schemas']['SessionDetailResponse'];
export type SessionSummary = components['schemas']['SessionSummary'];
export type Question = components['schemas']['Question'];
export type Answer = components['schemas']['Answer'];
export type ConversationState = components['schemas']['ConversationState'];
export type Requirement = components['schemas']['Requirement'];

export interface CreateSessionRequest {
  project: string;
}

export interface CreateSessionResponse {
  id: string;
  project: string;
  conversation_state: ConversationState;
  created_at: string;
}

export interface ContinueSessionResponse {
  session_id: string;
  next_question: Question | null;
  conversation_complete: boolean;
  conversation_state: ConversationState;
}

export interface SubmitAnswerRequest {
  answer_text: string;
}

export interface SubmitAnswerResponse {
  session_id: string;
  question: Question;
  answer: Answer;
  conversation_complete: boolean;
  conversation_state: ConversationState;
  requirements_generated: boolean;
}

export interface SessionStatusResponse {
  session_id: string;
  conversation_state: ConversationState;
  conversation_complete: boolean;
  current_question: Question | null;
  progress: {
    total_questions: number;
    answered_questions: number;
    remaining_questions: number;
    completion_percentage: number;
  };
}

export interface CurrentQuestionResponse {
  current_question: Question | null;
  conversation_complete: boolean;
  conversation_state: ConversationState;
}
