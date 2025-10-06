import { Container } from '@/components/ui/Container';

export default function SessionsLoading() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-deep-indigo-50 to-white">
      <div className="h-16 bg-white border-b" />
      <main className="py-12">
        <Container size="lg">
          <div className="space-y-6" role="status" aria-live="polite" aria-busy="true">
            <span className="sr-only">Loading sessions...</span>
            <div className="flex justify-between items-center mb-8">
              <div className="space-y-2">
                <div className="h-8 bg-deep-indigo-100 rounded w-48 animate-pulse" />
                <div className="h-4 bg-deep-indigo-100 rounded w-64 animate-pulse" />
              </div>
              <div className="h-12 bg-deep-indigo-100 rounded w-32 animate-pulse" />
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[...Array(6)].map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          </div>
        </Container>
      </main>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-white p-6 rounded-lg shadow border border-deep-indigo-100 animate-pulse">
      <div className="space-y-3">
        <div className="flex justify-between items-start gap-2">
          <div className="h-6 bg-deep-indigo-100 rounded w-3/4" />
          <div className="h-6 bg-deep-indigo-100 rounded w-20" />
        </div>
        <div className="space-y-2">
          <div className="h-4 bg-deep-indigo-100 rounded w-1/2" />
          <div className="h-4 bg-deep-indigo-100 rounded w-2/3" />
        </div>
        <div className="h-2 bg-deep-indigo-100 rounded w-full" />
        <div className="h-4 bg-deep-indigo-100 rounded w-1/3" />
        <div className="flex gap-2 pt-2">
          <div className="h-10 bg-deep-indigo-100 rounded flex-1" />
          <div className="h-10 bg-deep-indigo-100 rounded w-20" />
        </div>
      </div>
    </div>
  );
}
