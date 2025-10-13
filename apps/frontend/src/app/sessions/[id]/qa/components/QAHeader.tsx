import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';

interface QAHeaderProps {
  projectName: string;
  answeredCount: number;
  totalCount: number;
  onExport: () => void;
  isExporting: boolean;
  exportError: string | null;
}

export function QAHeader({
  projectName,
  answeredCount,
  totalCount,
  onExport,
  isExporting,
  exportError,
}: QAHeaderProps) {
  const router = useRouter();

  return (
    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
      <div className="flex-1">
        <Breadcrumb projectName={projectName} onNavigate={() => router.push('/sessions')} />
        <h1 className="text-3xl font-bold text-deep-indigo-500">{projectName}</h1>
        <ProgressText answeredCount={answeredCount} totalCount={totalCount} />
      </div>
      <ActionButtons
        onBack={() => router.push('/sessions')}
        onExport={onExport}
        isExporting={isExporting}
      />
      {exportError && <ExportError message={exportError} />}
    </div>
  );
}

function Breadcrumb({ projectName, onNavigate }: { projectName: string; onNavigate: () => void }) {
  return (
    <nav className="text-sm text-deep-indigo-400 mb-2" aria-label="Breadcrumb">
      <ol className="flex items-center space-x-2">
        <li>
          <button
            onClick={onNavigate}
            className="hover:text-deep-indigo-500 focus:ring-2 focus:ring-benzol-green-500 focus:ring-offset-2 rounded px-1"
          >
            Sessions
          </button>
        </li>
        <li aria-hidden="true">/</li>
        <li>
          <span className="text-deep-indigo-500 font-medium">{projectName}</span>
        </li>
        <li aria-hidden="true">/</li>
        <li>
          <span className="text-deep-indigo-500 font-medium">Q&A</span>
        </li>
      </ol>
    </nav>
  );
}

function ProgressText({ answeredCount, totalCount }: { answeredCount: number; totalCount: number }) {
  return (
    <p className="text-base text-deep-indigo-400 mt-1">
      {answeredCount} of {totalCount} questions answered
    </p>
  );
}

function ActionButtons({
  onBack,
  onExport,
  isExporting,
}: {
  onBack: () => void;
  onExport: () => void;
  isExporting: boolean;
}) {
  return (
    <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
      <Button onClick={onBack} variant="secondary" size="md" className="w-full sm:w-auto">
        Back to Sessions
      </Button>
      <Button
        onClick={onExport}
        variant="primary"
        size="md"
        disabled={isExporting}
        className="w-full sm:w-auto"
        aria-label="Export Q&A as Markdown"
      >
        {isExporting ? 'Exporting...' : 'Export Markdown'}
      </Button>
    </div>
  );
}

function ExportError({ message }: { message: string }) {
  return (
    <p className="text-sm text-jasper-red-500 mt-2" role="alert">
      {message}
    </p>
  );
}
