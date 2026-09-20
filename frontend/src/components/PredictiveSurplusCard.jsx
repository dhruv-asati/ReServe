import { useState } from 'react';
import { Sparkles, Bell, CheckCircle2, Info, AlertTriangle, BarChart3 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

import { Card, Button, Badge, LoadingState } from '@/components/ui';
import { CHART_AXIS, CHART_CURSOR } from '@/utils/theme';
import { ANALYTICS_LIVE, notifyNearbyRescuePartners } from '@/services/analyticsService';

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

/** 90 -> "90", 87.5 -> "87.5" */
const formatQuantity = (value) => Number(value).toLocaleString('en-US', { maximumFractionDigits: 1 });

const plural = (count, word) => `${count} ${word}${count === 1 ? '' : 's'}`;

/**
 * What the "Notify" action really did, in plain words. The counts come from
 * the backend — `partnersNotified` is how many real partner accounts just got
 * a notification, and 0 is reported as 0.
 */
function describeResult(result) {
  if (result.partnersNotified > 0) {
    const scope = result.scope === 'nearby' ? ' near you' : '';
    const skipped =
      result.alreadyNotified > 0 ? ` (${result.alreadyNotified} already alerted in the last hour)` : '';
    return {
      tone: 'success',
      text: `${plural(result.partnersNotified, 'rescue partner')}${scope} notified${skipped}`,
    };
  }
  if (result.alreadyNotified > 0) {
    return {
      tone: 'neutral',
      text: `Nobody new to notify — ${plural(result.alreadyNotified, 'partner')} already alerted in the last hour`,
    };
  }
  return {
    tone: 'neutral',
    text:
      result.scope === 'nearby'
        ? 'No available rescue partners near you to notify right now'
        : 'No available rescue partners to notify right now',
  };
}

/**
 * PredictiveSurplusCard — recent food surplus and, when the history supports
 * one, the hour it usually appears in.
 *
 * Everything shown is computed by the backend from recorded resources; there
 * is no sample data. With no surplus recorded there is no chart, and with too
 * little history there is no prediction (and the notify button is disabled).
 * The notify button sends real notifications to real rescue-partner accounts
 * and reports the true number it reached.
 */
export default function PredictiveSurplusCard({ forecast, loading = false }) {
  const [notifyState, setNotifyState] = useState('idle'); // 'idle' | 'sending' | 'done' | 'error'
  const [result, setResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  const history = forecast?.history ?? [];
  const prediction = forecast?.prediction ?? null;
  const hasHistory = history.some((day) => day.quantity > 0);
  const unit = forecast?.unit ?? 'units';

  async function handleNotify() {
    setNotifyState('sending');
    setErrorMessage('');
    try {
      const data = await notifyNearbyRescuePartners();
      setResult(data);
      setNotifyState('done');
    } catch (failure) {
      setErrorMessage(failure?.message || 'Could not send the notification. Try again in a moment.');
      setNotifyState('error');
    }
  }

  const outcome = notifyState === 'done' && result ? describeResult(result) : null;

  return (
    <Card>
      <Card.Header
        icon={Sparkles}
        title="Predictive Surplus"
        subtitle="Recent food surplus, and the hour it usually shows up in."
        action={
          ANALYTICS_LIVE ? (
            <Badge tone="success" size="sm">
              Live data
            </Badge>
          ) : null
        }
      />
      <Card.Body className="space-y-5">
        <div className="flex items-start gap-2.5 rounded-control border border-line bg-surface-2/60 px-3.5 py-3">
          <Info size={16} strokeWidth={1.75} className="mt-0.5 shrink-0 text-muted" />
          <p className="text-xs leading-relaxed text-muted">
            Built from the food surplus recorded on the platform. A window is only predicted once
            surplus has appeared in the same hour on at least {forecast?.minDaysRequired ?? 3}{' '}
            different days of the last {forecast?.windowDays ?? 28}. It is an estimate from past
            activity, not a guarantee.
          </p>
        </div>

        {loading ? (
          <LoadingState label="Loading surplus history…" />
        ) : (
          <>
            <div>
              <p className="mb-2 text-xs font-medium tracking-wide text-muted">
                Surplus food, last 7 days ({unit})
              </p>
              {hasHistory ? (
                <div style={{ width: '100%', height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={history} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
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
                      <Tooltip
                        {...tooltipStyle}
                        formatter={(value) => [`${formatQuantity(value)} ${unit}`, 'Surplus']}
                      />
                      <Bar dataKey="quantity" name="Surplus" fill={BRAND_COLOR} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center gap-3 px-6 py-10 text-center">
                  <span className="rounded-full border border-line bg-surface-2 p-3 text-faint">
                    <BarChart3 size={20} strokeWidth={1.5} />
                  </span>
                  <p className="max-w-xs text-xs text-muted">
                    No surplus food has been recorded in the last 7 days. It shows up here once
                    providers post food resources.
                  </p>
                </div>
              )}
            </div>

            {prediction ? (
              <div className="rounded-control border border-predicted/25 bg-predicted/10 px-4 py-3.5">
                <div className="flex items-start gap-2.5">
                  <Sparkles size={18} strokeWidth={2} className="mt-0.5 shrink-0 text-predicted" />
                  <div className="min-w-0 flex-1 space-y-1">
                    <p className="text-sm font-semibold text-predicted">
                      Predicted surplus:{' '}
                      {prediction.low === prediction.high
                        ? `about ${formatQuantity(prediction.high)}`
                        : `${formatQuantity(prediction.low)}–${formatQuantity(prediction.high)}`}{' '}
                      {prediction.unit} expected around {prediction.windowLabel}
                    </p>
                    <p className="text-xs leading-relaxed text-muted">
                      Surplus appeared in this hour on {prediction.daysWithSurplus} of the last{' '}
                      {prediction.windowDays} days. The range is the smallest and largest amount
                      seen on those days — an estimate, not a guaranteed forecast.
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-control border border-line bg-surface-2/60 px-4 py-3.5">
                <p className="text-sm font-semibold text-content">Not enough history to predict yet</p>
                <p className="mt-1 text-xs leading-relaxed text-muted">
                  A predicted window appears once surplus food has been recorded in the same hour
                  on at least {forecast?.minDaysRequired ?? 3} different days.
                </p>
              </div>
            )}

            <div className="flex flex-col gap-3 border-t border-line pt-4 sm:flex-row sm:items-start sm:justify-between">
              <p className="text-xs text-muted">
                Sends an in-app notification to the available rescue partners
                {ANALYTICS_LIVE ? '' : ' (needs the backend connected)'} so they can get ready ahead
                of the predicted window.
              </p>
              <div className="flex shrink-0 flex-col items-stretch gap-2 sm:items-end">
                <Button
                  icon={Bell}
                  variant="secondary"
                  loading={notifyState === 'sending'}
                  disabled={!prediction || !ANALYTICS_LIVE}
                  onClick={handleNotify}
                  className="w-full sm:w-auto"
                >
                  Notify Nearby Rescue Partners
                </Button>

                {outcome && (
                  <p
                    role="status"
                    className={
                      outcome.tone === 'success'
                        ? 'flex items-start gap-2 rounded-control border border-success/25 bg-success/10 px-3 py-2 text-xs font-medium text-success'
                        : 'flex items-start gap-2 rounded-control border border-line bg-surface-2/60 px-3 py-2 text-xs font-medium text-muted'
                    }
                  >
                    {outcome.tone === 'success' ? (
                      <CheckCircle2 size={14} strokeWidth={2} className="mt-0.5 shrink-0" />
                    ) : (
                      <Info size={14} strokeWidth={2} className="mt-0.5 shrink-0" />
                    )}
                    <span className="min-w-0 break-words">{outcome.text}</span>
                  </p>
                )}

                {notifyState === 'error' && (
                  <p
                    role="alert"
                    className="flex items-start gap-2 rounded-control border border-critical/25 bg-critical/10 px-3 py-2 text-xs font-medium text-critical"
                  >
                    <AlertTriangle size={14} strokeWidth={2} className="mt-0.5 shrink-0" />
                    <span className="min-w-0 break-words">{errorMessage}</span>
                  </p>
                )}
              </div>
            </div>
          </>
        )}
      </Card.Body>
    </Card>
  );
}
