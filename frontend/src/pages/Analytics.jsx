import { useEffect, useState } from 'react';
import {
  Package,
  CheckCircle2,
  Timer,
  Radio,
  Info,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';

import StatCard from '@/components/StatCard';
import ChartCard from '@/components/ChartCard';
import PredictiveSurplusCard from '@/components/PredictiveSurplusCard';
import { CHART_ACTIVE_DOT, CHART_AXIS, CHART_CURSOR, RESOURCE_META } from '@/utils/theme';
import {
  getAnalyticsSummary,
  getResourcesRescuedOverTime,
  getFoodVsMedical,
  getSuccessfulAllocations,
  getAvgMatchingTime,
  getSupplyVsDemand,
  getDeadlinePerformance,
  getOperationCompletion,
  getAtRiskVsCompleted,
  getSurplusPredictionHistory,
  getSurplusPrediction,
} from '@/services/analyticsService';

const SUCCESS_COLOR = '#22c55e';
const CRITICAL_COLOR = '#f4506a';
const BRAND_COLOR = '#14b98f';
const ACTIVE_COLOR = '#38bdf8';
const URGENT_COLOR = '#f59e0b';

/** Status → color for the operation-completion chart, matching STATUS_META's palette. */
const COMPLETION_COLORS = {
  completed: SUCCESS_COLOR,
  inProgress: ACTIVE_COLOR,
  cancelled: CRITICAL_COLOR,
};

/** Status → color for the deadline-performance chart. */
const DEADLINE_COLORS = {
  onTime: SUCCESS_COLOR,
  late: URGENT_COLOR,
};

const FOOD_MEDICAL_COLORS = {
  food: RESOURCE_META.food.color,
  medical: RESOURCE_META.medical.color,
};

/** Shared Recharts tooltip styling so every chart on the page matches the app's dark panels. */
const tooltipStyle = {
  contentStyle: {
    backgroundColor: '#161d27',
    border: '1px solid #232d3b',
    borderRadius: 8,
    fontSize: 12,
  },
  labelStyle: { color: '#e6edf5' },
  itemStyle: { color: '#94a3b8' },
  // Hover highlight: dark violet tint (bar charts). Line / area charts override with CHART_CURSOR.line.
  cursor: CHART_CURSOR.bar,
};

/**
 * Analytics — reporting overview built on mock data.
 *
 * Every figure on this page (summary cards and charts alike) is illustrative
 * placeholder data from src/data/analytics.js, not a verified or real-world
 * production metric — the page says so up top and on every chart. Each
 * section fetches through its own mock service, mirroring the pattern
 * already used on the Dashboard page, so wiring in a live reporting endpoint
 * later needs no layout changes here.
 */
export default function Analytics() {
  const [summary, setSummary] = useState(null);
  const [rescuedOverTime, setRescuedOverTime] = useState(null);
  const [foodVsMedical, setFoodVsMedical] = useState(null);
  const [allocations, setAllocations] = useState(null);
  const [matchingTime, setMatchingTime] = useState(null);
  const [supplyVsDemand, setSupplyVsDemand] = useState(null);
  const [deadlinePerformance, setDeadlinePerformance] = useState(null);
  const [operationCompletion, setOperationCompletion] = useState(null);
  const [atRiskVsCompleted, setAtRiskVsCompleted] = useState(null);
  const [surplusHistory, setSurplusHistory] = useState(null);
  const [surplusPrediction, setSurplusPrediction] = useState(null);

  useEffect(() => {
    let active = true;

    getAnalyticsSummary().then((data) => active && setSummary(data));
    getResourcesRescuedOverTime().then((data) => active && setRescuedOverTime(data));
    getFoodVsMedical().then((data) => active && setFoodVsMedical(data));
    getSuccessfulAllocations().then((data) => active && setAllocations(data));
    getAvgMatchingTime().then((data) => active && setMatchingTime(data));
    getSupplyVsDemand().then((data) => active && setSupplyVsDemand(data));
    getDeadlinePerformance().then((data) => active && setDeadlinePerformance(data));
    getOperationCompletion().then((data) => active && setOperationCompletion(data));
    getAtRiskVsCompleted().then((data) => active && setAtRiskVsCompleted(data));
    getSurplusPredictionHistory().then((data) => active && setSurplusHistory(data));
    getSurplusPrediction().then((data) => active && setSurplusPrediction(data));

    return () => {
      active = false;
    };
  }, []);

  const loadingSummary = !summary;

  // Derived from the chart data itself, not a separately hardcoded number,
  // so the headline rate can never drift out of sync with the donut.
  const onTimeRate = deadlinePerformance
    ? Math.round(
        (deadlinePerformance.find((d) => d.key === 'onTime')?.value /
          deadlinePerformance.reduce((sum, d) => sum + d.value, 0)) *
          100,
      )
    : null;

  return (
    <div className="animate-fade-up space-y-6 lg:space-y-8">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-content sm:text-2xl">Analytics</h1>
        <p className="mt-1.5 text-sm text-muted">
          Reporting overview across resources, allocations, and matching performance.
        </p>
      </div>

      <div className="flex items-start gap-2.5 rounded-control border border-line bg-surface-2/60 px-4 py-3">
        <Info size={16} strokeWidth={1.75} className="mt-0.5 shrink-0 text-muted" />
        <p className="text-xs leading-relaxed text-muted">
          The figures and charts on this page use{' '}
          <span className="font-medium text-content">illustrative mock data</span> to preview the
          Analytics layout. They are not verified or real-world production statistics and should
          not be cited as measured impact.
        </p>
      </div>

      {/* ---------- Summary Cards ---------- */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Resources Rescued"
          icon={Package}
          tone="brand"
          loading={loadingSummary}
          value={summary?.resourcesRescued.value}
          unit={summary?.resourcesRescued.unit}
          delta={summary?.resourcesRescued.delta}
        />
        <StatCard
          label="Successful Allocations"
          icon={CheckCircle2}
          tone="success"
          loading={loadingSummary}
          value={summary?.successfulAllocations.value}
          delta={summary?.successfulAllocations.delta}
        />
        <StatCard
          label="Avg. Matching Time"
          icon={Timer}
          tone="active"
          loading={loadingSummary}
          value={summary?.avgMatchingTime.value}
          unit={summary?.avgMatchingTime.unit}
          delta={summary?.avgMatchingTime.delta}
        />
        <StatCard
          label="Active Operations"
          icon={Radio}
          tone="urgent"
          loading={loadingSummary}
          value={summary?.activeOperations.value}
          delta={summary?.activeOperations.delta}
        />
      </div>

      {/* ---------- Charts ---------- */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChartCard
          title="Resources Rescued Over Time"
          subtitle="Daily kilograms rescued, last 14 days."
          loading={!rescuedOverTime}
          loadingLabel="Loading trend…"
        >
          <AreaChart data={rescuedOverTime ?? []} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
            <defs>
              <linearGradient id="rescuedFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={BRAND_COLOR} stopOpacity={0.35} />
                <stop offset="95%" stopColor={BRAND_COLOR} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke={CHART_AXIS.grid} vertical={false} />
            <XAxis
              dataKey="label"
              stroke={CHART_AXIS.stroke}
              fontSize={CHART_AXIS.fontSize}
              tickLine={false}
              axisLine={false}
              minTickGap={24}
            />
            <YAxis
              stroke={CHART_AXIS.stroke}
              fontSize={CHART_AXIS.fontSize}
              tickLine={false}
              axisLine={false}
              width={40}
            />
            <Tooltip {...tooltipStyle} cursor={CHART_CURSOR.line} formatter={(value) => [`${value} kg`, 'Rescued']} />
            <Area
              type="monotone"
              dataKey="kg"
              stroke={BRAND_COLOR}
              strokeWidth={2}
              fill="url(#rescuedFill)"
              activeDot={CHART_ACTIVE_DOT}
            />
          </AreaChart>
        </ChartCard>

        <ChartCard
          title="Food vs. Medical Resources"
          subtitle="Share of total resources rescued, by type."
          loading={!foodVsMedical}
          loadingLabel="Loading split…"
        >
          <PieChart margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
            <Tooltip {...tooltipStyle} formatter={(value) => [`${value} kg`, undefined]} />
            <Legend wrapperStyle={{ fontSize: 12, color: CHART_AXIS.stroke }} />
            <Pie
              data={foodVsMedical ?? []}
              stroke="none"
              dataKey="value"
              nameKey="name"
              innerRadius="55%"
              outerRadius="80%"
              paddingAngle={2}
            >
              {(foodVsMedical ?? []).map((entry) => (
                <Cell key={entry.key} fill={FOOD_MEDICAL_COLORS[entry.key] ?? BRAND_COLOR} />
              ))}
            </Pie>
          </PieChart>
        </ChartCard>

        <ChartCard
          title="Successful Allocations"
          subtitle="Successful vs. unsuccessful matches, by week."
          loading={!allocations}
          loadingLabel="Loading allocations…"
        >
          <BarChart data={allocations ?? []} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
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
              width={32}
            />
            <Tooltip {...tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 12, color: CHART_AXIS.stroke }} />
            <Bar
              dataKey="successful"
              name="Successful"
              stackId="allocations"
              fill={SUCCESS_COLOR}
              radius={[0, 0, 0, 0]}
            />
            <Bar
              dataKey="unsuccessful"
              name="Unsuccessful"
              stackId="allocations"
              fill={CRITICAL_COLOR}
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ChartCard>

        <ChartCard
          title="Average Matching Time"
          subtitle="Minutes from rescue creation to confirmed match, by week."
          loading={!matchingTime}
          loadingLabel="Loading matching time…"
        >
          <LineChart data={matchingTime ?? []} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
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
              width={32}
              unit=" min"
            />
            <Tooltip {...tooltipStyle} cursor={CHART_CURSOR.line} formatter={(value) => [`${value} min`, 'Avg. time']} />
            <Line
              type="monotone"
              dataKey="minutes"
              stroke={ACTIVE_COLOR}
              strokeWidth={2}
              dot={{ r: 3, fill: ACTIVE_COLOR }}
              activeDot={CHART_ACTIVE_DOT}
            />
          </LineChart>
        </ChartCard>
      </div>

      {/* ---------- Rescue Outcomes ---------- */}
      <section className="space-y-3">
        <div>
          <h2 className="text-sm font-semibold tracking-tight text-content sm:text-base">
            Rescue Outcomes
          </h2>
          <p className="mt-0.5 text-xs text-muted">
            How supply matched demand, and how operations resolved — illustrative mock data, same
            as above.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <ChartCard
            title="Supply vs. Demand"
            subtitle="Kilograms of resources logged vs. kilograms requested, by week."
            loading={!supplyVsDemand}
            loadingLabel="Loading supply and demand…"
          >
            <BarChart
              data={supplyVsDemand ?? []}
              margin={{ top: 8, right: 12, left: -12, bottom: 0 }}
            >
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
                width={40}
              />
              <Tooltip {...tooltipStyle} formatter={(value) => [`${value} kg`, undefined]} />
              <Legend wrapperStyle={{ fontSize: 12, color: CHART_AXIS.stroke }} />
              <Bar dataKey="supply" name="Supply" fill={BRAND_COLOR} radius={[4, 4, 0, 0]} />
              <Bar dataKey="demand" name="Demand" fill={ACTIVE_COLOR} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartCard>

          <ChartCard
            title="Completed Before Deadline"
            subtitle={
              onTimeRate !== null
                ? `${onTimeRate}% of rescues completed before their deadline.`
                : 'Share of rescues completed before their deadline.'
            }
            loading={!deadlinePerformance}
            loadingLabel="Loading deadline performance…"
          >
            <PieChart margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
              <Tooltip {...tooltipStyle} formatter={(value) => [`${value} rescues`, undefined]} />
              <Legend wrapperStyle={{ fontSize: 12, color: CHART_AXIS.stroke }} />
              <Pie
                data={deadlinePerformance ?? []}
                stroke="none"
                dataKey="value"
                nameKey="name"
                innerRadius="55%"
                outerRadius="80%"
                paddingAngle={2}
              >
                {(deadlinePerformance ?? []).map((entry) => (
                  <Cell key={entry.key} fill={DEADLINE_COLORS[entry.key] ?? BRAND_COLOR} />
                ))}
              </Pie>
            </PieChart>
          </ChartCard>

          <ChartCard
            title="Operation Completion"
            subtitle="Operations by how they resolved, as a count."
            loading={!operationCompletion}
            loadingLabel="Loading operation completion…"
          >
            <BarChart
              data={operationCompletion ?? []}
              layout="vertical"
              margin={{ top: 8, right: 16, left: 8, bottom: 0 }}
            >
              <CartesianGrid stroke={CHART_AXIS.grid} horizontal={false} />
              <XAxis
                type="number"
                stroke={CHART_AXIS.stroke}
                fontSize={CHART_AXIS.fontSize}
                tickLine={false}
                axisLine={false}
                allowDecimals={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                stroke={CHART_AXIS.stroke}
                fontSize={CHART_AXIS.fontSize}
                tickLine={false}
                axisLine={false}
                width={110}
              />
              <Tooltip {...tooltipStyle} formatter={(value) => [`${value} operations`, undefined]} />
              <Bar dataKey="value" name="Operations" radius={[0, 4, 4, 0]}>
                {(operationCompletion ?? []).map((entry) => (
                  <Cell key={entry.key} fill={COMPLETION_COLORS[entry.key] ?? BRAND_COLOR} />
                ))}
              </Bar>
            </BarChart>
          </ChartCard>

          <ChartCard
            title="At-Risk vs. Completed Operations"
            subtitle="Count of operations, by week."
            loading={!atRiskVsCompleted}
            loadingLabel="Loading at-risk comparison…"
          >
            <BarChart
              data={atRiskVsCompleted ?? []}
              margin={{ top: 8, right: 12, left: -12, bottom: 0 }}
            >
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
                width={32}
                allowDecimals={false}
              />
              <Tooltip {...tooltipStyle} formatter={(value) => [`${value} operations`, undefined]} />
              <Legend wrapperStyle={{ fontSize: 12, color: CHART_AXIS.stroke }} />
              <Bar dataKey="completed" name="Completed" fill={SUCCESS_COLOR} radius={[4, 4, 0, 0]} />
              <Bar dataKey="atRisk" name="At-Risk" fill={URGENT_COLOR} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartCard>
        </div>
      </section>

      {/* ---------- Predictive Surplus Demo ---------- */}
      <PredictiveSurplusCard
        history={surplusHistory}
        prediction={surplusPrediction}
        loading={!surplusHistory || !surplusPrediction}
      />
    </div>
  );
}
