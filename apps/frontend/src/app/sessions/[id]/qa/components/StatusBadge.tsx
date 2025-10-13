type BadgeVariant = 'complete' | 'partial' | 'notStarted';

interface StatusBadgeProps {
  variant: BadgeVariant;
}

interface BadgeConfig {
  dotColor: string;
  textColor: string;
  label: string;
}

const BADGE_CONFIGS: Record<BadgeVariant, BadgeConfig> = {
  complete: {
    dotColor: 'bg-benzol-green-500',
    textColor: 'text-benzol-green-700',
    label: 'Complete',
  },
  partial: {
    dotColor: 'bg-amber-500',
    textColor: 'text-amber-700',
    label: 'Partial',
  },
  notStarted: {
    dotColor: 'bg-jasper-red-500',
    textColor: 'text-jasper-red-700',
    label: 'Not Started',
  },
};

function getBadgeConfig(variant: BadgeVariant): BadgeConfig {
  return BADGE_CONFIGS[variant];
}

export function StatusBadge({ variant }: StatusBadgeProps) {
  const config = getBadgeConfig(variant);

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`inline-flex h-2.5 w-2.5 rounded-full ${config.dotColor}`} aria-hidden="true" />
      <span className={`text-xs font-medium ${config.textColor}`}>{config.label}</span>
    </span>
  );
}
