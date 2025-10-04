import React from 'react';
import { useRouter } from 'next/navigation';
import { Requirement } from '@/lib/api/types';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { CheckCircleIcon } from '@/components/icons/CheckCircleIcon';
import { useInterview } from '@/hooks/useInterview';

interface RequirementsViewProps {
  requirements: Requirement[];
  projectName: string;
}

const priorityColors: Record<string, string> = {
  MUST: 'bg-jasper-red-100 text-jasper-red-600 border-jasper-red-200',
  SHOULD: 'bg-benzol-green-100 text-benzol-green-600 border-benzol-green-200',
  COULD: 'bg-deep-indigo-100 text-deep-indigo-600 border-deep-indigo-200',
};

function generateMarkdown(requirements: Requirement[], projectName: string): string {
  const grouped = requirements.reduce((acc, req) => {
    const priority = req.priority || 'COULD';
    if (!acc[priority]) acc[priority] = [];
    acc[priority].push(req);
    return acc;
  }, {} as Record<string, Requirement[]>);

  let markdown = `# ${projectName} - Requirements\n\n`;
  markdown += `Generated on ${new Date().toLocaleDateString()}\n\n`;

  ['MUST', 'SHOULD', 'COULD'].forEach(priority => {
    const reqs = grouped[priority];
    if (reqs && reqs.length > 0) {
      markdown += `## ${priority} Have\n\n`;
      reqs.forEach((req, index) => {
        markdown += `### ${index + 1}. ${req.title}\n\n`;
        if (req.rationale) {
          markdown += `${req.rationale}\n\n`;
        }
      });
    }
  });

  return markdown;
}

export function RequirementsView({ requirements, projectName }: RequirementsViewProps) {
  const router = useRouter();
  const { reset } = useInterview();

  const groupedRequirements = requirements.reduce((acc, req) => {
    const priority = req.priority || 'COULD';
    if (!acc[priority]) {
      acc[priority] = [];
    }
    acc[priority].push(req);
    return acc;
  }, {} as Record<string, Requirement[]>);

  const priorities = ['MUST', 'SHOULD', 'COULD'];

  const handleExport = () => {
    const content = generateMarkdown(requirements, projectName);
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${projectName.replace(/\s+/g, '-').toLowerCase()}-requirements.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handlePrint = () => {
    window.print();
  };

  const handleStartNew = () => {
    reset();
    router.push('/interview/new');
  };

  return (
    <div className="space-y-6">
      <div className="text-center space-y-4">
        <div className="flex justify-center">
          <CheckCircleIcon className="w-16 h-16 text-benzol-green-500" />
        </div>
        <h2 className="text-3xl font-bold text-deep-indigo-500">
          Interview Complete!
        </h2>
        <p className="text-deep-indigo-400">
          We&apos;ve generated {requirements.length} requirements for <strong>{projectName}</strong>
        </p>
      </div>

      {/* Action buttons */}
      <Card padding="md">
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button onClick={handleExport} variant="primary">
            Download Requirements
          </Button>
          <Button onClick={handlePrint} variant="secondary">
            Print
          </Button>
          <Button onClick={handleStartNew} variant="outline">
            Start New Interview
          </Button>
        </div>
      </Card>

      <div className="space-y-6">
        {priorities.map((priority) => {
          const reqs = groupedRequirements[priority];
          if (!reqs || reqs.length === 0) return null;

          return (
            <div key={priority} className="space-y-3">
              <h3 className="text-lg font-semibold text-deep-indigo-500">
                {priority} Have ({reqs.length})
              </h3>
              <div className="space-y-3">
                {reqs.map((req) => (
                  <Card key={req.id} padding="md" hover>
                    <div className="space-y-2">
                      <div className="flex items-start justify-between gap-4">
                        <h4 className="font-medium text-deep-indigo-500 flex-1">
                          {req.title}
                        </h4>
                        <span
                          className={`
                            px-2 py-1 rounded text-xs font-medium border
                            ${priorityColors[priority]}
                          `}
                        >
                          {priority}
                        </span>
                      </div>
                      {req.rationale && (
                        <p className="text-sm text-deep-indigo-400">
                          {req.rationale}
                        </p>
                      )}
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
