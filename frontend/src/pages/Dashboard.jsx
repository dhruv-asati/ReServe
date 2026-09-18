import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Package,
  Radio,
  AlertTriangle,
  CheckCircle2,
  PlusCircle,
  GitBranch,
  Map,
} from 'lucide-react';

import { Card, LoadingState } from '@/components/ui';
import StatCard from '@/components/StatCard';
import OperationCard from '@/components/OperationCard';
import AtRiskCard from '@/components/AtRiskCard';
import ActivityTimeline from '@/components/ActivityTimeline';
import { PATHS } from '@/routes/paths';
import { getDashboardOverview } from '@/services/dashboardService';
import { getActiveOperations } from '@/services/operationsService';
import { getAtRiskResources } from '@/services/resourcesService';
import { getRecentActivity } from '@/services/activityService';

const QUICK_ACTIONS = [
  { label: 'Create Rescue', to: PATHS.CREATE_RESCUE, icon: PlusCircle },
  { label: 'Find Match', to: PATHS.MATCHING, icon: GitBranch },
  { label: 'View Operations', to: PATHS.LIVE_OPERATIONS, icon: Radio },
  { label: 'View Network', to: PATHS.RESCUE_NETWORK, icon: Map },
];

/**
 * Dashboard — operational overview.
 *
 * Every section fetches through its own mock service (dashboardService,
 * operationsService, resourcesService, activityService) — same shape a real
 * endpoint will return later, loaded independently so one slow section never
 * blocks the rest of the page. The map, charts, and the full operations
 * table are separate, later steps.
 */
export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [operations, setOperations] = useState(null);
  const [atRiskResources, setAtRiskResources] = useState(null);
  const [activity, setActivity] = useState(null);

  useEffect(() => {
    let active = true;

    getDashboardOverview().then((data) => active && setStats(data));
    getActiveOperations().then((data) => active && setOperations(data));
    getAtRiskResources().then((data) => active && setAtRiskResources(data));
    getRecentActivity().then((data) => active && setActivity(data));

    return () => {
      active = false;
    };
  }, []);

  const loading = !stats;

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-content sm:text-2xl">
          Rescue Operations Overview
        </h1>
        <p className="mt-1 text-sm text-muted">
          Monitor resources, active rescues, and at-risk operations.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Resources Rescued"
          icon={Package}
          tone="brand"
          loading={loading}
          value={stats?.resourcesRescued.value}
          unit={stats?.resourcesRescued.unit}
          delta={stats?.resourcesRescued.delta}
        />
        <StatCard
          label="Active Rescues"
          icon={Radio}
          tone="active"
          loading={loading}
          value={stats?.activeRescues.value}
          delta={stats?.activeRescues.delta}
        />
        <StatCard
          label="At-Risk Resources"
          icon={AlertTriangle}
          tone="urgent"
          loading={loading}
          value={stats?.atRiskResources.value}
          delta={stats?.atRiskResources.delta}
        />
        <StatCard
          label="Successful Allocations"
          icon={CheckCircle2}
          tone="success"
          loading={loading}
          value={stats?.successfulAllocations.value}
          delta={stats?.successfulAllocations.delta}
        />
      </div>

      <Card>
        <Card.Header
          title="Quick Actions"
          subtitle="Jump straight into the most common tasks."
        />
        <Card.Body>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {QUICK_ACTIONS.map(({ label, to, icon: Icon }) => (
              <Link key={label} to={to} className="block">
                <Card
                  interactive
                  className="flex h-full flex-col items-center justify-center gap-2 px-3 py-5 text-center"
                >
                  <span className="flex h-10 w-10 items-center justify-center rounded-control bg-brand-500/10 text-brand-400">
                    <Icon size={18} strokeWidth={1.75} />
                  </span>
                  <span className="text-xs font-medium text-content">{label}</span>
                </Card>
              </Link>
            ))}
          </div>
        </Card.Body>
      </Card>

      {/* ---------- Active Rescue Operations ---------- */}
      <section className="space-y-3">
        <div>
          <h2 className="text-sm font-semibold tracking-tight text-content sm:text-base">
            Active Rescue Operations
          </h2>
          <p className="mt-0.5 text-xs text-muted">
            Rescues currently being analyzed, matched, or in transit.
          </p>
        </div>

        {operations ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {operations.map((operation) => (
              <OperationCard key={operation.id} operation={operation} />
            ))}
          </div>
        ) : (
          <LoadingState label="Loading active operations…" />
        )}
      </section>

      {/* ---------- At-Risk Resources ---------- */}
      <section className="space-y-3">
        <div>
          <h2 className="text-sm font-semibold tracking-tight text-content sm:text-base">
            At-Risk Resources
          </h2>
          <p className="mt-0.5 text-xs text-muted">
            Resources approaching their rescue deadline, most urgent first.
          </p>
        </div>

        {atRiskResources ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {atRiskResources.map((resource) => (
              <AtRiskCard key={resource.id} resource={resource} />
            ))}
          </div>
        ) : (
          <LoadingState label="Loading at-risk resources…" />
        )}
      </section>

      {/* ---------- Recent Rescue Activity ---------- */}
      <Card>
        <Card.Header
          title="Recent Rescue Activity"
          subtitle="Latest lifecycle events across active rescues."
        />
        <Card.Body>
          {activity ? (
            <ActivityTimeline items={activity} />
          ) : (
            <LoadingState label="Loading recent activity…" />
          )}
        </Card.Body>
      </Card>
    </div>
  );
}
