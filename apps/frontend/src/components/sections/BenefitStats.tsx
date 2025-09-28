const stats = [
  { value: '8+', label: 'Question categories' },
  { value: '3', label: 'AI providers' },
  { value: 'OAuth', label: 'Secure authentication' }
];

export function BenefitStats() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
      {stats.map((stat, index) => (
        <div key={index}>
          <div className="text-2xl font-bold text-benzol-green-500 mb-1">{stat.value}</div>
          <div className="text-sm text-deep-indigo-300">{stat.label}</div>
        </div>
      ))}
    </div>
  );
}