import Link from 'next/link';

export function NavLogo() {
  return (
    <Link href="/" className="flex items-center space-x-2">
      <div className="w-8 h-8 bg-jasper-red-500 rounded-lg flex items-center justify-center">
        <span className="text-white font-bold text-lg">R</span>
      </div>
      <span className="text-xl font-semibold text-deep-indigo-500">
        Requirements Bot
      </span>
    </Link>
  );
}
