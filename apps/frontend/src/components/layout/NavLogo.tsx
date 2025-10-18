import Link from 'next/link';
import Image from 'next/image';

export function NavLogo() {
  return (
    <Link href="/" className="flex items-center space-x-2">
      <Image
        src="/logos/logo-icon.svg"
        alt="SpecScribe"
        width={32}
        height={32}
        className="w-8 h-8"
        priority
      />
      <span className="text-xl font-semibold text-deep-indigo-500">
        SpecScribe
      </span>
    </Link>
  );
}
