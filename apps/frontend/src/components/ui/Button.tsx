import { forwardRef } from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'success' | 'outline' | 'danger' | 'danger-text';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
  asChild?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = '', variant = 'primary', size = 'md', children, asChild = false, disabled = false, ...props }, ref) => {
    const baseClasses = 'btn-base';
    const variantClasses = {
      primary: 'btn-primary',
      secondary: 'btn-secondary',
      success: 'btn-success',
      outline: 'btn-outline',
      danger: 'btn-danger',
      'danger-text': 'btn-danger-text'
    };
    const sizeClasses = {
      sm: 'btn-md px-4 py-2 text-sm',
      md: 'btn-md',
      lg: 'btn-lg'
    };

    const classes = `${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`.trim();

    if (asChild) {
      return (
        <span className={classes}>
          {children}
        </span>
      );
    }

    return (
      <button
        className={classes}
        ref={ref}
        disabled={disabled}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

export { Button };