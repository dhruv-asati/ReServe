import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, CheckCircle2, Handshake, Info, Radio, RotateCw, Truck } from 'lucide-react';

import { LoadingState } from '@/components/ui';
import { PATHS } from '@/routes/paths';
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '@/services/notificationsService';
import { cn } from '@/utils/cn';

/** How many notifications the panel loads. Older ones are not paged in. */
const PANEL_LIMIT = 20;

/** Backend NotificationType -> icon + tint (matches the app's semantic tones). */
const TYPE_META = {
  MATCH_FOUND: { icon: Handshake, tone: 'bg-brand-500/10 text-brand-400' },
  PARTNER_ASSIGNED: { icon: Truck, tone: 'bg-active/10 text-active' },
  OPERATION_UPDATE: { icon: Radio, tone: 'bg-active/10 text-active' },
  REALLOCATION: { icon: RotateCw, tone: 'bg-urgent/10 text-urgent' },
  DELIVERY_CONFIRMED: { icon: CheckCircle2, tone: 'bg-success/10 text-success' },
  SYSTEM: { icon: Info, tone: 'bg-surface-3 text-muted' },
};

/** "5 min ago" style label. The API sends timezone-aware ISO strings; a bare one is treated as UTC. */
function timeAgo(iso) {
  if (!iso) return '';
  const hasZone = /(?:[zZ]|[+-]\d{2}:?\d{2})$/.test(iso);
  const then = new Date(hasZone ? iso : `${iso}Z`);
  const minutes = Math.floor((Date.now() - then.getTime()) / 60000);
  if (!Number.isFinite(minutes)) return '';
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} d ago`;
  return then.toLocaleDateString([], { day: 'numeric', month: 'short' });
}

/**
 * NotificationsMenu — the topbar bell.
 *
 * Shows the unread count on the bell; opening it loads the newest
 * notifications (GET /notifications). Choosing one marks it read
 * (PATCH /notifications/{id}/read) and, when it refers to a rescue operation,
 * opens that operation in Live Operations. "Mark all read" clears the rest in
 * one request. The unread count lives in AppLayout (it also refreshes on every
 * navigation), so this component reports every change through
 * `onUnreadCountChange` and never keeps its own copy of the number.
 */
export default function NotificationsMenu({ unreadCount = 0, onUnreadCountChange }) {
  const navigate = useNavigate();
  const wrapperRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await listNotifications({ limit: PANEL_LIMIT });
      setItems(data.items ?? []);
      onUnreadCountChange?.(data.unread_count ?? 0);
    } catch (failure) {
      setError(failure);
    }
  }, [onUnreadCountChange]);

  // Fetch fresh data every time the panel opens.
  useEffect(() => {
    if (open) load();
  }, [open, load]);

  useEffect(() => {
    if (!open) return undefined;
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) setOpen(false);
    }
    function handleEscape(event) {
      if (event.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open]);

  async function handleSelect(item) {
    setOpen(false);

    if (!item.is_read) {
      // Optimistic: flip it now, restore from the server if the request fails.
      setItems((current) =>
        current?.map((entry) => (entry.id === item.id ? { ...entry, is_read: true } : entry)),
      );
      onUnreadCountChange?.((count) => Math.max(0, count - 1));
      markNotificationRead(item.id).catch(() => load());
    }

    if (item.related_operation_id) {
      navigate(`${PATHS.LIVE_OPERATIONS}?${new URLSearchParams({ operation: item.related_operation_id })}`);
    }
  }

  async function handleMarkAll() {
    setBusy(true);
    setError(null);
    try {
      await markAllNotificationsRead();
      setItems((current) => current?.map((entry) => ({ ...entry, is_read: true })));
      onUnreadCountChange?.(0);
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div ref={wrapperRef} className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label={unreadCount > 0 ? `Notifications, ${unreadCount} unread` : 'Notifications'}
        aria-haspopup="dialog"
        aria-expanded={open}
        className={cn(
          'relative rounded-control p-2 text-muted transition-colors hover:bg-surface-2 hover:text-content',
          open && 'bg-surface-2 text-content',
        )}
      >
        <Bell size={17} strokeWidth={1.75} />
        {unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-brand-500 px-1 text-[10px] font-semibold leading-none text-white ring-2 ring-surface-1">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Notifications"
          className={cn(
            'animate-fade-up z-40 overflow-hidden rounded-control border border-line bg-surface-1 shadow-lg',
            // Phones: span the screen under the bar. Larger screens: a panel under the bell.
            'max-sm:fixed max-sm:inset-x-4 max-sm:top-[4.25rem]',
            'sm:absolute sm:right-0 sm:top-[calc(100%+0.5rem)] sm:w-96',
          )}
        >
          <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-2.5">
            <h2 className="text-sm font-semibold tracking-tight text-content">Notifications</h2>
            <button
              type="button"
              onClick={handleMarkAll}
              disabled={busy || unreadCount === 0}
              className="text-xs font-medium text-brand-400 transition-colors hover:text-brand-300 disabled:cursor-not-allowed disabled:text-faint"
            >
              Mark all read
            </button>
          </div>

          <div className="max-h-[min(24rem,60vh)] overflow-y-auto">
            {error ? (
              <div role="alert" className="px-4 py-8 text-center">
                <p className="text-xs text-muted">{error.message || 'Could not load notifications.'}</p>
                <button
                  type="button"
                  onClick={load}
                  className="mt-2 text-xs font-medium text-brand-400 hover:text-brand-300"
                >
                  Try again
                </button>
              </div>
            ) : items === null ? (
              <LoadingState label="Loading notifications…" className="py-10" />
            ) : items.length === 0 ? (
              <p className="px-4 py-10 text-center text-xs text-muted">
                No notifications yet. You will see matches, partner assignments, reallocations and
                deliveries here.
              </p>
            ) : (
              <ul className="divide-y divide-line">
                {items.map((item) => (
                  <NotificationRow key={item.id} item={item} onSelect={handleSelect} />
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function NotificationRow({ item, onSelect }) {
  const meta = TYPE_META[item.notification_type] ?? TYPE_META.SYSTEM;
  const Icon = meta.icon;

  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(item)}
        className={cn(
          'flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-2',
          !item.is_read && 'bg-brand-500/5',
        )}
      >
        <span
          className={cn('mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-control', meta.tone)}
        >
          <Icon size={15} strokeWidth={1.75} aria-hidden="true" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-start justify-between gap-2">
            <span
              className={cn(
                'text-xs leading-snug text-content',
                item.is_read ? 'font-medium' : 'font-semibold',
              )}
            >
              {item.title}
            </span>
            {!item.is_read && (
              <span
                aria-label="Unread"
                className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-400"
              />
            )}
          </span>
          <span className="mt-0.5 block break-words text-[11px] leading-relaxed text-muted">
            {item.message}
          </span>
          <span className="mt-1 block text-[10px] text-faint">{timeAgo(item.created_at)}</span>
        </span>
      </button>
    </li>
  );
}
