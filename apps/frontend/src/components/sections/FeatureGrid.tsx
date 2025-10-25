import { FeatureCard } from '../ui';
import { ChatIcon, GridIcon, DocumentIcon } from '../icons';

const features = [
  {
    icon: <ChatIcon />,
    title: 'Structured BA Methodology',
    description: 'Like a seasoned business analyst, SpecScribe guides you through 8 comprehensive question categories, asking adaptive follow-up questions to uncover requirements you might have missed.',
    iconColor: 'green' as const
  },
  {
    icon: <GridIcon />,
    title: 'Multi-Provider Support',
    description: 'Your choice, your workflow. SpecScribe adapts to work with Claude, GPT, or Gemini. Switch providers anytime without changing your process.',
    iconColor: 'indigo' as const
  },
  {
    icon: <DocumentIcon />,
    title: 'Professional Documentation',
    description: 'Every interview produces a structured Markdown document with prioritized requirements (MUST/SHOULD/COULD), ready for developers to build from immediately.',
    iconColor: 'red' as const
  }
];

export function FeatureGrid() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
      {features.map((feature, index) => (
        <FeatureCard
          key={index}
          icon={feature.icon}
          title={feature.title}
          description={feature.description}
          iconColor={feature.iconColor}
        />
      ))}
    </div>
  );
}