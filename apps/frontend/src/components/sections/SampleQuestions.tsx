const questionCategories = [
  { category: 'SCOPE', question: 'What problem are we solving with this project?', color: 'benzol-green' as const },
  { category: 'USERS', question: 'Who are the primary users and what are their key jobs?', color: 'jasper-red' as const },
  { category: 'CONSTRAINTS', question: 'What technical, budget, or timeline constraints do we have?', color: 'jasper-red' as const },
  { category: 'SUCCESS', question: 'How will we measure the success of this project?', color: 'benzol-green' as const }
];

const colorStyles = {
  'benzol-green': {
    border: 'border-benzol-green-500',
    text: 'text-benzol-green-600'
  },
  'jasper-red': {
    border: 'border-jasper-red-500',
    text: 'text-jasper-red-600'
  }
} as const;

function QuestionCard({ category, question, color }: { category: string; question: string; color: keyof typeof colorStyles }) {
  const styles = colorStyles[color];

  return (
    <div className={`border-l-4 ${styles.border} pl-4`}>
      <div className={`text-sm font-medium ${styles.text} mb-1`}>{category}</div>
      <div className="text-deep-indigo-400">&ldquo;{question}&rdquo;</div>
    </div>
  );
}

export function SampleQuestions() {
  return (
    <div className="mt-16 bg-white rounded-2xl p-8 shadow-sm">
      <h3 className="text-feature-title text-deep-indigo-500 mb-6 text-center">
        Sample Interview Questions
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <QuestionCard {...questionCategories[0]} />
          <QuestionCard {...questionCategories[1]} />
        </div>
        <div className="space-y-4">
          <QuestionCard {...questionCategories[2]} />
          <QuestionCard {...questionCategories[3]} />
        </div>
      </div>
    </div>
  );
}