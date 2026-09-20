import { ResponsiveContainer } from 'recharts';

import { Card, LoadingState, Badge } from '@/components/ui';

/**
 * ChartCard — the standard shell for every chart on the Analytics page.
 *
 * Wraps the shared Card primitive so charts inherit the app's panel styling,
 * always shows an "Illustrative data" badge (this page's numbers are mock
 * data, never a verified production metric), and renders a Recharts
 * ResponsiveContainer so charts resize cleanly between mobile and desktop.
 */
export default function ChartCard({
  title,
  subtitle,
  height = 280,
  loading = false,
  loadingLabel = 'Loading chart…',
  children,
}) {
  return (
    <Card>
      <Card.Header
        title={title}
        subtitle={subtitle}
        action={
          <Badge tone="neutral" size="sm">
            Illustrative data
          </Badge>
        }
      />
      <Card.Body>
        {loading ? (
          <LoadingState label={loadingLabel} />
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
