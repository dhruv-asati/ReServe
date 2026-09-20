import { BarChart3 } from 'lucide-react';
import { ResponsiveContainer } from 'recharts';

import { Card, LoadingState, Badge } from '@/components/ui';

/**
 * ChartCard — the standard shell for every chart on the Analytics page.
 *
 * Wraps the shared Card primitive so charts inherit the app's panel styling
 * and renders a Recharts ResponsiveContainer so charts resize cleanly
 * between mobile and desktop.
 *
 * A chart is only ever drawn from real data. While loading it shows a
 * spinner; when the data source has nothing to plot (`empty`) it shows
 * `emptyLabel` instead of an empty or placeholder chart. The "Live data"
 * badge appears when the chart is backed by the API (`live`).
 */
export default function ChartCard({
  title,
  subtitle,
  height = 280,
  loading = false,
  loadingLabel = 'Loading chart…',
  live = false,
  empty = false,
  emptyLabel = 'No data yet.',
  children,
}) {
  return (
    <Card>
      <Card.Header
        title={title}
        subtitle={subtitle}
        action={
          live ? (
            <Badge tone="success" size="sm">
              Live data
            </Badge>
          ) : null
        }
      />
      <Card.Body>
        {loading ? (
          <LoadingState label={loadingLabel} />
        ) : empty ? (
          <div
            className="flex flex-col items-center justify-center gap-3 px-6 text-center"
            style={{ width: '100%', height }}
          >
            <span className="rounded-full border border-line bg-surface-2 p-3 text-faint">
              <BarChart3 size={20} strokeWidth={1.5} />
            </span>
            <p className="max-w-xs text-xs text-muted">{emptyLabel}</p>
          </div>
        ) : (
          <div style={{ width: '100%', height }}>
            <ResponsiveContainer width="100%" height="100%">
              {children}
            </ResponsiveContainer>
          </div>
        )}
      </Card.Body>
    </Card>
  );
}
