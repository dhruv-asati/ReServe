import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Circle,
  FlaskConical,
  ListChecks,
  Loader2,
  Package,
  Play,
  RotateCw,
  ShieldCheck,
  Users,
  GitBranch,
} from 'lucide-react';

import { Badge, Button, Card, EmptyState, LoadingState, Skeleton } from '@/components/ui';
import MatchCandidateCard from '@/components/MatchCandidateCard';
import AllocationResultCard from '@/components/AllocationResultCard';
import ReallocationWarning from '@/components/ReallocationWarning';
import useReallocationDemo from '@/hooks/useReallocationDemo';
import { RESOURCE_ICONS } from '@/utils/icons';
import { RESOURCE_META, URGENCY_META } from '@/utils/theme';
import { PATHS } from '@/routes/paths';
import {
  MATCHING_STEPS,
  MATCHING_STEP_DURATION_MS,
  getMatchingResource,
  getMatchingCandidates,
} from '@/services/matchingService';
import {
  applyDemoToMatchCandidates,
  getReallocationView,
} from '@/services/reallocationDemoService';

/** Urgency → Badge tone. Same weighting AIAnalysis and AtRiskCard use. */
const URGENCY_TONE = {
  critical: 'critical',
  high: 'urgent',
  medium: 'active',
  low: 'neutral',
};

const PHASE = {
  IDLE: 'idle',
  RUNNING: 'running',
  COMPLETE: 'complete',
};

/** Recalculation replays the same stages, just faster (demo only). */
const RECALC_STEP_DURATION_MS = 400;

/**
 * Demo validation for the proposed allocation plan: the summed allocations
 * must equal the available resource quantity exactly (neither over- nor
 * under-allocated). Pure and local — no backend call.
 */
function validateAllocationPlan(resource, allocations) {
  const quantity = resource?.quantity;
  const unit = resource?.unit ?? '';
  const total = allocations.reduce((sum, item) => sum + (Number(item.allocatedQuantity) || 0), 0);
  const problems = [];

  if (!Number.isFinite(quantity)) {
    problems.push('The resource quantity is not available.');
  }
  if (allocations.length === 0) {
    problems.push('There are no proposed allocations to confirm.');
  }
  if (allocations.some((item) => !Number.isFinite(item.allocatedQuantity) || item.allocatedQuantity < 0)) {
    problems.push('Every allocation must be a valid, non-negative quantity.');
  }
  if (Number.isFinite(quantity) && total !== quantity) {
    const difference = Math.abs(quantity - total);
    problems.push(
      `Allocated total (${total} ${unit}) does not match the available quantity (${quantity} ${unit}) — ${difference} ${unit} ${total > quantity ? 'over-allocated' : 'left unallocated'}.`,
    );
  }

  return {
    valid: problems.length === 0,
    problems,
    total,
    quantity,
    unit,
    remaining: Number.isFinite(quantity) ? quantity - total : null,
  };
}

/**
 * Smart Matching — base page for finding feasible recipients and (later)
 * building resource allocation plans.
 *
 * Sections, top to bottom (side by side from xl up):
 *   1. Page header
 *   2. Selected resource summary
 *   3. Matching process     — simulated step checklist + "Start Matching"
 *   4. Matching results     — placeholder until the matching logic exists
 *   5. Allocation summary   — totals only; allocation cards come later
 *
 * Frontend only: "Start Matching" runs a timed, purely cosmetic step
 * sequence. No algorithm, backend or API call is involved, and no recipients
 * are invented — results stay empty on purpose.
 *
 * RS-1024 demo: when the operation's recipient has been marked unavailable
 * on the Operations page, this page reflects it — NGO A cannot be selected,
 * its 50-portion share drops out of the proposed allocation, and the plan
 * validation below reports the unallocated remainder (so Confirm stays
 * disabled). Once the mock reallocation there has finished, the updated
 * allocation (Shelter B 20, NGO D 40, Night Rescue Hub 20 with the demo data)
 * is written onto the candidates: the Proposed Allocation cards show it, the
 * total is 80 again, and validation passes. Nothing is sent anywhere; see
 * services/reallocationDemoService.js.
 *
 * Plan actions (in the Allocation Summary card): "Recalculate Match" replays
 * the simulated stages and restores the demo allocation; "Confirm Rescue
 * Plan" is only enabled while the allocation total equals the resource
 * quantity, and then marks the demo plan confirmed. Neither creates a real
 * rescue, contacts any organization or touches a backend.
 */
export default function Matching() {
  const [resource, setResource] = useState(null);
  // The mock candidates as fetched. The RS-1024 recipient-unavailable demo
  // (see the Operations page) is applied on top, so an unavailable NGO A is
  // never offered or allocated here — not even after "Recalculate Match".
  const [baseCandidates, setCandidates] = useState(null);
  const demo = useReallocationDemo();
  const candidates = useMemo(
    () => applyDemoToMatchCandidates(baseCandidates, demo),
    [baseCandidates, demo],
  );
  const reallocation = useMemo(() => getReallocationView(demo), [demo]);
  const [phase, setPhase] = useState(PHASE.IDLE);
  const [completedSteps, setCompletedSteps] = useState(0);
  const [lastRun, setLastRun] = useState('start'); // 'start' | 'recalculate'
  const [confirmation, setConfirmation] = useState(null);
  const timersRef = useRef([]);
  const fetchIdRef = useRef(0);
  const confirmationRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;
    getMatchingResource().then((data) => active && setResource(data));
    getMatchingCandidates().then((data) => active && setCandidates(data));
    return () => {
      active = false;
    };
  }, []);

  // Never leave a simulated run ticking after the page is gone.
  useEffect(
    () => () => {
      timersRef.current.forEach(clearTimeout);
      fetchIdRef.current = -1; // ignore any in-flight mock fetch
    },
    [],
  );

  // Bring the confirmation result into view (it sits below the action buttons).
  useEffect(() => {
    if (!confirmation || !confirmationRef.current) return;
    confirmationRef.current.focus({ preventScroll: true });
    confirmationRef.current.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [confirmation]);

  const runMatching = (kind) => {
    const recalculating = kind === 'recalculate';
    timersRef.current.forEach(clearTimeout);
    setConfirmation(null); // any earlier confirmation no longer applies
    setLastRun(kind);
    setPhase(PHASE.RUNNING);
    setCompletedSteps(0);

    if (recalculating) {
      // Restore the demo allocation from the same mock source.
      const fetchId = ++fetchIdRef.current;
      getMatchingCandidates().then((data) => {
        if (fetchIdRef.current === fetchId) setCandidates(data);
      });
    }

    const stepMs = recalculating ? RECALC_STEP_DURATION_MS : MATCHING_STEP_DURATION_MS;
    timersRef.current = MATCHING_STEPS.map((_, index) =>
      setTimeout(() => {
        setCompletedSteps(index + 1);
        if (index === MATCHING_STEPS.length - 1) setPhase(PHASE.COMPLETE);
      }, stepMs * (index + 1)),
    );
  };

  const startMatching = () => runMatching('start');
  const recalculateMatch = () => runMatching('recalculate');

  const running = phase === PHASE.RUNNING;
  const complete = phase === PHASE.COMPLETE;
  const recalculating = running && lastRun === 'recalculate';
  const progress = (completedSteps / MATCHING_STEPS.length) * 100;

  // Proposed demo allocation: candidates with a non-null allocatedQuantity.
  // Purely derived from the mock candidate list — no optimization routine
  // or backend call involved.
  const proposedAllocations = (candidates ?? []).filter(
    (candidate) => candidate.allocatedQuantity != null,
  );
  const allocatedTotal = proposedAllocations.reduce(
    (sum, candidate) => sum + candidate.allocatedQuantity,
    0,
  );

  // Live validation: the allocation total must equal the resource quantity.
  const planCheck = validateAllocationPlan(resource, proposedAllocations);

  // Demo confirmation: only possible when the plan validates, and it only
  // updates this page's mock state. No request is made, no one is contacted.
  const confirmPlan = () => {
    if (!planCheck.valid) return;
    setConfirmation({
      ...planCheck,
      allocations: proposedAllocations.map(({ id, name, allocatedQuantity, unit }) => ({
        id,
        name,
        allocatedQuantity,
        unit,
      })),
    });
  };
  const confirmed = confirmation !== null;

  return (
    <div className="animate-fade-up space-y-6 lg:space-y-8">
      {/* ---------- 1. Page header ---------- */}
      <div>
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="text-xl font-bold tracking-tight text-content sm:text-2xl">
            Smart Matching
          </h1>
          <Badge tone="predicted" icon={FlaskConical} size="sm">
            DEMO / MOCK MATCHING
          </Badge>
        </div>
        <p className="mt-1.5 text-sm text-muted">
          Find feasible recipients and create resource allocation plans.
        </p>
      </div>

      {/* ---------- RS-1024 recipient-unavailable demo notice ---------- */}
      {reallocation.unavailable && (
        <ReallocationWarning variant="compact" warning={reallocation.warning}>
          <Link
            to={PATHS.LIVE_OPERATIONS}
            className="text-xs font-medium text-urgent underline underline-offset-2 hover:text-content"
          >
            Open {reallocation.operationId} in Operations
          </Link>
        </ReallocationWarning>
      )}

      {/* ---------- 2. Selected resource summary ---------- */}
      <ResourceSummary
        resource={resource}
        planStatus={confirmed ? 'confirmed' : complete ? 'proposed' : 'pending'}
      />

      <div className="grid grid-cols-1 gap-6 lg:gap-8 xl:grid-cols-3">
        <div className="min-w-0 space-y-6 lg:space-y-8 xl:col-span-2">
          {/* ---------- 3. Matching process ---------- */}
          <Card>
            <Card.Header
              icon={GitBranch}
              title="Matching Process"
              subtitle="Each recipient is checked against the rescue constraints."
              action={
                <Badge tone={complete ? 'success' : running ? 'active' : 'neutral'} size="sm">
                  {complete
                    ? 'Complete'
                    : recalculating
                      ? 'Recalculating…'
                      : running
                        ? 'Matching…'
                        : 'Not started'}
                </Badge>
              }
            />
            <Card.Body>
              {recalculating && (
                <div
                  className="mb-5 flex items-center gap-2.5 rounded-control border border-predicted/25 bg-predicted/10 px-3.5 py-2.5"
                  role="status"
                >
                  <FlaskConical size={16} strokeWidth={2} className="shrink-0 text-predicted" />
                  <p className="text-sm font-medium text-predicted">
                    Demo recalculation — replaying the simulated matching stages locally.
                  </p>
                </div>
              )}
              <ol className="space-y-3">
                {MATCHING_STEPS.map((step, index) => {
                  const state =
                    index < completedSteps
                      ? 'complete'
                      : running && index === completedSteps
                        ? 'active'
                        : 'pending';
                  return <StepRow key={step.key} label={step.label} state={state} />;
                })}
              </ol>

              {complete && (
                <div className="mt-5 flex items-center gap-2.5 rounded-control border border-success/25 bg-success/10 px-3.5 py-2.5">
                  <CheckCircle2 size={16} strokeWidth={2} className="shrink-0 text-success" />
                  <p className="text-sm font-medium text-success">
                    {lastRun === 'recalculate'
                      ? reallocation.unavailable
                        ? `Demo recalculation completed — ${reallocation.matchingNote}`
                        : 'Demo recalculation completed — demo allocation results restored.'
                      : 'Matching analysis completed.'}
                  </p>
                </div>
              )}

              <div
                className="mt-5 h-1.5 w-full overflow-hidden rounded-full bg-surface-3"
                role="progressbar"
                aria-label="Matching progress"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(progress)}
              >
                <div
                  className="h-full rounded-full bg-brand-500 transition-all duration-300 ease-soft"
                  style={{ width: `${progress}%` }}
                />
              </div>

              <div className="mt-5 flex flex-col gap-3 border-t border-line pt-4 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs text-faint" aria-live="polite">
                  {running
                    ? `${recalculating ? 'Demo recalculation — step' : 'Step'} ${Math.min(completedSteps + 1, MATCHING_STEPS.length)} of ${MATCHING_STEPS.length} — simulated locally.`
                    : complete
                      ? 'Simulation finished. No matching logic has run yet.'
                      : 'Simulated locally — no matching engine or backend call is made.'}
                </p>
                <Button
                  icon={complete ? RotateCw : Play}
                  variant={complete ? 'secondary' : 'primary'}
                  loading={running}
                  disabled={!resource}
                  onClick={startMatching}
                  className="w-full justify-center sm:w-auto"
                >
                  {recalculating
                    ? 'Recalculating…'
                    : running
                      ? 'Matching…'
                      : complete
                        ? 'Restart Matching'
                        : 'Start Matching'}
                </Button>
              </div>
            </Card.Body>
          </Card>

          {/* ---------- 4. Matching results ---------- */}
          <Card>
            <Card.Header
              icon={Users}
              title="Matching Results"
              subtitle="Feasible recipients for this resource."
              action={
                complete && (
                  <Badge tone="predicted" icon={FlaskConical} size="sm">
                    DEMO DATA
                  </Badge>
                )
              }
            />
            {running ? (
              <Card.Body>
                <LoadingState
                  variant="skeleton"
                  rows={3}
                  label={recalculating ? 'Recalculating demo results…' : 'Evaluating recipients…'}
                />
              </Card.Body>
            ) : complete ? (
              <Card.Body>
                <p className="mb-4 text-xs text-faint">
                  Hardcoded demo candidates for this walkthrough — not looked up, scored or
                  ranked by any model or backend, and not real organizations.
                </p>
                {candidates?.length ? (
                  <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
                    {candidates.map((candidate) => (
                      <MatchCandidateCard key={candidate.id} candidate={candidate} />
                    ))}
                  </div>
                ) : (
                  <LoadingState variant="skeleton" rows={3} label="Loading demo candidates…" />
                )}
              </Card.Body>
            ) : (
              <EmptyState
                icon={Users}
                title="No matching results yet"
                description="Start matching to look for feasible recipients for this resource."
              />
            )}
          </Card>

          {/* ---------- 4b. Proposed allocation ---------- */}
          {complete && proposedAllocations.length > 0 && (
            <Card>
              <Card.Header
                icon={ListChecks}
                title={confirmed ? 'Confirmed Allocation' : 'Proposed Allocation'}
                subtitle="One card per destination this resource is proposed to be split across."
                action={
                  <Badge tone={confirmed ? 'success' : 'brand'} icon={FlaskConical} size="sm">
                    {confirmed ? 'CONFIRMED / DEMO' : 'PROPOSED / DEMO'}
                  </Badge>
                }
              />
              <Card.Body>
                <p className="mb-4 text-xs text-faint">
                  {confirmed
                    ? 'Confirmed as a demo plan only — hardcoded for this walkthrough. No real rescue was created and no organization was contacted.'
                    : reallocation.updated
                      ? `Updated demo split after ${reallocation.recipientName} became unavailable for ${reallocation.operationId} — recalculated by a small scripted rule over the hardcoded demo recipients (details on the Operations page). Not a live production allocation, and not yet confirmed or dispatched. No confidence or optimization scores are implied.`
                      : 'A proposed demo split only — hardcoded for this walkthrough, not the output of an optimization routine, and not yet confirmed or dispatched. No confidence or optimization scores are implied.'}
                </p>
                <div className="grid grid-cols-1 items-start gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
                  {proposedAllocations.map((allocation) => (
                    <AllocationResultCard
                      key={allocation.id}
                      allocation={allocation}
                      resource={resource}
                      confirmed={confirmed}
                    />
                  ))}
                </div>
              </Card.Body>
            </Card>
          )}
        </div>

        {/* ---------- 5. Allocation summary ---------- */}
        <div className="min-w-0 space-y-6 lg:space-y-8">
          <AllocationSummary
            resource={resource}
            complete={complete}
            confirmed={confirmed}
            allocatedTotal={allocatedTotal}
            actions={
              <PlanActions
                running={running}
                recalculating={recalculating}
                complete={complete}
                confirmed={confirmed}
                check={planCheck}
                canConfirm={Boolean(resource) && planCheck.valid}
                onRecalculate={recalculateMatch}
                onConfirm={confirmPlan}
              />
            }
          />
          {confirmation && (
            <ConfirmationPanel
              ref={confirmationRef}
              confirmation={confirmation}
              resource={resource}
              onContinue={() => navigate(PATHS.LIVE_OPERATIONS)}
            />
          )}
        </div>
      </div>

      {/* Announces state changes to screen readers */}
      <p className="sr-only" aria-live="polite">
        {running
          ? recalculating
            ? 'Demo recalculation started.'
            : 'Matching started.'
          : confirmed
            ? 'Demo rescue plan confirmed.'
            : complete
              ? lastRun === 'recalculate'
                ? 'Demo recalculation complete.'
                : 'Matching complete.'
              : ''}
      </p>
    </div>
  );
}

/** One line of the process checklist. */
function StepRow({ label, state }) {
  return (
    <li className="flex items-center gap-3">
      <span
        className={
          state === 'complete'
            ? 'flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-success/10 text-success'
            : state === 'active'
              ? 'flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-500/10 text-brand-400'
              : 'flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-3 text-faint'
        }
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

/** Selected resource card. Shows skeleton fields while the mock resource loads. */
function ResourceSummary({ resource, planStatus = 'pending' }) {
  const typeMeta = resource ? RESOURCE_META[resource.resourceType] : null;
  const TypeIcon = (resource && RESOURCE_ICONS[resource.resourceType]) || Package;
  const urgencyMeta = resource ? URGENCY_META[resource.urgency] : null;

  return (
    <Card>
      <Card.Header
        icon={Package}
        title="Selected Resource"
        subtitle={resource ? resource.id : 'Loading…'}
        action={
          resource && (
            <Badge
              tone={
                planStatus === 'confirmed' ? 'success' : planStatus === 'proposed' ? 'brand' : 'neutral'
              }
              size="sm"
            >
              {planStatus === 'confirmed'
                ? 'Plan confirmed (Demo)'
                : planStatus === 'proposed'
                  ? 'Plan proposed (Demo)'
                  : 'Awaiting matching'}
            </Badge>
          )
        }
      />
      <Card.Body>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-3 lg:grid-cols-4">
          <Field label="Resource ID" loading={!resource}>
            <span className="font-mono text-xs">{resource?.id}</span>
          </Field>
          <Field label="Resource" loading={!resource}>
            {resource?.resource}
          </Field>
          <Field label="Resource Type" loading={!resource}>
            <Badge tone={resource?.resourceType ?? 'neutral'} icon={TypeIcon} size="sm">
              {typeMeta?.label ?? resource?.resourceType}
            </Badge>
          </Field>
          <Field label="Quantity" loading={!resource}>
            <span className="tabular">
              {resource?.quantity} {resource?.unit}
            </span>
          </Field>
          <Field label="Provider" loading={!resource}>
            {resource?.provider}
          </Field>
          <Field label="Location" loading={!resource}>
            {resource?.location}
          </Field>
          <Field label="Urgency" loading={!resource}>
            <Badge tone={URGENCY_TONE[resource?.urgency] ?? 'neutral'} dot size="sm">
              {urgencyMeta?.label ?? resource?.urgency}
            </Badge>
          </Field>
          <Field label="Rescue Window" loading={!resource}>
            <span className="tabular">{resource?.rescueWindowMinutes} minutes</span>
          </Field>
        </dl>
      </Card.Body>
    </Card>
  );
}

function Field({ label, loading, children }) {
  return (
    <div className="min-w-0">
      <dt className="text-[10px] font-medium uppercase tracking-wide text-faint">{label}</dt>
      <dd className="mt-1 break-words text-sm font-medium text-content">
        {loading ? <Skeleton className="h-4 w-24" /> : children}
      </dd>
    </div>
  );
}

/**
 * Allocation summary — totals for the proposed demo allocation. Before
 * matching completes, nothing is allocated yet and the full quantity shows
 * as remaining; once complete, totals reflect the proposed demo split
 * (see Proposed Allocation above). Confirming only marks the demo plan as
 * confirmed — nothing is dispatched or created anywhere.
 */
function AllocationSummary({
  resource,
  complete,
  confirmed = false,
  allocatedTotal = 0,
  actions = null,
}) {
  const total = resource?.quantity ?? null;
  const allocated = complete ? allocatedTotal : 0;
  const remaining = total === null ? null : total - allocated;
  const percent = total ? (allocated / total) * 100 : 0;

  return (
    <Card>
      <Card.Header
        icon={ListChecks}
        title="Allocation Summary"
        subtitle={resource ? `Plan for ${resource.id}` : 'Loading…'}
        action={
          <Badge tone={confirmed ? 'success' : complete ? 'brand' : 'neutral'} size="sm">
            {confirmed ? 'Confirmed (Demo)' : complete ? 'Proposed (Demo)' : 'Awaiting matching'}
          </Badge>
        }
      />
      <Card.Body>
        <dl className="grid grid-cols-3 gap-3">
          <Metric label="Total Resource Quantity" value={total} unit={resource?.unit} loading={!resource} />
          <Metric label="Total Allocated" value={allocated} unit={resource?.unit} loading={!resource} />
          <Metric label="Remaining Quantity" value={remaining} unit={resource?.unit} loading={!resource} />
        </dl>

        {resource && (
          <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted">
            <span className="flex items-center gap-1.5">
              Urgency
              <Badge tone={URGENCY_TONE[resource.urgency] ?? 'neutral'} dot size="sm">
                {URGENCY_META[resource.urgency]?.label ?? resource.urgency}
              </Badge>
            </span>
            <span className="flex items-center gap-1.5">
              Rescue window
              <span className="tabular font-medium text-content">
                {resource.rescueWindowMinutes} minutes
              </span>
            </span>
          </div>
        )}

        <div
          className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-surface-3"
          role="progressbar"
          aria-label="Quantity allocated"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(percent)}
        >
          <div
            className="h-full rounded-full bg-brand-500 transition-all duration-300 ease-soft"
            style={{ width: `${percent}%` }}
          />
        </div>

        <p className="mt-4 text-xs text-muted">
          {confirmed
            ? 'Reflects the confirmed demo allocation — a demo state only; nothing was dispatched.'
            : complete
              ? 'Reflects the proposed demo allocation above — not yet confirmed or dispatched.'
              : 'Recipient allocations will appear here once matching has run.'}
        </p>

        {actions}
      </Card.Body>
    </Card>
  );
}

function Metric({ label, value, unit, loading }) {
  return (
    <div className="min-w-0 rounded-control border border-line bg-surface-2 px-3 py-2.5">
      <dt className="text-[10px] font-medium uppercase tracking-wide text-faint">{label}</dt>
      <dd className="mt-1 text-content">
        {loading ? (
          <Skeleton className="h-5 w-8" />
        ) : (
          <>
            <span className="tabular text-lg font-semibold tracking-tight">{value}</span>
            {unit && ' '}
            {unit && <span className="text-[11px] font-medium text-muted">{unit}</span>}
          </>
        )}
      </dd>
    </div>
  );
}

/**
 * The two plan actions. Both are demo-only: Recalculate replays the mock
 * stages; Confirm is only enabled while the proposed split validates (total
 * equals the resource quantity) and otherwise a validation message explains
 * why. Stacked in the narrow xl side column, side by side on wider
 * single-column layouts.
 */
function PlanActions({
  running,
  recalculating,
  complete,
  confirmed,
  check,
  canConfirm,
  onRecalculate,
  onConfirm,
}) {
  const showCheck = complete && !running && !confirmed;
  const hint = running
    ? recalculating
      ? 'Demo recalculation in progress…'
      : 'Matching in progress…'
    : !complete
      ? 'Run matching first to enable these actions.'
      : confirmed
        ? 'Confirmed as a demo plan — no rescue was created and no organization was contacted.'
        : 'Demo only: recalculating replays the simulated stages, and confirming marks this plan as confirmed in the demo. Nothing is sent to a backend and no organization is contacted.';

  return (
    <div className="mt-5 border-t border-line pt-4">
      {showCheck &&
        (check.valid ? (
          <p
            className="mb-3 flex items-start gap-2 rounded-control border border-success/25 bg-success/10 px-3 py-2 text-xs font-medium text-success"
            role="status"
          >
            <CheckCircle2 size={14} strokeWidth={2} className="mt-0.5 shrink-0" />
            <span className="min-w-0 break-words">
              Allocation total matches the available quantity ({check.total} = {check.quantity}{' '}
              {check.unit}). Ready to confirm.
            </span>
          </p>
        ) : (
          <div
            className="mb-3 space-y-1.5 rounded-control border border-critical/25 bg-critical/10 px-3 py-2"
            role="alert"
          >
            {check.problems.map((problem) => (
              <p
                key={problem}
                className="flex items-start gap-2 text-xs font-medium text-critical"
              >
                <AlertTriangle size={14} strokeWidth={2} className="mt-0.5 shrink-0" />
                <span className="min-w-0 break-words">{problem}</span>
              </p>
            ))}
            <p className="text-[11px] text-critical/80">
              Confirmation is disabled until the allocation total equals the resource quantity.
            </p>
          </div>
        ))}
      <div className="flex flex-col gap-2.5 sm:flex-row xl:flex-col">
        <Button
          variant="secondary"
          icon={RotateCw}
          loading={recalculating}
          disabled={!complete || running}
          onClick={onRecalculate}
          className="w-full justify-center sm:flex-1"
        >
          {recalculating ? 'Recalculating…' : 'Recalculate Match'}
        </Button>
        <Button
          icon={confirmed ? CheckCircle2 : ShieldCheck}
          disabled={!complete || running || !canConfirm || confirmed}
          onClick={onConfirm}
          className="w-full justify-center sm:flex-1"
        >
          {confirmed ? 'Plan Confirmed (Demo)' : 'Confirm Rescue Plan'}
        </Button>
      </div>
      <p className="mt-3 flex items-start gap-1.5 text-[11px] text-faint" aria-live="polite">
        <FlaskConical size={12} strokeWidth={1.75} className="mt-0.5 shrink-0 text-predicted" />
        <span>{hint}</span>
      </p>
    </div>
  );
}

/**
 * Result of "Confirm Rescue Plan" (only reachable once the plan validated).
 * Shows the confirmed demo allocation summary and the way on to Live
 * Operations. Deliberately worded as a demo — no real rescue is created, no
 * organization is contacted and nothing is sent anywhere.
 */
function ConfirmationPanel({ ref, confirmation, resource, onContinue }) {
  const { allocations, total, quantity, remaining, unit } = confirmation;

  return (
    <div ref={ref} tabIndex={-1} role="status" className="outline-none">
      <Card className="border-l-2 border-l-success">
        <Card.Header
          icon={ShieldCheck}
          title="Rescue Plan Confirmed"
          subtitle={resource ? `Demo plan for ${resource.id}` : 'Demo plan'}
          action={
            <Badge tone="success" icon={FlaskConical} size="sm">
              CONFIRMED (DEMO)
            </Badge>
          }
        />
        <Card.Body className="space-y-4">
          <div className="flex items-start gap-2.5 rounded-control border border-success/25 bg-success/10 px-3.5 py-2.5">
            <CheckCircle2 size={16} strokeWidth={2} className="mt-0.5 shrink-0 text-success" />
            <p className="text-sm font-medium text-success">
              Validation passed — {total} of {quantity} {unit} allocated, matching the resource
              quantity exactly.
            </p>
          </div>

          {resource && (
            <p className="text-xs text-muted">
              {resource.resource} · {resource.provider} ·{' '}
              {URGENCY_META[resource.urgency]?.label ?? resource.urgency} urgency ·{' '}
              {resource.rescueWindowMinutes}-minute rescue window
            </p>
          )}

          <p className="text-xs text-faint">
            Demo confirmation only. No real rescue was created, no organization was contacted and
            no request was sent to any backend.
          </p>

          <div>
            <p className="text-[10px] font-medium uppercase tracking-wide text-faint">
              Confirmed demo allocation
            </p>
            <ul className="mt-2 divide-y divide-line rounded-control border border-line">
              {allocations.map((item) => (
                <li key={item.id} className="flex items-center justify-between gap-3 px-3 py-2.5">
                  <span className="min-w-0 break-words text-sm text-content">{item.name}</span>
                  <span className="tabular shrink-0 text-sm font-semibold text-content">
                    {item.allocatedQuantity} {item.unit}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <dl className="grid grid-cols-3 gap-3">
            <SummaryStat label="Resource Quantity" value={quantity} unit={unit} />
            <SummaryStat label="Total Allocated" value={total} unit={unit} />
            <SummaryStat label="Remaining" value={remaining} unit={unit} />
          </dl>

          <Button
            iconRight={ArrowRight}
            onClick={onContinue}
            className="w-full justify-center"
          >
            Continue to Live Operations
          </Button>
        </Card.Body>
      </Card>
    </div>
  );
}

function SummaryStat({ label, value, unit }) {
  return (
    <div className="min-w-0 rounded-control border border-line bg-surface-2 px-3 py-2.5">
      <dt className="text-[10px] font-medium uppercase tracking-wide text-faint">{label}</dt>
      <dd className="mt-1 text-content">
        <span className="tabular text-lg font-semibold tracking-tight">{value}</span>
        {unit && ' '}
        {unit && <span className="text-[11px] font-medium text-muted">{unit}</span>}
      </dd>
    </div>
  );
}
