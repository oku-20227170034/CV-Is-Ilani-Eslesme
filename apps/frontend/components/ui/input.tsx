import * as React from 'react';
import { cn } from '@/lib/utils';

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

/**
 * Swiss International Style Input Component
 *
 * Design Principles:
 * - Square corners (rounded-none) - Brutalist aesthetic
 * - Black border for high contrast
 * - Focus ring in Hyper Blue
 */
const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-11 w-full border border-rose-100 bg-white px-4 py-2 text-sm shadow-premium-sm transition-all duration-300',
          'placeholder:text-rose-300',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-200 focus-visible:border-primary',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'rounded-xl',
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = 'Input';

export { Input };
