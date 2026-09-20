import { useState } from 'react';
import { Sparkles, Bell, CheckCircle2, Info } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

import { Card, Button, Badge, LoadingState } from '@/components/ui';
import { CHART_AXIS, CHART_CURSOR } from '@/utils/theme';
import { notifyNearbyRescuePartners } from '@/services/analyticsService';

const BRAND_COLOR = '#14b98f';

const tooltipStyle = {
  contentStyle: {
    backgroundColor: '#161d27',
    border: '1px solid #232d3b',
    borderRadius: 8,
    fontSize: 12,
  },
  labelStyle: { color: '#e6edf5' },
  itemStyle: { color: '#94a3b8' },
  cursor: CHART_CURSOR.bar,
};

/**
 * PredictiveSurplusCard — worked demo of a short-term surplus forecast.
 *
 * Everything here — the daily history, the predicted range and window, and
 * the "notify partners" action — is a fixed, illustrative demonstration of
 * how historical patterns *could* support preparation for future rescues.
 * None of it is real model output, a guaranteed forecast, or a real
 * notification: the notify button only calls the mock
 * `notifyNearbyRescuePartners` service and shows a simulated confirmation.
 */
export default function PredictiveSurplusCard({ history, prediction, loading = false }) {
  const [notifyState, setNotifyState] = useState('idle'); // 'idle' | 'sending' | 'sent'
  const [result, setResult] = useState(null);

  async function handleNotify() {
    setNotifyState('sending');
    try {
      const data = await notifyNearbyRescuePartners();
      setResult(data);
      setNotifyState('sent');
    } catch {
      setNotifyState('idle');
    }
  }

  return (
    <Card>
      <Card.Header
        icon={Sparkles}
        title="Predictive Surplus Demo"
        subtitle="A worked example of forecasting surplus from historical patterns."
        action={
          <Badge tone="neutral" size="sm">
            Illustrative demo
          </Badge>
        }
      />
      <Card.Body className="space-y-5">
        <div className="flex items-start gap-2.5 rounded-control border border-line bg-surface-2/60 px-3.5 py-3">
          <Info size={16} strokeWidth={1.75} className="mt-0.5 shrink-0 text-muted" />
          <p className="text-xs leading-relaxed text-muted">
            This section demonstrates how a week of historical surplus counts could support
            preparing for future rescues — it is not connected to a real forecasting model and
            does not guarantee any outcome. The history, predicted range, and notification below
            are all fixed, illustrative demo values.
          </p>
        </div>

        {loading ? (
          <LoadingState label="Loading surplus history…" />
        ) : (
          <>
            <div>
              <p className="mb-2 text-xs font-medium tracking-wide text-muted">
                Illustrative Historical Surplus (Meals)
              </p>
              <div style={{ width: '100%', height: 220 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={history ?? []}
                    margin={{ top: 8, right: 12, left: -12, bottom: 0 }}
                  >
                    <CartesianGrid stroke={CHART_AXIS.grid} vertical={false} />
                    <XAxis
                      dataKey="label"
                      stroke={CHART_AXIS.stroke}
                      fontSize={CHART_AXIS.fontSize}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      stroke={CHART_AXIS.stroke}
                      fontSize={CHART_AXIS.fontSize}
                      tickLine={false}
                      axisLine={false}
                      width={36}
                      allowDecimals={false}
                    />
                    <Tooltip {...tooltipStyle} formatter={(value) => [`${value} meals`, 'Surplus']} />
                    <Bar dataKey="meals" name="Surplus" fill={BRAND_COLOR} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="rounded-control border border-predicted/25 bg-predicted/10 px-4 py-3.5">
              <div className="flex items-start gap-2.5">
                <Sparkles size={18} strokeWidth={2} className="mt-0.5 shrink-0 text-predicted" />
                <div className="min-w-0 flex-1 space-y-1">
                  <p className="text-sm font-semibold text-predicted">
                    Predicted surplus: {prediction?.low}–{prediction?.high} {prediction?.unit}{' '}
                    expected {prediction?.windowLabel}
                  </p>
                  <p className="text-xs leading-relaxed text-muted">
                    Illustrative projection based on the pattern above — not an actual model
                    output or a guaranteed forecast.
                  </p>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-3 border-t border-line pt-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs text-muted">
                In a real deployment, a forecast like this could prompt reaching out to partners
                ahead of the predicted window.
              </p>
              <div className="shrink-0">
                {notifyState === 'sent' ? (
                  <p
                    role="status"
                    className="flex w-full items-start gap-2 rounded-control border border-success/25 bg-success/10 px-3 py-2 text-xs font-medium text-success sm:w-auto"
                  >
                    <CheckCircle2 size={14} strokeWidth={2} className="mt-0.5 shrink-0" />
                    <span className="min-w-0 break-words">
                      Demo notification sent
                      {result?.partnersNotified ? ` · ${result.partnersNotified} partners (simulated)` : ''}
                    </span>
                  </p>
                ) : (
                  <Button
                    icon={Bell}
                    variant="secondary"
                    loading={notifyState === 'sending'}
                    onClick={handleNotify}
                    className="w-full sm:w-auto"
                  >
                    Notify Nearby Rescue Partners
                  </Button>
                )}
              </div>
            </div>
          </>
        )}
      </Card.Body>
    </Card>
  );
}
