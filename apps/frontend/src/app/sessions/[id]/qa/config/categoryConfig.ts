import { Question } from '@/lib/api/types';

export const categoryConfig: Record<
  Question['category'],
  { label: string; colors: string; borderColor: string; badgeColors: string }
> = {
  scope: {
    label: 'Project Scope',
    colors: 'bg-indigo-100 text-indigo-700',
    borderColor: 'border-l-indigo-500',
    badgeColors: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  },
  users: {
    label: 'Users & Stakeholders',
    colors: 'bg-purple-100 text-purple-700',
    borderColor: 'border-l-purple-500',
    badgeColors: 'bg-purple-50 text-purple-700 border-purple-200',
  },
  constraints: {
    label: 'Constraints',
    colors: 'bg-amber-100 text-amber-800',
    borderColor: 'border-l-amber-500',
    badgeColors: 'bg-amber-50 text-amber-700 border-amber-200',
  },
  nonfunctional: {
    label: 'Non-Functional Requirements',
    colors: 'bg-blue-100 text-blue-700',
    borderColor: 'border-l-blue-500',
    badgeColors: 'bg-blue-50 text-blue-700 border-blue-200',
  },
  interfaces: {
    label: 'Interfaces & Integrations',
    colors: 'bg-teal-100 text-teal-700',
    borderColor: 'border-l-teal-500',
    badgeColors: 'bg-teal-50 text-teal-700 border-teal-200',
  },
  data: {
    label: 'Data Requirements',
    colors: 'bg-cyan-100 text-cyan-800',
    borderColor: 'border-l-cyan-500',
    badgeColors: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  },
  risks: {
    label: 'Risks & Assumptions',
    colors: 'bg-orange-100 text-orange-700',
    borderColor: 'border-l-orange-500',
    badgeColors: 'bg-rose-50 text-rose-700 border-rose-200',
  },
  success: {
    label: 'Success Criteria',
    colors: 'bg-benzol-green-100 text-benzol-green-700',
    borderColor: 'border-l-benzol-green-500',
    badgeColors: 'bg-green-50 text-green-700 border-green-200',
  },
};
