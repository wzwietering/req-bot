import {
  Session,
  SessionSummary,
  CreateSessionRequest,
  CreateSessionResponse,
  ContinueSessionResponse,
  SubmitAnswerRequest,
  SubmitAnswerResponse,
  SessionStatusResponse,
  CurrentQuestionResponse,
  SessionQAResponse,
  QuestionCreateRequest,
  QuestionDetailResponse,
  AnswerUpdateRequest,
  AnswerDetailResponse,
} from './types';
import { apiClient } from './apiClient';

export const sessionsApi = {
  async createSession(data: CreateSessionRequest): Promise<CreateSessionResponse> {
    return apiClient.post<CreateSessionResponse>('/api/v1/sessions', data);
  },

  async listSessions(): Promise<SessionSummary[]> {
    const data = await apiClient.get<{ sessions: SessionSummary[] }>('/api/v1/sessions');
    return data.sessions;
  },

  async getSession(sessionId: string): Promise<Session> {
    return apiClient.get<Session>(`/api/v1/sessions/${sessionId}`);
  },

  async deleteSession(sessionId: string): Promise<void> {
    await apiClient.delete(`/api/v1/sessions/${sessionId}`);
  },

  async continueSession(sessionId: string): Promise<ContinueSessionResponse> {
    return apiClient.post<ContinueSessionResponse>(`/api/v1/sessions/${sessionId}/continue`);
  },

  async submitAnswer(sessionId: string, data: SubmitAnswerRequest): Promise<SubmitAnswerResponse> {
    return apiClient.post<SubmitAnswerResponse>(`/api/v1/sessions/${sessionId}/answers`, data);
  },

  async getCurrentQuestion(sessionId: string): Promise<CurrentQuestionResponse> {
    return apiClient.get<CurrentQuestionResponse>(`/api/v1/sessions/${sessionId}/questions/current`);
  },

  async getSessionStatus(sessionId: string): Promise<SessionStatusResponse> {
    return apiClient.get<SessionStatusResponse>(`/api/v1/sessions/${sessionId}/status`);
  },

  async getSessionQA(sessionId: string): Promise<SessionQAResponse> {
    return apiClient.get<SessionQAResponse>(`/api/v1/sessions/${sessionId}/qa`);
  },

  async createQuestion(
    sessionId: string,
    data: QuestionCreateRequest
  ): Promise<QuestionDetailResponse> {
    return apiClient.post<QuestionDetailResponse>(
      `/api/v1/sessions/${sessionId}/questions`,
      data
    );
  },

  async deleteQuestion(sessionId: string, questionId: string): Promise<void> {
    await apiClient.delete(`/api/v1/sessions/${sessionId}/questions/${questionId}`);
  },

  async updateAnswer(
    sessionId: string,
    questionId: string,
    data: AnswerUpdateRequest
  ): Promise<AnswerDetailResponse> {
    return apiClient.put<AnswerDetailResponse>(
      `/api/v1/sessions/${sessionId}/answers/${questionId}`,
      data
    );
  },

  async deleteAnswer(sessionId: string, questionId: string): Promise<void> {
    await apiClient.delete(`/api/v1/sessions/${sessionId}/answers/${questionId}`);
  },
};
