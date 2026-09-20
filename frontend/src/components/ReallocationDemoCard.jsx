import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  ChevronDown,
  Circle,
  FlaskConical,
  ListChecks,
  Loader2,
  RotateCw,
  Users,
  XCircle,
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
 *   1. The notice (only once triggered). While the mock steps run it says the
 *      original allocation is no longer feasible; once they finish it says the
 *      allocation was updated, and why.
 *   2. The allocation. Before and while running: NGO A 50, Shelter B 20,
 *      Night Rescue Hub 10, with each recipient's state. Once the mock steps
 *      finish: the previous and the updated allocation side by side, with
 *      what changed for each recipient, and totals for what has a recipient
 *      and what does not (80 / 80 / 0).
 *   3. "Why the allocation changed" — the cause (NGO A became unavailable),
 *      the rule that was applied, and the constraint checks behind each
 *      recipient (a collapsible list, read from the demo candidate data).
 *   4. The mock reallocation progress (only once triggered): a short, timed
 *      step list. The steps are cosmetic; nothing is actually searched.
 *   5. Actions: "Simulate Recipient Unavailable", then Reset Demo and a link
 *      to Smart Matching.
 *
 * All state comes from services/reallocationDemoService.js, which is what
 * keeps the Operations list, the summary above, the tracker, the map, Smart
 * Matching and the Dashboard in step with this card. The updated allocation is
 * a demo calculation over hardcoded demo recipients — not a live allocation.
 * Frontend only: no organization is contacted and no notification is sent.
 */
export default function ReallocationDemoCard() {
  const demo = useReallocationDemo();
  const view = useMemo(() => getReallocationView(demo), [demo]);
  const { unavailable, phase, updated } = view;
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

  const stepsBadge = running
    ? { tone: 'active', label: 'Reallocating…' }
    : updated
      ? { tone: 'brand', label: 'Updated allocation ready (demo)' }
      : { tone: 'urgent', label: 'Awaiting new recipient' };

  return (
    <Card className={cn('transition-colors duration-300', unavailable && 'border-l-2 border-l-urgent')}>
      <Card.Header
        icon={Users}
        title="Recipient Allocation"
        subtitle={
          updated
            ? `${view.operationId} · ${view.total} ${view.unit} · updated across ${updated.length} recipients`
            : `${view.operationId} · ${view.total} ${view.unit} across ${view.rows.length} recipients`
        }
        action={
          <Badge tone="predicted" icon={FlaskConical} size="sm">
            DEMO SCENARIO
          </Badge>
        }
      />

      <Card.Body className="space-y-5">
        {unavailable && (
          <ReallocationWarning
            ref={warningRef}
            role={running ? 'alert' : 'note'}
            warning={view.warning}
          />
        )}

        {updated ? (
          <AllocationComparison view={view} />
        ) : (
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
        )}

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

        {updated && <WhyChanged view={view} />}

        {unavailable && (
          <div className="space-y-4 border-t border-line pt-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-semibold text-content">Mock reallocation</p>
              <Badge tone={stepsBadge.tone} size="sm">
                {stepsBadge.label}
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

            {settled && !updated && (
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
          ? updated
            ? `Reallocation finished. ${view.operationId} has an updated demo allocation: all ${view.total} ${view.unit} are placed.`
            : `Reallocation search finished. ${view.operationId} is Reallocating and ${view.unplaced} ${view.unit} still need a recipient.`
          : ''}
      </p>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Previous vs updated allocation                                       */
/* ------------------------------------------------------------------ */

/** How a recipient's share moved, as a badge: tone and text. */
function changeBadge(row) {
  switch (row.change) {
    case 'new':
      return { tone: 'brand', label: 'New recipient' };
    case 'increased':
      return { tone: 'active', label: `+${row.delta} ${row.unit}` };
    case 'decreased':
      return { tone: 'urgent', label: `−${Math.abs(row.delta)} ${row.unit}` };
    default:
      return { tone: 'neutral', label: 'Unchanged' };
  }
}

/**
 * The previous allocation (with NGO A struck out) next to the updated one
 * (with what changed for each recipient). Both panels end in a total, so it is
 * visible at a glance that the amount stays exactly the same.
 */
function AllocationComparison({ view }) {
  const previousTotal = view.rows.reduce((sum, row) => sum + row.portions, 0);
  const updatedTotal = view.updated.reduce((sum, row) => sum + row.updated, 0);

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] md:items-stretch">
      <AllocationPanel
        title="Previous allocation"
        badge={{ tone: 'neutral', label: 'Original plan' }}
        total={previousTotal}
        unit={view.unit}
      >
        {view.rows.map((row) => {
          const down = row.state === 'unavailable';
          return (
            <li
              key={row.id}
              className={cn('flex items-center justify-between gap-3 px-3.5 py-3', down && 'bg-critical/5')}
            >
              <div className="min-w-0">
                <p className={cn('text-sm font-medium', down ? 'text-muted' : 'text-content')}>
                  {row.name}
                </p>
                {down && <p className="mt-0.5 text-[11px] text-critical">Became unavailable</p>}
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1">
                <span
                  className={cn(
                    'tabular text-sm font-semibold',
                    down ? 'text-faint line-through' : 'text-content',
                  )}
                >
                  {row.portions} {row.unit}
                </span>
                {down && (
                  <Badge tone="critical" size="sm">
                    Unavailable
                  </Badge>
                )}
              </div>
            </li>
          );
        })}
      </AllocationPanel>

      <div className="flex items-center justify-center text-faint" aria-hidden="true">
        <ArrowRight size={18} strokeWidth={1.75} className="rotate-90 md:rotate-0" />
      </div>

      <AllocationPanel
        title="Updated allocation"
        badge={{ tone: 'brand', label: 'Demo recalculation' }}
        total={updatedTotal}
        unit={view.unit}
      >
        {view.updated.map((row) => {
          const badge = changeBadge(row);
          return (
            <li key={row.id} className="flex items-center justify-between gap-3 px-3.5 py-3">
              <div className="min-w-0">
                <p className="text-sm font-medium text-content">{row.name}</p>
                {row.change === 'increased' && (
                  <p className="mt-0.5 text-[11px] text-muted">
                    Was {row.previous} {row.unit}
                  </p>
                )}
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1">
                <span className="tabular text-sm font-semibold text-content">
                  {row.updated} {row.unit}
                </span>
                <Badge tone={badge.tone} size="sm">
                  {badge.label}
                </Badge>
              </div>
            </li>
          );
        })}
      </AllocationPanel>
    </div>
  );
}

function AllocationPanel({ title, badge, total, unit, children }) {
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className="flex min-w-0 flex-col overflow-hidden rounded-control border border-line"
    >
      <div className="flex items-center justify-between gap-2 border-b border-line bg-surface-2 px-3.5 py-2.5">
        <h4 id={headingId} className="text-xs font-semibold text-content">
          {title}
        </h4>
        <Badge tone={badge.tone} size="sm">
          {badge.label}
        </Badge>
      </div>
      <ul className="flex-1 divide-y divide-line">{children}</ul>
      <div className="flex items-center justify-between gap-2 border-t border-line bg-surface-2 px-3.5 py-2.5 text-xs">
        <span className="font-medium text-muted">Total</span>
        <span className="tabular font-semibold text-content">
          {total} {unit}
        </span>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Why the allocation changed                                           */
/* ------------------------------------------------------------------ */

/**
 * The cause and the method, in plain words, with the per-recipient
 * constraint checks tucked into a collapsible list. Everything shown is read
 * from the demo data (see services/reallocationDemoService.js) — no scores.
 */
function WhyChanged({ view }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  return (
    <div className="space-y-3 rounded-control border border-line bg-surface-2 px-3.5 py-3.5">
      <p className="text-xs font-semibold text-content">Why the allocation changed</p>
      <p className="text-xs leading-relaxed text-muted">{view.whyChanged}</p>
      <p className="text-xs leading-relaxed text-muted">
        <span className="font-medium text-content">Rule used: </span>
        {view.rule}
      </p>

      <div className="border-t border-line pt-3">
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          aria-controls={panelId}
          className="flex w-full items-center justify-between gap-2 rounded-control text-left text-xs font-medium text-brand-400 transition-colors duration-150 hover:text-brand-300"
        >
          <span className="flex items-center gap-1.5">
            <ListChecks size={14} strokeWidth={1.75} />
            Constraint checks per recipient
          </span>
          <ChevronDown
            size={15}
            strokeWidth={1.75}
            className={cn('shrink-0 transition-transform duration-200', open && 'rotate-180')}
          />
        </button>

        {open && (
          <div id={panelId} className="mt-3 space-y-4">
            <ul className="space-y-3.5">
              {view.updated.map((row) => (
                <li key={row.id}>
                  <p className="text-xs font-medium text-content">
                    {row.name} — {row.updated} {row.unit}
                  </p>
                  <ul className="mt-2 space-y-2">
                    {row.checks.map((check) => (
                      <li key={check.key} className="flex items-start gap-2">
                        <CheckCircle2
                          size={14}
                          strokeWidth={2}
                          className="mt-0.5 shrink-0 text-success"
                        />
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-content">{check.label}</p>
                          <p className="mt-0.5 break-words text-[11px] text-muted">{check.detail}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>

            <div>
              <p className="text-xs font-medium text-content">Not used in the updated allocation</p>
              <ul className="mt-2 space-y-2">
                {view.excluded.map((entry) => (
                  <li key={entry.id} className="flex items-start gap-2">
                    <XCircle size={14} strokeWidth={2} className="mt-0.5 shrink-0 text-critical" />
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-content">{entry.name}</p>
                      <p className="mt-0.5 break-words text-[11px] text-muted">{entry.reason}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>

      <p className="flex items-start gap-1.5 border-t border-line pt-3 text-[11px] text-faint">
        <FlaskConical size={12} strokeWidth={1.75} className="mt-0.5 shrink-0 text-predicted" />
        <span>{view.disclaimer}</span>
      </p>
    </div>
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
