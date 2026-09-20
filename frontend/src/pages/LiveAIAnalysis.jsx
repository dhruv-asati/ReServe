import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  BrainCircuit,
  Clock,
  ListChecks,
  MapPin,
  Package,
  RotateCw,
  ShieldAlert,
  Sparkles,
  Tag,
} from 'lucide-react';

import { Badge, Button, Card, EmptyState, LoadingState } from '@/components/ui';
import { RESOURCE_ICONS } from '@/utils/icons';
import { RESOURCE_META, URGENCY_META } from '@/utils/theme';
import { analyzeRescue, getRescue } from '@/services/rescueService';
import { formatMinutes, lower, toDisplayResource } from '@/services/resourceAdapter';
import { PATHS, toPath } from '@/routes/paths';

/** Urgency → Badge tone. Same weighting the rest of the app uses. */
const URGENCY_TONE = { critical: 'critical', high: 'urgent', medium: 'active', low: 'neutral' };

/**
 * AIAnalysis for live data (VITE_USE_MOCKS=false): loads the real resource,
 * runs the backend's Gemini analysis (POST /api/resources/{id}/analyze) if it
 * hasn't been analyzed yet, and shows what came back.
 *
 * Analysis only describes the resource — it never matches, allocates or
 * changes status — so if it fails the person can still continue to matching.
 */
export default function LiveAIAnalysis() {
  const { rescueId } = useParams();
  const navigate = useNavigate();

  const [resource, setResource] = useState(null); // backend ResourceOut
  const [phase, setPhase] = useState('loading'); // loading | analyzing | done | not_found | error
  const [error, setError] = useState(null);
  const [attempt, setAttempt] = useState(0);
  const forceRef = useRef(false); // true when the person asked to re-run

  useEffect(() => {
    let active = true;
    setPhase('loading');
    setError(null);

    (async () => {
      let loaded = null;
      try {
        loaded = await getRescue(rescueId);
        if (!active) return;
        setResource(loaded);

        if (loaded.ai_analysis && !forceRef.current) {
          setPhase('done');
          return;
        }

        forceRef.current = false;
        setPhase('analyzing');
        const analyzed = await analyzeRescue(rescueId);
        if (!active) return;
        setResource(analyzed);
        setPhase('done');
      } catch (err) {
        if (!active) return;
        setError(err);
        setPhase(!loaded && err?.status === 404 ? 'not_found' : 'error');
      }
    })();

    return () => {
      active = false;
    };
  }, [rescueId, attempt]);

  const rerun = useCallback(() => {
    forceRef.current = true;
    setAttempt((n) => n + 1);
  }, []);
  // A plain reload — used when the resource itself failed to load, so nothing is force re-analyzed.
  const reload = useCallback(() => setAttempt((n) => n + 1), []);

  const goToMatching = () => navigate(toPath(PATHS.MATCHING_RESULTS, { rescueId }));

  if (phase === 'not_found') {
    return (
      <div className="animate-fade-up mx-auto max-w-lg">
        <Card>
          <EmptyState
            icon={Package}
            title="Resource not found"
            description="This resource doesn't exist, or you don't have access to it."
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

  const display = resource ? toDisplayResource(resource) : null;
  const TypeIcon = (display && RESOURCE_ICONS[display.resourceType]) || Package;
  const typeMeta = display ? RESOURCE_META[display.resourceType] : null;
  const result = resource?.ai_analysis ?? null;
  const analysis = result?.analysis ?? null;
  const done = phase === 'done' && analysis;

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
        <h1 className="mt-2 text-xl font-bold tracking-tight text-content sm:text-2xl">
          {done ? 'Analysis Complete' : phase === 'error' ? 'Analysis Unavailable' : 'Analyzing Resource…'}
        </h1>
        <p className="mt-1.5 text-sm text-muted">
          {display ? `${display.resource} · ${display.quantity} ${display.unit}` : 'Loading resource…'}
        </p>
      </div>

      {(phase === 'loading' || phase === 'analyzing') && (
        <Card>
          <Card.Body>
            <LoadingState
              label={phase === 'loading' ? 'Loading resource…' : 'Gemini is reading this resource — this can take up to 30 seconds.'}
            />
          </Card.Body>
        </Card>
      )}

      {phase === 'error' && (
        <Card>
          <Card.Body className="space-y-4">
            <div className="flex items-start gap-3">
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-critical/10 text-critical">
                <AlertTriangle size={16} strokeWidth={1.75} />
              </span>
              <div>
                <h3 className="text-sm font-semibold text-content">
                  {resource ? "The AI analysis couldn't be completed" : "This resource couldn't be loaded"}
                </h3>
                <p className="mt-1 text-xs text-muted">{error?.message ?? 'Something went wrong. Please try again.'}</p>
                {resource && (
                  <p className="mt-2 text-xs text-faint">
                    Your rescue was saved. Analysis is optional — you can retry it, or continue to matching without it.
                  </p>
                )}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" icon={RotateCw} onClick={resource ? rerun : reload}>
                Try again
              </Button>
              {resource && (
                <Button variant="primary" iconRight={ArrowRight} onClick={goToMatching}>
                  Continue to Matching
                </Button>
              )}
            </div>
          </Card.Body>
        </Card>
      )}

      {done && (
        <Card className="animate-fade-up">
          <Card.Header
            icon={TypeIcon}
            title="AI Analysis Summary"
            subtitle={`${analysis.resource_category} · ${analysis.resource_subtype}`}
            action={
              <Badge tone="predicted" icon={Sparkles} size="sm">
                {Math.round(analysis.confidence_score * 100)}% confidence
              </Badge>
            }
          />
          <Card.Body className="space-y-6">
            {/* ---- What was submitted, cross-checked by the AI ---- */}
            <div>
              <SectionTitle icon={BrainCircuit} tone="predicted" title="What the AI understood" />
              <div className="mt-3 space-y-1 divide-y divide-line rounded-control border border-line bg-surface-2 px-3.5">
                <Row icon={TypeIcon} label="Resource type">
                  <Badge tone={display.resourceType} size="sm">
                    {typeMeta?.label ?? display.resourceType}
                  </Badge>
                </Row>
                <Row icon={Tag} label="Classification">
                  {analysis.resource_category} — {analysis.resource_subtype}
                </Row>
                <Row icon={Package} label="Quantity posted">
                  {display.quantity} {display.unit}
                </Row>
                <Row icon={Package} label="Quantity read from text">
                  {analysis.extracted_quantity.value != null
                    ? `${analysis.extracted_quantity.value} ${analysis.extracted_quantity.unit ?? ''}`.trim()
                    : 'Not stated'}
                  {analysis.extracted_quantity.value != null && !analysis.extracted_quantity.matches_posted_quantity && (
                    <span className="ml-2 text-urgent">(differs from what was posted)</span>
                  )}
                </Row>
                <Row icon={MapPin} label="Pickup location">
                  {display.location}
                </Row>
                {analysis.important_attributes.length > 0 && (
                  <div className="py-2.5">
                    <span className="mb-2 flex items-center gap-1.5 text-xs text-faint">
                      <ListChecks size={12} strokeWidth={1.75} />
                      Important attributes
                    </span>
                    <div className="flex flex-wrap gap-1.5 pl-[18px]">
                      {analysis.important_attributes.map((attribute) => (
                        <Badge key={attribute} tone="neutral" size="sm">
                          {attribute}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                <Row icon={Package} label="Storage">
                  {analysis.storage_requirements}
                </Row>
                {analysis.eligibility_info && (
                  <Row icon={Tag} label="Eligibility">
                    {analysis.eligibility_info}
                  </Row>
                )}
              </div>
            </div>

            {/* ---- Urgency + rescue window ---- */}
            <div>
              <SectionTitle icon={Clock} tone="brand" title="Urgency and rescue window" />
              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="rounded-control border border-brand-500/20 bg-brand-500/5 p-3.5">
                  <p className="text-[11px] uppercase tracking-wide text-faint">AI urgency</p>
                  <div className="mt-1.5">
                    <Badge tone={URGENCY_TONE[lower(analysis.urgency_level)] ?? 'neutral'} dot>
                      {URGENCY_META[lower(analysis.urgency_level)]?.label?.toUpperCase() ?? analysis.urgency_level} URGENCY
                    </Badge>
                  </div>
                  <p className="mt-2 text-[11px] text-faint">
                    Resource is currently set to {URGENCY_META[display.urgency]?.label?.toLowerCase() ?? display.urgency}{' '}
                    urgency, from its deadline.
                  </p>
                </div>
                <div className="rounded-control border border-brand-500/20 bg-brand-500/5 p-3.5">
                  <p className="text-[11px] uppercase tracking-wide text-faint">Recommended pickup within</p>
                  <p className="mt-1.5 flex items-center gap-1.5 text-sm font-semibold text-content">
                    <Clock size={14} strokeWidth={1.75} className="text-brand-400" />
                    {analysis.rescue_window.recommended_pickup_within_hours != null
                      ? formatMinutes(Math.round(analysis.rescue_window.recommended_pickup_within_hours * 60))
                      : 'Not specified'}
                  </p>
                  <p className="mt-2 text-[11px] text-faint">{analysis.rescue_window.reasoning}</p>
                </div>
              </div>
            </div>

            {analysis.warnings.length > 0 && (
              <div>
                <SectionTitle icon={ShieldAlert} tone="urgent" title="Handling warnings" />
                <ul className="mt-3 space-y-1.5 rounded-control border border-urgent/25 bg-urgent/5 px-3.5 py-3">
                  {analysis.warnings.map((warning) => (
                    <li key={warning} className="flex items-start gap-2 text-xs text-content">
                      <AlertTriangle size={12} strokeWidth={2} className="mt-0.5 shrink-0 text-urgent" />
                      {warning}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <p className="text-xs leading-relaxed text-faint">
              Generated by {result.model} on {new Date(result.analyzed_at).toLocaleString()}. The analysis only
              describes this resource — it doesn&rsquo;t choose recipients or allocate anything; that happens in
              Smart Matching.
            </p>
          </Card.Body>
          <Card.Footer>
            <div className="flex w-full items-center justify-between gap-2">
              <Button variant="secondary" icon={RotateCw} onClick={rerun}>
                Re-run analysis
              </Button>
              <Button variant="primary" iconRight={ArrowRight} onClick={goToMatching}>
                Continue to Matching
              </Button>
            </div>
          </Card.Footer>
        </Card>
      )}
    </div>
  );
}

function SectionTitle({ icon: Icon, tone, title }) {
  const toneClass =
    tone === 'predicted'
      ? 'bg-predicted/10 text-predicted'
      : tone === 'urgent'
        ? 'bg-urgent/10 text-urgent'
        : 'bg-brand-500/10 text-brand-400';
  return (
    <div className="flex items-center gap-2">
      <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${toneClass}`}>
        <Icon size={13} strokeWidth={2} />
      </span>
      <h4 className="text-xs font-semibold uppercase tracking-wide text-content">{title}</h4>
    </div>
  );
}

function Row({ icon: Icon, label, children }) {
  return (
    <div className="flex items-start justify-between gap-3 py-2.5">
      <span className="flex shrink-0 items-center gap-1.5 text-xs text-faint">
        <Icon size={12} strokeWidth={1.75} />
        {label}
      </span>
      <span className="text-right text-xs font-medium text-content">{children}</span>
    </div>
  );
}
