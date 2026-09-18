import { cn } from '@/utils/cn';

/**
 * Card — the standard panel used for every grouped block in the app.
 *
 *   <Card>
 *     <Card.Header title="Active rescues" action={<Button …/>} />
 *     <Card.Body>…</Card.Body>
 *     <Card.Footer>…</Card.Footer>
 *   </Card>
 *
 * `interactive` adds hover affordance for cards that are themselves links.
 */
export default function Card({ interactive = false, className, children, ...props }) {
  return (
    <div
      className={cn(
        'panel overflow-hidden',
        interactive &&
          'cursor-pointer transition-colors duration-150 hover:border-line-strong hover:bg-surface-2',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

function Header({ title, subtitle, action, icon: Icon, className, children }) {
  return (
    <div
      className={cn(
        'flex items-start justify-between gap-3 border-b border-line px-4 py-3 sm:px-5',
        className,
      )}
    >
      {children ?? (
        <div className="flex min-w-0 items-start gap-2.5">
          {Icon && (
            <span className="mt-0.5 text-brand-400">
              <Icon size={16} strokeWidth={1.75} />
            </span>
          )}
          <div className="min-w-0">
            <h3 className="truncate text-sm font-semibold tracking-tight text-content">{title}</h3>
            {subtitle && <p className="mt-0.5 truncate text-xs text-muted">{subtitle}</p>}
          </div>
        </div>
      )}
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

function Body({ className, children, ...props }) {
  return (
    <div className={cn('p-4 sm:p-5', className)} {...props}>
      {children}
    </div>
  );
}

function Footer({ className, children, ...props }) {
  return (
    <div
      className={cn(
        'flex items-center justify-end gap-2 border-t border-line bg-surface-2/40 px-4 py-3 sm:px-5',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

Card.Header = Header;
Card.Body = Body;
Card.Footer = Footer;
