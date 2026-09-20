import { useCallback, useEffect, useState } from 'react';
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
import { ErrorState } from '@/components/ui';
import PredictiveSurplusCard from '@/components/PredictiveSurplusCard';
import { CHART_ACTIVE_DOT, CHART_AXIS, CHART_CURSOR, RESOURCE_META } from '@/utils/theme';
import {
  ANALYTICS_LIVE,
  INSIGHT_WEEKS,
  TREND_DAYS,
  getAnalyticsSummary,
  getAnalyticsInsights,
  getResourcesRescuedOverTime,
  getFoodVsMedical,
  getSurplusForecast,
} from '@/services/analyticsService';

/** Live quantities mix units (meals, kg, vials...), so they are plain "units". */
const QUANTITY_UNIT = 'units';

const SUCCESS_COLOR = '#22c55e';
const CRITICAL_COLOR = '#f4506a';
const BRAND_COLOR = '#14b98f';
const ACTIVE_COLOR = '#38bdf8';
const URGENT_COLOR = '#f59e0b';

/** Status → color for the operation-completion chart, matching STATUS_META's palette. */
const COMPLETION_COLORS = {
  completed: SUCCESS_COLOR,
  inProgress: ACTIVE_COLOR,
  failed: CRITICAL_COLOR,
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

/** Every value in every row of `rows` for `keys` is zero / missing → nothing to plot. */
const hasNoValues = (rows, keys) => rows.every((row) => keys.every((key) => !row[key]));

/** 4.2 -> { value: '4.2', unit: 'min' }; 0.4 -> { value: '24', unit: 'sec' }; null -> em dash. */
function matchingTimeStat(minutes) {
  if (minutes === null || minutes === undefined) return { value: '—', unit: undefined };
  if (minutes < 1) return { value: String(Math.round(minutes * 60)), unit: 'sec' };
  return { value: minutes.toFixed(1), unit: 'min' };
}

/**
 * Analytics — reporting overview built only on real data.
 *
 * Every summary card and chart is computed by the backend from the database
 * (see services/analyticsService.js). There is no sample data: a chart with
 * nothing to plot shows an empty state instead, and the summary cards read
 * zero. Sections load independently, so one slow endpoint never blocks the
 * rest of the page.
 */
export default function Analytics() {
  const [summary, setSummary] = useState(null);
  const [insights, setInsights] = useState(null);
  const [rescuedOverTime, setRescuedOverTime] = useState(null);
  const [foodVsMedical, setFoodVsMedical] = useState(null);
  const [surplusForecast, setSurplusForecast] = useState(null);

  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    setError(null);

    // Every section loads on its own; the first failure shows the error panel
    // (with Retry) instead of leaving the spinners up forever.
    const load = (request, setter) =>
      request
        .then((data) => active && setter(data))
        .catch((failure) => active && setError(failure));

    load(getAnalyticsSummary(), setSummary);
    load(getAnalyticsInsights(), setInsights);
    load(getResourcesRescuedOverTime(), setRescuedOverTime);
    load(getFoodVsMedical(), setFoodVsMedical);
    load(getSurplusForecast(), setSurplusForecast);

    return () => {
      active = false;
    };
  }, [reloadKey]);

  const retry = useCallback(() => {
    setSummary(null);
    setInsights(null);
    setRescuedOverTime(null);
    setFoodVsMedical(null);
    setSurplusForecast(null);
    setReloadKey((key) => key + 1);
  }, []);

  const loadingSummary = !summary || !insights;

  // Derived from the chart data itself, not a separately hardcoded number,
  // so the headline rate can never drift out of sync with the donut.
  const deadlineTotal = insights
    ? insights.deadlinePerformance.reduce((sum, entry) => sum + entry.value, 0)
    : 0;
  const onTimeRate =
    insights && deadlineTotal > 0
      ? Math.round(
          ((insights.deadlinePerformance.find((entry) => entry.key === 'onTime')?.value ?? 0) /
            deadlineTotal) *
            100,
        )
      : null;

  const matchingStat = matchingTimeStat(insights?.avgMatchingMinutes);

  if (error) {
    return (
      <div className="animate-fade-up space-y-6 lg:space-y-8">
        <h1 className="text-xl font-bold tracking-tight text-content sm:text-2xl">Analytics</h1>
        <div className="panel">
          <ErrorState
            title="Couldn't load analytics"
            description={error.message || 'The request could not be completed. Try again in a moment.'}
            onRetry={retry}
          />
        </div>
      </div>
    );
  }

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
        {ANALYTICS_LIVE ? (
          <p className="text-xs leading-relaxed text-muted">
            Every figure and chart here is computed from the database. Where nothing has been
            recorded yet the cards read zero and the chart shows an empty state — nothing is
            estimated or filled in.
          </p>
        ) : (
          <p className="text-xs leading-relaxed text-muted">
            The app is not connected to the backend, so there is nothing to show. Set{' '}
            <span className="font-medium text-content">VITE_USE_MOCKS=false</span> in the
            frontend <span className="font-medium text-content">.env</span>, restart{' '}
            <span className="font-medium text-content">npm run dev</span>, and sign in with a
            backend account.
          </p>
        )}
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
          value={matchingStat.value}
          unit={matchingStat.unit}
          delta={
            insights?.matchingSamples
              ? `${insights.matchingSamples} matched request${insights.matchingSamples === 1 ? '' : 's'}, last ${insights.windowWeeks} weeks`
              : 'No matched requests yet'
          }
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
          subtitle={`Daily ${QUANTITY_UNIT} delivered, last ${TREND_DAYS} days.`}
          loading={!rescuedOverTime}
          loadingLabel="Loading trend…"
          live={ANALYTICS_LIVE}
          empty={Boolean(rescuedOverTime) && hasNoValues(rescuedOverTime, ['quantity'])}
          emptyLabel="Nothing delivered in this period yet. Deliveries show up here once an operation is marked delivered."
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
            <Tooltip {...tooltipStyle} cursor={CHART_CURSOR.line} formatter={(value) => [`${value} ${QUANTITY_UNIT}`, 'Rescued']} />
            <Area
              type="monotone"
              dataKey="quantity"
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
          live={ANALYTICS_LIVE}
          empty={Boolean(foodVsMedical) && hasNoValues(foodVsMedical, ['value'])}
          emptyLabel="Nothing rescued yet. The split appears once an allocation is delivered."
        >
          <PieChart margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
            <Tooltip {...tooltipStyle} formatter={(value) => [`${value} ${QUANTITY_UNIT}`, undefined]} />
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
          subtitle="Delivered vs. cancelled allocations, by week."
          loading={!insights}
          loadingLabel="Loading allocations…"
          live={ANALYTICS_LIVE}
          empty={Boolean(insights) && hasNoValues(insights.allocations, ['successful', 'unsuccessful'])}
          emptyLabel="No delivered or cancelled allocations in this period yet."
        >
          <BarChart data={insights?.allocations ?? []} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
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
            <Tooltip {...tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 12, color: CHART_AXIS.stroke }} />
            <Bar
              dataKey="successful"
              name="Delivered"
              stackId="allocations"
              fill={SUCCESS_COLOR}
              radius={[0, 0, 0, 0]}
            />
            <Bar
              dataKey="unsuccessful"
              name="Cancelled"
              stackId="allocations"
              fill={CRITICAL_COLOR}
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ChartCard>

        <ChartCard
          title="Average Matching Time"
          subtitle="Minutes from rescue creation to first match, by week."
          loading={!insights}
          loadingLabel="Loading matching time…"
          live={ANALYTICS_LIVE}
          empty={Boolean(insights) && insights.matchingTime.every((week) => week.minutes === null)}
          emptyLabel="No rescue requests have been matched in this period yet."
        >
          <LineChart data={insights?.matchingTime ?? []} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
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
              width={44}
              unit=" min"
            />
            <Tooltip {...tooltipStyle} cursor={CHART_CURSOR.line} formatter={(value) => [`${value} min`, 'Avg. time']} />
            <Line
              type="monotone"
              dataKey="minutes"
              stroke={ACTIVE_COLOR}
              strokeWidth={2}
              connectNulls={false}
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
            How supply matched demand, and how operations resolved. The weekly charts cover the last{' '}
            {INSIGHT_WEEKS} weeks (weeks start on Monday); quantities are units as recorded.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <ChartCard
            title="Supply vs. Demand"
            subtitle="Units posted vs. units requested, by week."
            loading={!insights}
            loadingLabel="Loading supply and demand…"
            live={ANALYTICS_LIVE}
            empty={Boolean(insights) && hasNoValues(insights.supplyVsDemand, ['supply', 'demand'])}
            emptyLabel="No resources posted or requested in this period yet."
          >
            <BarChart
              data={insights?.supplyVsDemand ?? []}
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
              <Tooltip {...tooltipStyle} formatter={(value) => [`${value} ${QUANTITY_UNIT}`, undefined]} />
              <Legend wrapperStyle={{ fontSize: 12, color: CHART_AXIS.stroke }} />
              <Bar dataKey="supply" name="Supply" fill={BRAND_COLOR} radius={[4, 4, 0, 0]} />
              <Bar dataKey="demand" name="Demand" fill={ACTIVE_COLOR} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartCard>

          <ChartCard
            title="Completed Before Deadline"
            subtitle={
              onTimeRate !== null
                ? `${onTimeRate}% of delivered rescues arrived before their deadline.`
                : 'Share of delivered rescues that arrived before their deadline.'
            }
            loading={!insights}
            loadingLabel="Loading deadline performance…"
            live={ANALYTICS_LIVE}
            empty={Boolean(insights) && deadlineTotal === 0}
            emptyLabel="No delivered rescues with a deadline in this period yet."
          >
            <PieChart margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
              <Tooltip {...tooltipStyle} formatter={(value) => [`${value} rescues`, undefined]} />
              <Legend wrapperStyle={{ fontSize: 12, color: CHART_AXIS.stroke }} />
              <Pie
                data={insights?.deadlinePerformance ?? []}
                stroke="none"
                dataKey="value"
                nameKey="name"
                innerRadius="55%"
                outerRadius="80%"
                paddingAngle={2}
              >
                {(insights?.deadlinePerformance ?? []).map((entry) => (
                  <Cell key={entry.key} fill={DEADLINE_COLORS[entry.key] ?? BRAND_COLOR} />
                ))}
              </Pie>
            </PieChart>
          </ChartCard>

          <ChartCard
            title="Operation Completion"
            subtitle="Operations by how they resolved."
            loading={!insights}
            loadingLabel="Loading operation completion…"
            live={ANALYTICS_LIVE}
            empty={Boolean(insights) && hasNoValues(insights.operationCompletion, ['value'])}
            emptyLabel="No operations started in this period yet."
          >
            <BarChart
              data={insights?.operationCompletion ?? []}
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
                {(insights?.operationCompletion ?? []).map((entry) => (
                  <Cell key={entry.key} fill={COMPLETION_COLORS[entry.key] ?? BRAND_COLOR} />
                ))}
              </Bar>
            </BarChart>
          </ChartCard>

          <ChartCard
            title="At-Risk vs. Completed Operations"
            subtitle="Completed on time vs. failed or overdue, by week."
            loading={!insights}
            loadingLabel="Loading at-risk comparison…"
            live={ANALYTICS_LIVE}
            empty={Boolean(insights) && hasNoValues(insights.atRiskVsCompleted, ['completed', 'atRisk'])}
            emptyLabel="No completed or at-risk operations in this period yet."
          >
            <BarChart
              data={insights?.atRiskVsCompleted ?? []}
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

      {/* ---------- Predictive Surplus ---------- */}
      <PredictiveSurplusCard forecast={surplusForecast} loading={!surplusForecast} />
    </div>
  );
}
