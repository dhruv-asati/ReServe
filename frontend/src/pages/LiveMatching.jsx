import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { CheckCircle2, GitBranch, ListChecks, Package, PlusCircle, Radio, RotateCw } from 'lucide-react';

import { Badge, Button, Card, EmptyState, ErrorState, LoadingState, Select, StatusBadge } from '@/components/ui';
import { RESOURCE_ICONS } from '@/utils/icons';
import { RESOURCE_META, URGENCY_META } from '@/utils/theme';
import { getRescue } from '@/services/rescueService';
import {
  confirmAllocationPlan,
  getLatestMatching,
  listMatchableResources,
  runMatching,
} from '@/services/matchingService';
import { formatMinutes, resourceStatusToUi, toDisplayResource } from '@/services/resourceAdapter';
import { PATHS } from '@/routes/paths';

const URGENCY_TONE = { critical: 'critical', high: 'urgent', medium: 'active', low: 'neutral' };

const round2 = (value) => Math.round(value * 100) / 100;
const fmt = (value) => Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });

const isRejected = (candidate) => candidate.status === 'REJECTED' || candidate.rejection_reasons.length > 0;

/**
 * Propose a split across the eligible candidates: best score first, each taking
 * as much as it can (its declared capacity, or whatever is left when it has no
 * limit) until the requested quantity is covered. The person can edit or drop
 * any line before confirming — the backend re-checks every allocation.
 */
function buildPlan(results) {
  let remaining = Number(results.requested_quantity);
  const plan = {};
  results.candidates
    .filter((candidate) => !isRejected(candidate))
    .sort((a, b) => b.score - a.score)
    .forEach((candidate) => {
      const capacity = candidate.recipient.capacity;
      const share = remaining > 0 ? Math.min(remaining, capacity != null ? Number(capacity) : remaining) : 0;
      plan[candidate.match_id] = { include: share > 0, quantity: share > 0 ? String(round2(share)) : '' };
      remaining -= share;
    });
  return plan;
}

/**
 * Smart Matching for live data (VITE_USE_MOCKS=false).
 *
 *   1. pick one of your resources that still needs a home
 *   2. run the backend matching engine (POST /api/matching/{id})
 *   3. review the proposed split, adjust it, and confirm — which creates one
 *      allocation per recipient and then the rescue operation that carries them out
 *
 * Nothing here is simulated: every recipient shown is a real, registered
 * organization, and confirming writes real allocations.
 */
export default function LiveMatching() {
  const { rescueId } = useParams();

  const [loadState, setLoadState] = useState('loading'); // loading | ready | error
  const [loadError, setLoadError] = useState(null);
  const [resources, setResources] = useState([]); // backend ResourceOut[]
  const [selectedId, setSelectedId] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  const [results, setResults] = useState(null); // MatchingResultsData
  const [plan, setPlan] = useState({});
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState(null);

  const [confirming, setConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState(null);
  const [confirmed, setConfirmed] = useState(null);

  // ---- Load the resource(s) ----
  useEffect(() => {
    let active = true;
    setLoadState('loading');
    setLoadError(null);

    (async () => {
      try {
        const list = rescueId ? [await getRescue(rescueId)] : await listMatchableResources();
        if (!active) return;
        setResources(list);
        setSelectedId(rescueId ?? list[0]?.id ?? '');
        setLoadState('ready');
      } catch (error) {
        if (!active) return;
        setLoadError(error);
        setLoadState('error');
      }
    })();

    return () => {
      active = false;
    };
  }, [rescueId, reloadKey]);

  // ---- Whenever the selected resource changes, show its latest matching run (if any) ----
  useEffect(() => {
    let active = true;
    setResults(null);
    setPlan({});
    setRunError(null);
    setConfirmError(null);
    setConfirmed(null);
    if (!selectedId) return undefined;

    getLatestMatching(selectedId).then((latest) => {
      if (!active || !latest) return;
      setResults(latest);
      setPlan(buildPlan(latest));
    });

    return () => {
      active = false;
    };
  }, [selectedId]);

  const selected = resources.find((item) => item.id === selectedId) ?? null;
  const resource = selected ? toDisplayResource(selected) : null;

  const handleRun = useCallback(async () => {
    setRunning(true);
    setRunError(null);
    setConfirmError(null);
    try {
      const fresh = await runMatching(selectedId);
      setResults(fresh);
      setPlan(buildPlan(fresh));
    } catch (error) {
      setRunError(error);
    } finally {
      setRunning(false);
    }
  }, [selectedId]);

  // ---- Derived plan state ----
  const { eligible, rejected } = useMemo(() => {
    const all = results?.candidates ?? [];
    return {
      eligible: all.filter((candidate) => !isRejected(candidate)).sort((a, b) => b.score - a.score),
      rejected: all.filter(isRejected),
    };
  }, [results]);

  const chosen = eligible.filter((candidate) => plan[candidate.match_id]?.include);
  const quantityOf = (candidate) => Number(plan[candidate.match_id]?.quantity);
  const total = chosen.reduce((sum, candidate) => sum + (quantityOf(candidate) || 0), 0);
  const requested = results ? Number(results.requested_quantity) : 0;

  const problems = [];
  if (results && chosen.length === 0) problems.push('Select at least one recipient.');
  if (chosen.some((candidate) => !(quantityOf(candidate) > 0))) {
    problems.push('Every selected recipient needs a quantity greater than 0.');
  }
  if (total > requested + 1e-6) {
    problems.push(`The plan allocates ${fmt(total)} but only ${fmt(requested)} ${resource?.unit ?? ''} is available.`);
  }
  const planValid = results && problems.length === 0;
  const unallocated = requested - total;

  const updatePlan = (matchId, patch) =>
    setPlan((current) => ({ ...current, [matchId]: { ...current[matchId], ...patch } }));

  const handleConfirm = async () => {
    if (!planValid) return;
    setConfirming(true);
    setConfirmError(null);
    try {
      const outcome = await confirmAllocationPlan({
        rescueRequestId: results.rescue_request_id,
        allocations: chosen.map((candidate) => ({
          matchId: candidate.match_id,
          quantity: quantityOf(candidate),
          reason: candidate.explanation?.slice(0, 1000),
        })),
      });
      setConfirmed(outcome);
    } catch (error) {
      setConfirmError(error);
    } finally {
      setConfirming(false);
    }
  };

  // ---------------------------------------------------------------------------

  const header = (
    <div>
      <h1 className="text-xl font-bold tracking-tight text-content sm:text-2xl">Smart Matching</h1>
      <p className="mt-1.5 text-sm text-muted">Find feasible recipients and create resource allocation plans.</p>
    </div>
  );

  if (loadState === 'loading') {
    return (
      <div className="animate-fade-up space-y-6">
        {header}
        <LoadingState variant="skeleton" label="Loading resources…" />
      </div>
    );
  }

  if (loadState === 'error') {
    return (
      <div className="animate-fade-up space-y-6">
        {header}
        <Card>
          <ErrorState
            title="Couldn't load your resources"
            description={loadError?.message}
            onRetry={() => setReloadKey((n) => n + 1)}
          />
        </Card>
      </div>
    );
  }

  if (!resource) {
    return (
      <div className="animate-fade-up space-y-6">
        {header}
        <Card>
          <EmptyState
            icon={Package}
            title="No resources to match"
            description="Matching starts from a surplus resource that hasn't been fully allocated yet. Create a rescue to log one."
            action={
              <Button as={Link} to={PATHS.CREATE_RESCUE} icon={PlusCircle}>
                Create Rescue
              </Button>
            }
          />
        </Card>
      </div>
    );
  }

  const TypeIcon = RESOURCE_ICONS[resource.resourceType] ?? Package;
  const typeMeta = RESOURCE_META[resource.resourceType];
  const urgencyMeta = URGENCY_META[resource.urgency];

  if (confirmed) {
    const lastAllocation = confirmed.allocations[confirmed.allocations.length - 1];
    return (
      <div className="animate-fade-up space-y-6">
        {header}
        <Card>
          <Card.Header
            icon={CheckCircle2}
            title="Rescue plan confirmed"
            subtitle={`${resource.resource} · ${confirmed.allocations.length} allocation${confirmed.allocations.length === 1 ? '' : 's'}`}
            action={
              <Badge tone="success" size="sm">
                Operation {confirmed.operation.status?.toLowerCase() ?? 'planned'}
              </Badge>
            }
          />
          <Card.Body className="space-y-4">
            <ul className="divide-y divide-line rounded-control border border-line bg-surface-2 px-3.5">
              {confirmed.allocations.map((allocation) => (
                <li key={allocation.id} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                  <span className="font-medium text-content">
                    {allocation.recipient?.organization_name ?? allocation.rescue_hub?.name ?? 'Recipient'}
                  </span>
                  <span className="text-muted">
                    {fmt(allocation.allocated_quantity)} {resource.unit}
                  </span>
                </li>
              ))}
            </ul>
            {lastAllocation && lastAllocation.resource_remaining_quantity > 0 && (
              <p className="text-xs text-urgent">
                {fmt(lastAllocation.resource_remaining_quantity)} {resource.unit} is still unallocated — run matching
                again to place the rest.
              </p>
            )}
            <p className="text-xs text-faint">
              Operation <span className="font-mono">{confirmed.operation.id}</span> was created to carry this out.
              Track it under Live Operations.
            </p>
          </Card.Body>
          <Card.Footer>
            <div className="flex w-full flex-wrap justify-end gap-2">
              <Button as={Link} to={PATHS.DASHBOARD} variant="secondary">
                Back to dashboard
              </Button>
              <Button as={Link} to={PATHS.LIVE_OPERATIONS} iconRight={Radio}>
                View operations
              </Button>
            </div>
          </Card.Footer>
        </Card>
      </div>
    );
  }

  return (
    <div className="animate-fade-up space-y-6 lg:space-y-8">
      {header}

      {/* ---------- Resource ---------- */}
      <Card>
        <Card.Header
          icon={TypeIcon}
          title="Selected Resource"
          subtitle={resource.resource}
          action={<StatusBadge status={resourceStatusToUi(resource.status)} size="sm" />}
        />
        <Card.Body className="space-y-5">
          {!rescueId && resources.length > 1 && (
            <Select
              label="Resource"
              value={selectedId}
              onChange={(event) => setSelectedId(event.target.value)}
              options={resources.map((item) => ({
                value: item.id,
                label: `${item.title} — ${fmt(item.quantity)} ${item.unit}`,
              }))}
            />
          )}
          <dl className="grid grid-cols-2 gap-x-6 gap-y-4 lg:grid-cols-4">
            <Field label="Resource">{resource.resource}</Field>
            <Field label="Resource type">
              <Badge tone={resource.resourceType} icon={TypeIcon} size="sm">
                {typeMeta?.label ?? resource.resourceType}
              </Badge>
            </Field>
            <Field label="Quantity">
              {fmt(resource.quantity)} {resource.unit}
            </Field>
            <Field label="Provider">{resource.provider}</Field>
            <Field label="Location">{resource.location}</Field>
            <Field label="Urgency">
              <Badge tone={URGENCY_TONE[resource.urgency] ?? 'neutral'} dot size="sm">
                {urgencyMeta?.label ?? resource.urgency}
              </Badge>
            </Field>
            <Field label="Rescue window">{formatMinutes(resource.rescueWindowMinutes)}</Field>
            <Field label="Pickup deadline">
              {resource.deadline ? new Date(resource.deadline).toLocaleString() : 'Not set'}
            </Field>
          </dl>
        </Card.Body>
      </Card>

      {/* ---------- Matching ---------- */}
      <Card>
        <Card.Header
          icon={GitBranch}
          title="Matching"
          subtitle="Each registered recipient is checked for type, eligibility, availability, capacity and distance."
          action={
            <Badge tone={results ? 'success' : 'neutral'} size="sm">
              {results ? `Run ${new Date(results.generated_at).toLocaleTimeString()}` : 'Not run yet'}
            </Badge>
          }
        />
        <Card.Body className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant="primary"
              icon={results ? RotateCw : GitBranch}
              loading={running}
              onClick={handleRun}
              disabled={!selectedId}
            >
              {results ? 'Re-run matching' : 'Start matching'}
            </Button>
            {running && <span className="text-xs text-muted">Checking recipients…</span>}
          </div>
          {runError && <p className="text-xs text-critical">{runError.message}</p>}

          {results && (
            <div className="grid grid-cols-3 gap-3">
              <Stat label="Considered" value={results.total_candidates_considered} />
              <Stat label="Eligible" value={results.eligible_count} />
              <Stat label="Not eligible" value={results.rejected_count} />
            </div>
          )}
        </Card.Body>
      </Card>

      {/* ---------- Results ---------- */}
      {results && eligible.length === 0 && (
        <Card>
          <EmptyState
            icon={ListChecks}
            title="No eligible recipients"
            description={
              results.total_candidates_considered === 0
                ? 'No recipient organizations are registered yet. Recipients must sign up and be verified by an admin before they can receive resources.'
                : 'Every recipient was ruled out — see the reasons below. Recipients must be platform-verified (and medical-verified for medical resources), currently available, and have capacity.'
            }
          />
        </Card>
      )}

      {results && eligible.length > 0 && (
        <Card>
          <Card.Header
            icon={ListChecks}
            title="Proposed allocation"
            subtitle="Best matches first. Adjust quantities or untick a recipient before confirming."
          />
          <Card.Body className="space-y-3">
            {eligible.map((candidate) => {
              const line = plan[candidate.match_id] ?? { include: false, quantity: '' };
              const capacity = candidate.recipient.capacity;
              return (
                <div
                  key={candidate.match_id}
                  className={`rounded-control border p-3.5 transition-colors ${
                    line.include ? 'border-brand-500/30 bg-brand-500/5' : 'border-line bg-surface-2'
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <label className="flex min-w-0 cursor-pointer items-start gap-3">
                      <input
                        type="checkbox"
                        className="mt-1 h-4 w-4 accent-brand-500"
                        checked={line.include}
                        onChange={(event) => updatePlan(candidate.match_id, { include: event.target.checked })}
                      />
                      <span className="min-w-0">
                        <span className="block text-sm font-semibold text-content">
                          {candidate.recipient.organization_name}
                        </span>
                        <span className="mt-0.5 block text-xs text-muted">
                          {candidate.recipient.location_address}
                          {candidate.distance_km != null && ` · ${candidate.distance_km.toFixed(1)} km away`}
                          {capacity != null && ` · capacity ${fmt(capacity)}`}
                        </span>
                      </span>
                    </label>
                    <div className="flex items-center gap-3">
                      <Badge tone={candidate.score >= 0.7 ? 'success' : candidate.score >= 0.4 ? 'active' : 'neutral'} size="sm">
                        {Math.round(candidate.score * 100)}% match
                      </Badge>
                      <div className="w-32">
                        <input
                          type="number"
                          min="0"
                          step="any"
                          aria-label={`Quantity for ${candidate.recipient.organization_name}`}
                          disabled={!line.include}
                          value={line.quantity}
                          onChange={(event) => updatePlan(candidate.match_id, { quantity: event.target.value })}
                          className="h-9 w-full rounded-control border border-line bg-surface-2 px-3 text-right text-sm text-content focus:border-brand-500 focus:outline-none disabled:opacity-50"
                        />
                      </div>
                      <span className="w-14 text-xs text-muted">{resource.unit}</span>
                    </div>
                  </div>
                  <p className="mt-2 pl-7 text-xs text-muted">{candidate.explanation}</p>
                  {candidate.passed_reasons.length > 0 && (
                    <ul className="mt-2 flex flex-wrap gap-1.5 pl-7">
                      {candidate.passed_reasons.map((reason) => (
                        <li key={reason}>
                          <Badge tone="neutral" size="sm">
                            {reason}
                          </Badge>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              );
            })}
          </Card.Body>
          <Card.Footer>
            <div className="w-full space-y-3">
              <div className="grid grid-cols-3 gap-3">
                <Stat label="Available" value={`${fmt(requested)} ${resource.unit}`} />
                <Stat label="Allocated" value={`${fmt(total)} ${resource.unit}`} />
                <Stat label="Unallocated" value={`${fmt(Math.max(unallocated, 0))} ${resource.unit}`} />
              </div>
              {problems.length > 0 && (
                <ul className="space-y-1">
                  {problems.map((problem) => (
                    <li key={problem} className="text-xs text-urgent">
                      {problem}
                    </li>
                  ))}
                </ul>
              )}
              {planValid && unallocated > 1e-6 && (
                <p className="text-xs text-muted">
                  {fmt(unallocated)} {resource.unit} will stay unallocated — you can run matching again later to place
                  the rest.
                </p>
              )}
              {confirmError && (
                <p className="text-xs text-critical">
                  {confirmError.stage === 'operation'
                    ? `The allocations were saved, but the operation couldn't be created: ${confirmError.message}`
                    : confirmError.created?.length > 0
                      ? `${confirmError.created.length} allocation(s) were saved before an error stopped the rest: ${confirmError.message}`
                      : confirmError.message}
                </p>
              )}
              <div className="flex justify-end">
                <Button variant="primary" loading={confirming} disabled={!planValid} onClick={handleConfirm}>
                  Confirm rescue plan
                </Button>
              </div>
            </div>
          </Card.Footer>
        </Card>
      )}

      {results && rejected.length > 0 && (
        <Card>
          <Card.Header title="Not eligible" subtitle={`${rejected.length} recipient${rejected.length === 1 ? '' : 's'} ruled out`} />
          <Card.Body className="space-y-2">
            {rejected.map((candidate) => (
              <div key={candidate.match_id} className="rounded-control border border-line bg-surface-2 p-3">
                <p className="text-sm font-medium text-content">{candidate.recipient.organization_name}</p>
                <ul className="mt-1 list-disc space-y-0.5 pl-5 text-xs text-muted">
                  {candidate.rejection_reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </div>
            ))}
          </Card.Body>
        </Card>
      )}
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div className="min-w-0">
      <dt className="text-[10px] font-medium uppercase tracking-wide text-faint">{label}</dt>
      <dd className="mt-1 break-words text-sm font-medium text-content">{children}</dd>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="rounded-control border border-line bg-surface-2 px-3.5 py-2.5">
      <p className="text-[10px] font-medium uppercase tracking-wide text-faint">{label}</p>
      <p className="mt-1 text-sm font-semibold text-content">{value}</p>
    </div>
  );
}
