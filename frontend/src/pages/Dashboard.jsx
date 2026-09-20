import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Package,
  Radio,
  AlertTriangle,
  CheckCircle2,
  PlusCircle,
  GitBranch,
  Map,
  ClipboardList,
  History,
  ArrowUpRight,
} from 'lucide-react';

import { Card, Button, LoadingState, EmptyState } from '@/components/ui';
import StatCard from '@/components/StatCard';
import OperationCard from '@/components/OperationCard';
import AtRiskCard from '@/components/AtRiskCard';
import ActivityTimeline from '@/components/ActivityTimeline';
import MapPreview from '@/components/MapPreview';
import MapLegend from '@/components/MapLegend';
import ReallocationWarning from '@/components/ReallocationWarning';
import useReallocationDemo from '@/hooks/useReallocationDemo';
import { PATHS } from '@/routes/paths';
import { getDashboardOverview } from '@/services/dashboardService';
import { getActiveOperations } from '@/services/operationsService';
import { getAtRiskResources } from '@/services/resourcesService';
import { getRecentActivity } from '@/services/activityService';
import { getNetworkLocations } from '@/services/networkService';
import {
  applyDemoToActivity,
  applyDemoToAtRiskResources,
  applyDemoToDashboardStats,
  applyDemoToOperations,
  getReallocationView,
} from '@/services/reallocationDemoService';

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
 * operationsService, resourcesService, activityService, networkService) —
 * same shape a real endpoint will return later, loaded independently so one
 * slow section never blocks the rest of the page. Charts and the full
 * operations table are separate, later steps; the map here is a compact,
 * read-only preview, not the full interactive Rescue Network page.
 */
export default function Dashboard() {
  const [baseStats, setStats] = useState(null);
  const [baseOperations, setOperations] = useState(null);
  const [baseAtRisk, setAtRiskResources] = useState(null);
  const [baseActivity, setActivity] = useState(null);
  const [networkLocations, setNetworkLocations] = useState(null);

  // The RS-1024 recipient-unavailable demo (started on the Operations page)
  // is layered over the fetched mock data, so this page shows the same
  // Reallocating status, at-risk count and activity as every other page.
  const demo = useReallocationDemo();
  const reallocation = useMemo(() => getReallocationView(demo), [demo]);
  const stats = useMemo(() => applyDemoToDashboardStats(baseStats, demo), [baseStats, demo]);
  const operations = useMemo(
    () => applyDemoToOperations(baseOperations, demo),
    [baseOperations, demo],
  );
  const atRiskResources = useMemo(
    () => applyDemoToAtRiskResources(baseAtRisk, demo),
    [baseAtRisk, demo],
  );
  const activity = useMemo(() => applyDemoToActivity(baseActivity, demo), [baseActivity, demo]);

  useEffect(() => {
    let active = true;

    getDashboardOverview().then((data) => active && setStats(data));
    getActiveOperations().then((data) => active && setOperations(data));
    getAtRiskResources().then((data) => active && setAtRiskResources(data));
    getRecentActivity().then((data) => active && setActivity(data));
    getNetworkLocations().then((data) => active && setNetworkLocations(data));

    return () => {
      active = false;
    };
  }, []);

  const loading = !stats;

  return (
    <div className="animate-fade-up space-y-6 lg:space-y-8">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-content sm:text-2xl">
          Rescue Operations Overview
        </h1>
        <p className="mt-1.5 text-sm text-muted">
          Monitor resources, active rescues, and at-risk operations.
        </p>
      </div>

      {reallocation.unavailable && (
        <ReallocationWarning variant="compact" warning={reallocation.warning}>
          <Link
            to={PATHS.LIVE_OPERATIONS}
            className="text-xs font-medium text-urgent underline underline-offset-2 hover:text-content"
          >
            View {reallocation.operationId} in Operations
          </Link>
        </ReallocationWarning>
      )}

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
        <Card.Header title="Quick Actions" subtitle="Jump straight into the most common tasks." />
        <Card.Body>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {QUICK_ACTIONS.map(({ label, to, icon: Icon }) => (
              <Link key={label} to={to} className="group block">
                <Card
                  interactive
                  className="flex h-full flex-col items-center justify-center gap-2 px-3 py-5 text-center"
                >
                  <span className="flex h-10 w-10 items-center justify-center rounded-control bg-veil-500/10 text-veil-400 transition-colors duration-150 group-hover:bg-veil-500/20">
                    <Icon size={18} strokeWidth={1.75} />
                  </span>
                  <span className="text-xs font-medium text-content">{label}</span>
                </Card>
              </Link>
            ))}
          </div>
        </Card.Body>
      </Card>

      {/* ---------- Network Map Preview ---------- */}
      <Card>
        <Card.Header
          icon={Map}
          title="Network Map Preview"
          subtitle="Providers, recipients, partners and hubs across the service area."
          action={
            <Button
              as={Link}
              to={PATHS.RESCUE_NETWORK}
              variant="ghost"
              size="sm"
              iconRight={ArrowUpRight}
              className="max-sm:hidden"
            >
              Open full map
            </Button>
          }
        />
        <Card.Body className="space-y-4">
          {networkLocations ? (
            <>
              <MapPreview locations={networkLocations} />
              <MapLegend />
            </>
          ) : (
            <LoadingState label="Loading network map…" />
          )}
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

        {operations === null ? (
          <LoadingState label="Loading active operations…" />
        ) : operations.length === 0 ? (
          <Card>
            <EmptyState
              icon={ClipboardList}
              title="No active operations"
              description="New rescues will appear here as soon as a resource is logged."
            />
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {operations.map((operation) => (
              <OperationCard key={operation.id} operation={operation} />
            ))}
          </div>
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

        {atRiskResources === null ? (
          <LoadingState label="Loading at-risk resources…" />
        ) : atRiskResources.length === 0 ? (
          <Card>
            <EmptyState
              icon={AlertTriangle}
              title="Nothing at risk right now"
              description="Resources nearing their rescue deadline will show up here."
            />
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {atRiskResources.map((resource) => (
              <AtRiskCard key={resource.id} resource={resource} />
            ))}
          </div>
        )}
      </section>

      {/* ---------- Recent Rescue Activity ---------- */}
      <Card>
        <Card.Header
          title="Recent Rescue Activity"
          subtitle="Latest lifecycle events across active rescues."
        />
        <Card.Body>
          {activity === null ? (
            <LoadingState label="Loading recent activity…" />
          ) : activity.length === 0 ? (
            <EmptyState
              icon={History}
              title="No recent activity"
              description="Lifecycle events — created, analyzed, matched, assigned, completed — will show up here."
            />
          ) : (
            <ActivityTimeline items={activity} />
          )}
        </Card.Body>
      </Card>
    </div>
  );
}
