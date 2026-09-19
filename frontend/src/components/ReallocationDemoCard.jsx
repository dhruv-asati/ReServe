import { useEffect, useMemo, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  Circle,
  FlaskConical,
  Loader2,
  RotateCw,
  Users,
} from 'lucide-react';

import { Badge, Button, Card } from '@/components/ui';
import ReallocationWarning from '@/components/ReallocationWarning';
import useReallocationDemo from '@/hooks/useReallocationDemo';
import {
  getReallocationView,
  resetReallocationDemo,
  simulateRecipientUnavailable,
} from '@/services/reallocationDemoService';
import { PATHS } from '@/routes/paths';
import { cn } from '@/utils/cn';

/**
 * ReallocationDemoCard — the RS-1024 "recipient becomes unavailable" demo,
 * shown in the Operations details view while RS-1024 is selected.
 *
 * Top to bottom:
 *   1. The warning (only once triggered): the original allocation is no
 *      longer feasible.
 *   2. The allocation — NGO A 50, Shelter B 20, Night Rescue Hub 10 — with
 *      each recipient's state, and totals for what has a recipient and what
 *      does not.
 *   3. The mock reallocation progress (only once triggered): a short,
 *      timed step list. The steps are cosmetic; nothing is searched.
 *   4. Actions: "Simulate Recipient Unavailable", then Reset Demo and a link
 *      to Smart Matching.
 *
 * All state comes from services/reallocationDemoService.js, which is what
 * keeps the Operations list, the summary above, the tracker, the map, Smart
 * Matching and the Dashboard in step with this card. Frontend only: no
 * organization is contacted and no notification is sent.
 */
export default function ReallocationDemoCard() {
  const demo = useReallocationDemo();
  const view = useMemo(() => getReallocationView(demo), [demo]);
  const { unavailable, phase } = view;
  const running = phase === 'running';
  const settled = phase === 'settled';

  const warningRef = useRef(null);
  const simulateRef = useRef(null);
  const wasUnavailable = useRef(unavailable);

  // The button that was just pressed becomes disabled (and Reset removes
  // itself), so move focus to where the user's attention should go instead of
  // letting it fall back to <body>. Skipped on mount, so revisiting the page
  // with the scenario already active does not steal focus.
  useEffect(() => {
    if (unavailable && !wasUnavailable.current) warningRef.current?.focus();
    if (!unavailable && wasUnavailable.current) simulateRef.current?.focus();
    wasUnavailable.current = unavailable;
  }, [unavailable]);

  const progress = (view.completedSteps / view.steps.length) * 100;

  const hint = running
    ? 'Mock reallocation in progress — simulated locally.'
    : settled
      ? `Demo state only — nothing was sent to ${view.recipientName} or any other organization. Reset to restore the original allocation.`
      : `Demo only: marks ${view.recipientName} unavailable and plays a mock reallocation. No organization is contacted and no notification is sent.`;

  return (
    <Card className={cn('transition-colors duration-300', unavailable && 'border-l-2 border-l-urgent')}>
      <Card.Header
        icon={Users}
        title="Recipient Allocation"
        subtitle={`${view.operationId} · ${view.total} ${view.unit} across ${view.rows.length} recipients`}
        action={
          <Badge tone="predicted" icon={FlaskConical} size="sm">
            DEMO SCENARIO
          </Badge>
        }
      />

      <Card.Body className="space-y-5">
        {unavailable && <ReallocationWarning ref={warningRef} role="alert" warning={view.warning} />}

        <ul
          aria-label={`Allocation of ${view.operationId} by recipient`}
          className="divide-y divide-line overflow-hidden rounded-control border border-line"
        >
          {view.rows.map((row) => {
            const down = row.state === 'unavailable';
            return (
              <li
                key={row.id}
                className={cn(
                  'flex items-center justify-between gap-3 px-3.5 py-3 transition-colors duration-300',
                  down && 'bg-critical/5',
                )}
              >
                <div className="min-w-0">
                  <p className={cn('text-sm font-medium', down ? 'text-muted' : 'text-content')}>
                    {row.name}
                  </p>
                  {down && (
                    <p className="mt-0.5 text-[11px] text-critical">
                      Can no longer receive this allocation
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span
                    className={cn(
                      'tabular text-sm font-semibold',
                      down ? 'text-faint line-through' : 'text-content',
                    )}
                  >
                    {row.portions} {row.unit}
                  </span>
                  <Badge tone={down ? 'critical' : 'success'} size="sm">
                    {down ? 'Unavailable' : 'Allocated'}
                  </Badge>
                </div>
              </li>
            );
          })}
        </ul>

        <dl className="grid grid-cols-3 gap-3">
          <Metric label="Total" value={view.total} unit={view.unit} />
          <Metric label="With a recipient" value={view.placed} unit={view.unit} />
          <Metric
            label="No recipient"
            value={view.unplaced}
            unit={view.unit}
            tone={view.unplaced > 0 ? 'urgent' : 'default'}
          />
        </dl>

        {unavailable && (
          <div className="space-y-4 border-t border-line pt-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-semibold text-content">Mock reallocation</p>
              <Badge tone={settled ? 'urgent' : 'active'} size="sm">
                {settled ? 'Awaiting new recipient' : 'Reallocating…'}
              </Badge>
            </div>

            <ol className="space-y-3">
              {view.steps.map((step, index) => {
                const state =
                  index < view.completedSteps
                    ? 'complete'
                    : running && index === view.completedSteps
                      ? 'active'
                      : 'pending';
                return <StepRow key={step.key} label={step.label} state={state} />;
              })}
            </ol>

            <div
              className="h-1.5 w-full overflow-hidden rounded-full bg-surface-3"
              role="progressbar"
              aria-label="Mock reallocation progress"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(progress)}
            >
              <div
                className="h-full rounded-full bg-brand-500 transition-all duration-500 ease-soft"
                style={{ width: `${progress}%` }}
              />
            </div>

            {settled && (
              <p className="rounded-control border border-line bg-surface-2 px-3.5 py-3 text-xs leading-relaxed text-muted">
                {view.outcome}
              </p>
            )}
          </div>
        )}

        <div className="border-t border-line pt-4">
          <div className="flex flex-col gap-2.5 sm:flex-row sm:flex-wrap">
            <Button
              ref={simulateRef}
              variant="danger"
              icon={AlertTriangle}
              loading={running}
              disabled={unavailable}
              onClick={simulateRecipientUnavailable}
              className="w-full justify-center sm:w-auto"
            >
              Simulate Recipient Unavailable
            </Button>
            {unavailable && (
              <>
                <Button
                  variant="secondary"
                  icon={RotateCw}
                  onClick={resetReallocationDemo}
                  className="w-full justify-center sm:w-auto"
                >
                  Reset Demo
                </Button>
                <Button
                  as={Link}
                  to={PATHS.MATCHING}
                  variant="outline"
                  iconRight={ArrowUpRight}
                  className="w-full justify-center sm:w-auto"
                >
                  Review in Smart Matching
                </Button>
              </>
            )}
          </div>
          <p className="mt-3 flex items-start gap-1.5 text-[11px] text-faint">
            <FlaskConical size={12} strokeWidth={1.75} className="mt-0.5 shrink-0 text-predicted" />
            <span>{hint}</span>
          </p>
        </div>
      </Card.Body>

      {/* Announces the end of the mock progress to screen readers */}
      <p className="sr-only" aria-live="polite">
        {settled
          ? `Reallocation search finished. ${view.operationId} is Reallocating and ${view.unplaced} ${view.unit} still need a recipient.`
          : ''}
      </p>
    </Card>
  );
}

/** One line of the mock progress list — same look as the Matching page's step rows. */
function StepRow({ label, state }) {
  return (
    <li className="flex items-center gap-3">
      <span
        className={cn(
          'flex h-6 w-6 shrink-0 items-center justify-center rounded-full',
          state === 'complete' && 'bg-success/10 text-success',
          state === 'active' && 'bg-brand-500/10 text-brand-400',
          state === 'pending' && 'bg-surface-3 text-faint',
        )}
      >
        {state === 'complete' && <CheckCircle2 size={15} strokeWidth={2} />}
        {state === 'active' && <Loader2 size={13} strokeWidth={2.25} className="animate-spin" />}
        {state === 'pending' && <Circle size={9} strokeWidth={2} fill="currentColor" />}
      </span>
      <span className={state === 'pending' ? 'text-sm text-faint' : 'text-sm font-medium text-content'}>
        {label}
      </span>
    </li>
  );
}

function Metric({ label, value, unit, tone = 'default' }) {
  return (
    <div
      className={cn(
        'min-w-0 rounded-control border px-3 py-2.5 transition-colors duration-300',
        tone === 'urgent' ? 'border-urgent/30 bg-urgent/5' : 'border-line bg-surface-2',
      )}
    >
      <dt className="text-[10px] font-medium uppercase tracking-wide text-faint">{label}</dt>
      <dd className="mt-1">
        <span
          className={cn(
            'tabular text-lg font-semibold tracking-tight',
            tone === 'urgent' ? 'text-urgent' : 'text-content',
          )}
        >
          {value}
        </span>{' '}
        <span className="text-[11px] font-medium text-muted">{unit}</span>
      </dd>
    </div>
  );
}
