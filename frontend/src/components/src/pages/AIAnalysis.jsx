import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  Sparkles,
  CheckCircle2,
  Loader2,
  Circle,
  Package,
  Clock,
  ArrowLeft,
  ArrowRight,
  FlaskConical,
  BrainCircuit,
  GitBranch,
  Tag,
  Hash,
  ListChecks,
} from 'lucide-react';

import { Card, Button, Badge, EmptyState } from '@/components/ui';
import { RESOURCE_ICONS } from '@/utils/icons';
import { URGENCY_META } from '@/utils/theme';
import { ANALYSIS_STEPS, STEP_DURATION_MS, computeMockAnalysis } from '@/utils/mockAnalysis';
import { getMockResource } from '@/services/rescueService';
import { PATHS, toPath } from '@/routes/paths';

/** Urgency → Badge tone. Matches the colour weight used elsewhere (AtRiskCard). */
const URGENCY_TONE = {
  critical: 'critical',
  high: 'urgent',
  medium: 'active',
  low: 'neutral',
};

/**
 * AIAnalysis — mock AI analysis stage shown right after Create Rescue
 * submission.
 *
 * Frontend only: no Gemini call, no backend. The resource was already saved
 * to localStorage by services/rescueService (createRescue); this page reads
 * it back, runs a short simulated step-by-step "analysis" sequence purely
 * client-side, then derives a deterministic mock result from the resource's
 * own data (see utils/mockAnalysis). Clearly labelled as a demo throughout.
 */
export default function AIAnalysis() {
  const { rescueId } = useParams();
  const navigate = useNavigate();

  const resource = useMemo(() => getMockResource(rescueId), [rescueId]);
  const analysis = useMemo(() => (resource ? computeMockAnalysis(resource) : null), [resource]);

  const [stepIndex, setStepIndex] = useState(-1); // -1 = not started
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!resource) return undefined;

    const timers = [];
    ANALYSIS_STEPS.forEach((_, index) => {
      timers.push(
        setTimeout(() => setStepIndex(index), STEP_DURATION_MS * index + 150),
      );
    });
    timers.push(
      setTimeout(
        () => setDone(true),
        STEP_DURATION_MS * ANALYSIS_STEPS.length + 350,
      ),
    );

    return () => timers.forEach(clearTimeout);
  }, [resource]);

  if (!resource) {
    return (
      <div className="animate-fade-up mx-auto max-w-lg">
        <Card>
          <EmptyState
            icon={Package}
            title="Resource not found"
            description="This mock resource isn't in local storage — it may have been cleared, or this link is stale. Create a new rescue to run the analysis again."
            action={
              <Button as={Link} to={PATHS.CREATE_RESCUE} variant="primary" icon={ArrowLeft}>
                Back to Create Rescue
              </Button>
            }
          />
        </Card>
      </div>
    );
  }

  const TypeIcon = RESOURCE_ICONS[resource.resourceType] ?? Package;
  const urgencyMeta = analysis ? URGENCY_META[analysis.urgency] : null;

  return (
    <div className="animate-fade-up mx-auto max-w-2xl space-y-6">
      <div>
        <Link
          to={PATHS.DASHBOARD}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted transition-colors hover:text-content"
        >
          <ArrowLeft size={13} strokeWidth={1.75} />
          Back to dashboard
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-2.5">
          <h1 className="text-xl font-bold tracking-tight text-content sm:text-2xl">
            {done ? 'Analysis Complete' : 'Analyzing Resource…'}
          </h1>
          <Badge tone="predicted" icon={FlaskConical} size="sm">
            DEMO / MOCK AI ANALYSIS
          </Badge>
        </div>
        <p className="mt-1.5 text-sm text-muted">
          {resource.id} &middot; simulated locally, no AI or backend call is made.
        </p>
      </div>

      {/* ---------- Step sequence ---------- */}
      <Card>
        <Card.Header
          icon={Sparkles}
          title="Analysis steps"
          subtitle={done ? 'All checks completed.' : 'Running a short simulated sequence…'}
        />
        <Card.Body>
          <ol className="space-y-3">
            {ANALYSIS_STEPS.map((step, index) => {
              const state = index <= stepIndex ? 'complete' : index === stepIndex + 1 ? 'active' : 'pending';
              return (
                <li key={step.key} className="flex items-center gap-3">
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
                    {state === 'active' && (
                      <Loader2 size={13} strokeWidth={2.25} className="animate-spin" />
                    )}
                    {state === 'pending' && <Circle size={9} strokeWidth={2} fill="currentColor" />}
                  </span>
                  <span
                    className={
                      state === 'pending'
                        ? 'text-sm text-faint'
                        : 'text-sm font-medium text-content'
                    }
                  >
                    {step.label}
                  </span>
                </li>
              );
            })}
          </ol>

          {/* Progress bar */}
          <div className="mt-5 h-1.5 w-full overflow-hidden rounded-full bg-surface-3">
            <div
              className="h-full rounded-full bg-brand-500 transition-all duration-300 ease-soft"
              style={{
                width: `${Math.min(100, ((stepIndex + 1) / ANALYSIS_STEPS.length) * 100)}%`,
              }}
            />
          </div>
        </Card.Body>
      </Card>

      {/* ---------- Final AI Analysis Summary ---------- */}
      {done && analysis && (
        <Card className="animate-fade-up">
          <Card.Header
            icon={TypeIcon}
            title="AI Analysis Summary"
            subtitle={`${analysis.title} · ${analysis.quantityLabel}`}
            action={
              <Badge tone="predicted" icon={FlaskConical} size="sm">
                DEMO / MOCK AI ANALYSIS
              </Badge>
            }
          />
          <Card.Body className="space-y-6">
            {/* ---- Section 1: what the (mock) AI read off the submission ---- */}
            <div>
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-predicted/10 text-predicted">
                  <BrainCircuit size={13} strokeWidth={2} />
                </span>
                <h4 className="text-xs font-semibold uppercase tracking-wide text-content">
                  AI-understood information
                </h4>
                <Badge tone="predicted" size="sm">
                  From your submission
                </Badge>
              </div>
              <p className="mt-1 pl-8 text-xs text-faint">
                Read directly from what you entered — the mock analysis identified and labelled
                it, nothing here was decided or planned.
              </p>

              <div className="mt-3 space-y-1 divide-y divide-line rounded-control border border-line bg-surface-2 px-3.5">
                <div className="flex items-center justify-between py-2.5">
                  <span className="flex items-center gap-1.5 text-xs text-faint">
                    <TypeIcon size={12} strokeWidth={1.75} />
                    Resource type
                  </span>
                  <Badge tone={resource.resourceType} size="sm">
                    {analysis.resourceTypeLabel}
                  </Badge>
                </div>
                <div className="flex items-center justify-between py-2.5">
                  <span className="flex items-center gap-1.5 text-xs text-faint">
                    <Tag size={12} strokeWidth={1.75} />
                    Category
                  </span>
                  <span className="text-xs font-medium text-content">{analysis.categoryLabel}</span>
                </div>
                <div className="flex items-center justify-between py-2.5">
                  <span className="flex items-center gap-1.5 text-xs text-faint">
                    <Hash size={12} strokeWidth={1.75} />
                    Quantity
                  </span>
                  <span className="text-xs font-medium text-content">{analysis.quantityLabel}</span>
                </div>

                {analysis.attributes.length > 0 && (
                  <div className="py-2.5">
                    <span className="mb-2 flex items-center gap-1.5 text-xs text-faint">
                      <ListChecks size={12} strokeWidth={1.75} />
                      Important attributes
                    </span>
                    <dl className="space-y-1.5 pl-[18px]">
                      {analysis.attributes.map((attr) => (
                        <div key={attr.label} className="flex items-start justify-between gap-3 text-xs">
                          <dt className="shrink-0 text-faint">{attr.label}</dt>
                          <dd className="text-right font-medium text-content">{attr.value}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                )}
              </div>
            </div>

            {/* ---- Section 2: what the (mock) system decided for allocation ---- */}
            <div>
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-500/10 text-brand-400">
                  <GitBranch size={13} strokeWidth={2} />
                </span>
                <h4 className="text-xs font-semibold uppercase tracking-wide text-content">
                  System allocation decisions
                </h4>
                <Badge tone="brand" size="sm">
                  Computed
                </Badge>
              </div>
              <p className="mt-1 pl-8 text-xs text-faint">
                Derived by the mock matching logic to plan the rescue — these drive what happens
                next, rather than describing what you submitted.
              </p>

              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="rounded-control border border-brand-500/20 bg-brand-500/5 p-3.5">
                  <p className="text-[11px] uppercase tracking-wide text-faint">Urgency</p>
                  <div className="mt-1.5">
                    <Badge tone={URGENCY_TONE[analysis.urgency] ?? 'neutral'} dot>
                      {urgencyMeta?.label?.toUpperCase()} URGENCY
                    </Badge>
                  </div>
                </div>

                <div className="rounded-control border border-brand-500/20 bg-brand-500/5 p-3.5">
                  <p className="text-[11px] uppercase tracking-wide text-faint">Rescue window</p>
                  <p className="mt-1.5 flex items-center gap-1.5 text-sm font-semibold text-content">
                    <Clock size={14} strokeWidth={1.75} className="text-brand-400" />
                    {analysis.rescueWindowLabel}
                  </p>
                </div>
              </div>
            </div>

            <p className="text-xs leading-relaxed text-faint">
              This summary is generated locally from the details you entered — not by a real AI
              model or backend service. Matching uses this mock result in the next step.
            </p>
          </Card.Body>
          <Card.Footer>
            <div className="flex w-full items-center justify-between gap-2">
              <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate(-1)}>
                Back
              </Button>
              <Button
                variant="primary"
                iconRight={ArrowRight}
                onClick={() => navigate(toPath(PATHS.MATCHING_RESULTS, { rescueId: resource.id }))}
              >
                Continue to Matching
              </Button>
            </div>
          </Card.Footer>
        </Card>
      )}
    </div>
  );
}
