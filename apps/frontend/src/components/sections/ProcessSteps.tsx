import { ProcessStep } from '../ui';
import { PlusIcon, ChatIcon, FileIcon } from '../icons';

const steps = [
  {
    icon: <PlusIcon />,
    title: 'Start Interview',
    description: 'Begin with your project name and initial description. Choose your preferred AI provider and interview style.'
  },
  {
    icon: <ChatIcon />,
    title: 'AI Asks Questions',
    description: 'Our AI conducts an intelligent interview, asking targeted questions across 8 key categories and following up based on your responses.'
  },
  {
    icon: <FileIcon />,
    title: 'Get Documentation',
    description: 'Receive a comprehensive, professionally formatted requirements document ready for your development team to use.'
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