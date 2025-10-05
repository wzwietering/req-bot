import { useContext } from 'react';
import { InterviewContext } from '@/components/interview/InterviewProvider';

export function useInterview() {
  const context = useContext(InterviewContext);

  if (!context) {
    throw new Error('useInterview must be used within InterviewProvider');
  }

  return context;
}
