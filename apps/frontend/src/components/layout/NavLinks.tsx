import Link from 'next/link';

interface NavItem {
  href: string;
  label: string;
}

interface NavLinksProps {
  items: NavItem[];
  className?: string;
}

export function NavLinks({ items, className = '' }: NavLinksProps) {
  return (
    <>
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={className || "text-deep-indigo-400 hover:text-deep-indigo-500 transition-colors"}
        >
          {item.label}
        </Link>
      ))}
    </>
  );
}
