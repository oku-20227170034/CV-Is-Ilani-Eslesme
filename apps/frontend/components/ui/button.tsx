import * as React from 'react';
import { cn } from '@/lib/utils';

/**
 * Swiss International Style Button Component
 *
 * Design Principles:
 * - Hard shadows (no blur) that create depth
 * - Square corners (rounded-none) - Brutalist aesthetic
 * - High contrast black borders
 * - Hover: translate + shadow removal creates "press" effect
 * - Clear semantic variants for different actions
 */

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /**
   * Visual variant determining color and purpose:
   * - `default`: Hyper Blue (#1D4ED8) - Primary actions (save, submit, create)
   * - `destructive`: Alert Red (#DC2626) - Destructive actions (delete, remove)
   * - `success`: Signal Green (#15803D) - Positive actions (download, confirm, complete)
   * - `warning`: Alert Orange (#F97316) - Caution actions (reset, clear, undo)
   * - `outline`: Transparent + black border - Secondary actions (cancel, back)
   * - `secondary`: Panel Grey (#E5E5E0) - Tertiary actions
   * - `ghost`: No background - Subtle actions (icon buttons, navigation)
   * - `link`: Text only with underline - Inline links
   */
  variant?:
    | 'default'
    | 'destructive'
    | 'success'
    | 'warning'
    | 'outline'
    | 'secondary'
    | 'ghost'
    | 'link';
  /**
   * Button size:
   * - `default`: Standard button (h-10)
   * - `sm`: Small button (h-8)
   * - `lg`: Large button (h-12)
   * - `icon`: Square icon button (h-9 w-9)
   */
  size?: 'default' | 'sm' | 'lg' | 'icon';
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => {
    // Base styles applied to ALL buttons
    // Swiss Design: clean, functional, high contrast
    const baseStyles = cn(
      'relative inline-flex items-center justify-center gap-2',
      'whitespace-nowrap text-sm font-semibold transition-all duration-300 active:scale-95',
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-300 focus-visible:ring-offset-2',
      'disabled:pointer-events-none disabled:opacity-50',
      "[&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 [&_svg]:shrink-0",
      'rounded-full'
    );

    const variants = {
      default: cn(
        'bg-primary text-white shadow-premium-md',
        'hover:bg-rose-400 hover:shadow-premium-lg'
      ),
      destructive: cn(
        'bg-rose-700 text-white shadow-premium-md',
        'hover:bg-rose-800'
      ),
      success: cn(
        'bg-emerald-500 text-white shadow-premium-md',
        'hover:bg-emerald-600'
      ),
      warning: cn(
        'bg-amber-500 text-white shadow-premium-md',
        'hover:bg-amber-600'
      ),
      outline: cn(
        'bg-transparent text-primary border border-primary',
        'hover:bg-rose-50'
      ),
      secondary: cn(
        'bg-secondary text-foreground shadow-premium-sm',
        'hover:bg-rose-100'
      ),
      ghost: cn(
        'bg-transparent text-foreground hover:bg-rose-50'
      ),
      link: cn(
        'bg-transparent text-primary underline-offset-4 hover:underline p-0 h-auto'
      ),
    };

    // Size styles. Icon variant is 44×44px to meet WCAG 2.2 AA target size
    // (success criterion 2.5.8). Call sites that override the visible size
    // with smaller h-X w-X classes get the touch-area expansion via the
    // iconHitArea overlay above.
    const iconHitArea = "before:absolute before:-inset-1.5 before:content-['']";

    const sizes = {
      default: 'h-10 px-6 py-2',
      sm: 'h-8 px-4 py-1 text-xs',
      lg: 'h-12 px-8 py-3 text-base',
      icon: cn('h-11 w-11 p-0', iconHitArea),
    };

    const variantClass = variants[variant];
    const sizeClass = sizes[size];

    return (
      <button ref={ref} className={cn(baseStyles, variantClass, sizeClass, className)} {...props} />
    );
  }
);
Button.displayName = 'Button';

export { Button };
