import { ShieldIcon, CheckCircleIcon } from '../icons';

export function TrustIndicators() {
  return (
    <div className="flex flex-col sm:flex-row items-center justify-center gap-6 text-sm text-deep-indigo-300 mb-12">
      <div className="flex items-center">
        <ShieldIcon className="w-4 h-4 mr-2 text-benzol-green-500" />
        Secure OAuth authentication
      </div>
      <div className="flex items-center">
        <CheckCircleIcon className="w-4 h-4 mr-2 text-benzol-green-500" />
        Open source project
      </div>
    </div>
  );
}