import { FeatureCard } from '../ui';
import { ChatIcon, GridIcon, DocumentIcon } from '../icons';

const features = [
  {
    icon: <ChatIcon />,
    title: 'Intelligent Interviews',
    description: 'AI asks targeted follow-up questions based on your responses, ensuring comprehensive requirement coverage without missing critical details.',
    iconColor: 'green' as const
  },
  {
    icon: <GridIcon />,
    title: 'Multi-Provider Support',
    description: 'Works seamlessly with Anthropic Claude, OpenAI GPT, and Google Gemini. Choose your preferred AI provider or switch between them.',
    iconColor: 'indigo' as const
  },
  {
    icon: <DocumentIcon />,
    title: 'Professional Documentation',
    description: 'Automatically generates comprehensive, well-structured requirements documents in Markdown format, ready for your development team.',
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