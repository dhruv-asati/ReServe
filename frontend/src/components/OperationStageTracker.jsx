import { CheckCircle2, XCircle } from 'lucide-react';

import { ACTIVITY_STAGE_ICONS } from '@/utils/icons';
import { cn } from '@/utils/cn';

/**
 * OperationStageTracker — vertical stepper for a rescue's full lifecycle:
 * Created → AI Analyzed → Matched → Partner Assigned → Pickup Started →
 * In Transit → Delivered.
 *
 * Unlike ActivityTimeline (a reverse-chronological event feed of things
 * that already happened), this renders every stage of the lifecycle up
 * front — completed, the one current stage, and the ones still upcoming —
 * so an operator can see at a glance how far along an operation is and
 * what's left. Built on the same dot-and-line visual language as
 * ActivityTimeline so it reads as part of the same design system.
 *
 * A stage may also be `state: 'ended'` — the terminal stage of an operation
 * that was cancelled or expired. It renders in the critical colour with an X
 * icon, and such an operation lists no upcoming stages after it.
 *
 * Frontend only: `stages` is demo data (see data/operationDetail.js).
 * Every timestamp shown is a hardcoded, illustrative value — never a live
 * or auto-refreshing clock — and upcoming stages intentionally carry no
 * timestamp at all.
 */
export default function OperationStageTracker({ stages = [] }) {
  return (
    <ol className="space-y-0">
      {stages.map((stage, index) => {
        const isLast = index === stages.length - 1;
        const isCompleted = stage.state === 'completed';
        const isCurrent = stage.state === 'current';
        const isEnded = stage.state === 'ended';
        const Icon = isEnded
          ? XCircle
          : isCompleted
            ? CheckCircle2
            : ACTIVITY_STAGE_ICONS[stage.key];

        return (
          <li key={stage.key} className="relative flex gap-3 pb-6 last:pb-0">
            {!isLast && (
              <span
                className={cn(
                  'absolute left-[15px] top-8 h-[calc(100%-1.75rem)] w-px',
                  isCompleted ? 'bg-veil-500/50' : 'bg-line',
                )}
              />
            )}

            <span
              className={cn(
                'flex h-8 w-8 shrink-0 items-center justify-center rounded-full ring-1 ring-inset',
                isCompleted && 'bg-veil-500/15 text-veil-400 ring-veil-500/30',
                isCurrent && 'animate-pulse-soft bg-active/15 text-active ring-active/40',
                isEnded && 'bg-critical/15 text-critical ring-critical/40',
                stage.state === 'upcoming' && 'bg-surface-3 text-faint ring-line',
              )}
            >
              {Icon && <Icon size={14} strokeWidth={1.75} />}
            </span>

            <div className="min-w-0 flex-1 pt-1">
              <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                  <p
                    className={cn(
                      'truncate text-xs font-semibold',
                      stage.state === 'upcoming' ? 'text-faint' : 'text-content',
                    )}
                  >
                    {stage.label}
                  </p>
                  {isCurrent && (
                    <span className="inline-flex h-5 items-center whitespace-nowrap rounded-full bg-active/10 px-1.5 text-[10px] font-medium tracking-tight text-active ring-1 ring-inset ring-active/25">
                      Current stage
                    </span>
                  )}
                </div>
                <span className="shrink-0 text-[11px] text-faint">
                  {stage.state === 'upcoming' ? 'Pending' : stage.timestamp}
                </span>
              </div>
              {stage.description && (
                <p
                  className={cn(
                    'mt-0.5 text-xs',
                    stage.state === 'upcoming' ? 'text-faint' : 'text-muted',
                  )}
                >
                  {stage.description}
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
