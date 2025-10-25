import { ProcessStep } from '../ui';
import { PlusIcon, ChatIcon, FileIcon } from '../icons';

const steps = [
  {
    icon: <PlusIcon />,
    title: 'Start Interview',
    description: 'Describe your project idea in your own words. Choose your preferred AI provider (Claude, GPT, or Gemini) and interview depth.'
  },
  {
    icon: <ChatIcon />,
    title: 'SpecScribe Guides the Interview',
    description: 'Like a seasoned business analyst, SpecScribe guides you through 8 comprehensive question categories like SCOPE, USERS, CONSTRAINTS, SUCCESS, and more, with adaptive follow-up questions based on your answers.'
  },
  {
    icon: <FileIcon />,
    title: 'Receive Your Specification',
    description: 'Download a structured Markdown document with prioritized requirements (MUST/SHOULD/COULD), user stories, technical constraints, and success metrics. Ready for developers immediately.'
  }
];

export function ProcessSteps() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-12">
      {steps.map((step, index) => (
        <ProcessStep
          key={index}
          step={index + 1}
          title={step.title}
          description={step.description}
          icon={step.icon}
          isLast={index === steps.length - 1}
        />
      ))}
    </div>
  );
}