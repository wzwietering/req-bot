'use client';

import React, { createContext, useReducer, ReactNode, useCallback, useEffect } from 'react';
import { sessionsApi } from '@/lib/api/sessions';
import { Question, Requirement, ConversationState } from '@/lib/api/types';

interface InterviewState {
  sessionId: string | null;
  project: string | null;
  currentQuestion: Question | null;
  conversationState: ConversationState | null;
  isComplete: boolean;
  isLoading: boolean;
  error: string | null;
  progress: {
    totalQuestions: number;
    answeredQuestions: number;
    remainingQuestions: number;
    completionPercentage: number;
  } | null;
  requirements: Requirement[];
}

type InterviewAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SESSION_CREATED'; payload: { sessionId: string; project: string; state: ConversationState } }
  | { type: 'QUESTION_RECEIVED'; payload: { question: Question | null; isComplete: boolean; state: ConversationState } }
  | { type: 'ANSWER_SUBMITTED'; payload: { isComplete: boolean; state: ConversationState } }
  | { type: 'PROGRESS_UPDATED'; payload: InterviewState['progress'] }
  | { type: 'REQUIREMENTS_LOADED'; payload: Requirement[] }
  | { type: 'RESET' };

const initialState: InterviewState = {
  sessionId: null,
  project: null,
  currentQuestion: null,
  conversationState: null,
  isComplete: false,
  isLoading: false,
  error: null,
  progress: null,
  requirements: [],
};

function interviewReducer(state: InterviewState, action: InterviewAction): InterviewState {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload, isLoading: false };
    case 'SESSION_CREATED':
      return {
        ...state,
        sessionId: action.payload.sessionId,
        project: action.payload.project,
        conversationState: action.payload.state,
        isLoading: false,
        error: null,
      };
    case 'QUESTION_RECEIVED':
      return {
        ...state,
        currentQuestion: action.payload.question,
        isComplete: action.payload.isComplete,
        conversationState: action.payload.state,
        isLoading: false,
      };
    case 'ANSWER_SUBMITTED':
      return {
        ...state,
        isComplete: action.payload.isComplete,
        conversationState: action.payload.state,
        isLoading: false,
      };
    case 'PROGRESS_UPDATED':
      return { ...state, progress: action.payload };
    case 'REQUIREMENTS_LOADED':
      return { ...state, requirements: action.payload, isLoading: false };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

interface InterviewContextType extends InterviewState {
  startSession: (project: string) => Promise<void>;
  getNextQuestion: () => Promise<void>;
  submitAnswer: (answerText: string) => Promise<void>;
  loadRequirements: () => Promise<void>;
  updateProgress: () => Promise<void>;
  reset: () => void;
}

export const InterviewContext = createContext<InterviewContextType | null>(null);

interface InterviewProviderProps {
  children: ReactNode;
}

export function InterviewProvider({ children }: InterviewProviderProps) {
  const [state, dispatch] = useReducer(interviewReducer, initialState);

  // Try to restore session on mount
  useEffect(() => {
    const savedSessionId = localStorage.getItem('current-interview-session');
    if (savedSessionId) {
      restoreSession(savedSessionId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const restoreSession = useCallback(async (sessionId: string) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const session = await sessionsApi.getSession(sessionId);

      dispatch({
        type: 'SESSION_CREATED',
        payload: {
          sessionId: session.id,
          project: session.project,
          state: session.conversation_state,
        },
      });

      // If session is complete, load requirements
      if (session.conversation_complete) {
        dispatch({ type: 'REQUIREMENTS_LOADED', payload: session.requirements || [] });
        dispatch({
          type: 'QUESTION_RECEIVED',
          payload: {
            question: null,
            isComplete: true,
            state: session.conversation_state,
          },
        });
      }
    } catch (error) {
      console.error('Failed to restore session:', error);
      localStorage.removeItem('current-interview-session');
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, []);

  const startSession = useCallback(async (project: string) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const response = await sessionsApi.createSession({ project });
      dispatch({
        type: 'SESSION_CREATED',
        payload: {
          sessionId: response.id,
          project: response.project,
          state: response.conversation_state,
        },
      });
      // Save session ID for restoration
      localStorage.setItem('current-interview-session', response.id);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to create session';
      dispatch({ type: 'SET_ERROR', payload: message });
    }
  }, []);

  const getNextQuestion = useCallback(async () => {
    if (!state.sessionId) return;

    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const response = await sessionsApi.continueSession(state.sessionId);
      dispatch({
        type: 'QUESTION_RECEIVED',
        payload: {
          question: response.next_question,
          isComplete: response.conversation_complete,
          state: response.conversation_state,
        },
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to get next question';
      dispatch({ type: 'SET_ERROR', payload: message });
    }
  }, [state.sessionId]);

  const submitAnswer = useCallback(async (answerText: string) => {
    if (!state.sessionId) return;

    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const response = await sessionsApi.submitAnswer(state.sessionId, { answer_text: answerText });
      dispatch({
        type: 'ANSWER_SUBMITTED',
        payload: {
          isComplete: response.conversation_complete,
          state: response.conversation_state,
        },
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to submit answer';
      dispatch({ type: 'SET_ERROR', payload: message });
    }
  }, [state.sessionId]);

  const loadRequirements = useCallback(async () => {
    if (!state.sessionId) return;

    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const session = await sessionsApi.getSession(state.sessionId);
      dispatch({ type: 'REQUIREMENTS_LOADED', payload: session.requirements || [] });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load requirements';
      dispatch({ type: 'SET_ERROR', payload: message });
    }
  }, [state.sessionId]);

  const updateProgress = useCallback(async () => {
    if (!state.sessionId) return;

    try {
      const status = await sessionsApi.getSessionStatus(state.sessionId);
      dispatch({
        type: 'PROGRESS_UPDATED',
        payload: {
          totalQuestions: status.progress.total_questions,
          answeredQuestions: status.progress.answered_questions,
          remainingQuestions: status.progress.remaining_questions,
          completionPercentage: status.progress.completion_percentage,
        },
      });
    } catch (error) {
      console.error('Failed to update progress:', error);
    }
  }, [state.sessionId]);

  const reset = useCallback(() => {
    localStorage.removeItem('current-interview-session');
    dispatch({ type: 'RESET' });
  }, []);

  const value: InterviewContextType = {
    ...state,
    startSession,
    getNextQuestion,
    submitAnswer,
    loadRequirements,
    updateProgress,
    reset,
  };

  return <InterviewContext.Provider value={value}>{children}</InterviewContext.Provider>;
}
