/**
 * ResultsDashboard
 * Fully dynamic — driven by whatever JSON /api/analyze returns.
 * No column names, category names, or month strings are hardcoded here.
 */
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  PieChart,
  Pie,
  Legend,
  ComposedChart,
  Area,
  Line,
  ReferenceLine,
} from "recharts";
import { Download, Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

// ── types ─────────────────────────────────────────────────────────────────────

interface Summary {
  total_records: number;
  total_sales: number;
  num_categories: number;
  period_start: string;
  period_end: string;
  currency_symbol: string;
}
interface MonthlyTrendItem  { period: string; total_sales: number }
interface CategoryItem       { category: string; total_sales: number }
interface ForecastItem       { period: string; forecast: number; lower: number; upper: number }
interface AnomalyItem        { period: string; value: number }

interface AnalysisResult {
  error?: string;
  summary:            Summary;
  monthly_trend:      MonthlyTrendItem[];
  category_breakdown: CategoryItem[];
  forecast:           ForecastItem[];
  insights:           string[];
  anomalies:          AnomalyItem[];
}

interface Props {
  data: AnalysisResult;
  onExportPDF: () => void;
  exporting?: boolean;
}

// ── constants ─────────────────────────────────────────────────────────────────

const PIE_COLORS = [
  "#F5C518","#5799EF","#22c55e","#e50914",
  "#a855f7","#f97316","#06b6d4","#ec4899",
];
const THEME_PRIMARY = "#7c6fff"; // matches --primary hsl(250 100% 70%)
const ANOMALY_COLOR = "#ef4444";
const FORECAST_LINE = "#06b6d4";
const BAND_COLOR    = "#06b6d420";

// ── formatters ────────────────────────────────────────────────────────────────

const fmtCurrency = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(v);

const fmtCurrencyFull = (v: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(v);

// ── insight icon heuristic ────────────────────────────────────────────────────

function insightIcon(text: string): string {
  const t = text.toLowerCase();
  if (/anomal|unusual|spike|drop/.test(t)) return "⚠️";
  if (/peak|high|top|growth/.test(t))      return "📈";
  if (/low|dip|clearance/.test(t))         return "📉";
  return "💡";
}

// ── custom tooltip helpers ────────────────────────────────────────────────────

const BarTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as MonthlyTrendItem;
  return (
    <div className="bg-card border border-border rounded-lg px-3 py-2 text-sm shadow-lg">
      <p className="font-medium text-foreground">{d.period}</p>
      <p className="text-primary">{fmtCurrencyFull(d.total_sales)}</p>
    </div>
  );
};

const ForecastTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload as ForecastItem;
  return (
    <div className="bg-card border border-border rounded-lg px-3 py-2 text-sm shadow-lg space-y-0.5">
      <p className="font-medium text-foreground">{d.period}</p>
      <p className="text-cyan-400">Forecast: {fmtCurrencyFull(d.forecast)}</p>
      <p className="text-muted-foreground text-xs">
        Range: {fmtCurrency(d.lower)} – {fmtCurrency(d.upper)}
      </p>
    </div>
  );
};

const PieTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as CategoryItem;
  return (
    <div className="bg-card border border-border rounded-lg px-3 py-2 text-sm shadow-lg">
      <p className="font-medium text-foreground">{d.category}</p>
      <p className="text-primary">{fmtCurrencyFull(d.total_sales)}</p>
    </div>
  );
};

// ── Pie label renderer (outside label: name + %) ──────────────────────────────

const renderPieLabel = ({
  cx, cy, midAngle, outerRadius, percent, category,
}: any) => {
  const RADIAN = Math.PI / 180;
  const r = outerRadius + 28;
  const x = cx + r * Math.cos(-midAngle * RADIAN);
  const y = cy + r * Math.sin(-midAngle * RADIAN);
  if (percent < 0.04) return null; // skip tiny slices
  return (
    <text
      x={x} y={y}
      fill="#a0a0b0"
      textAnchor={x > cx ? "start" : "end"}
      dominantBaseline="central"
      fontSize={11}
    >
      {category} {(percent * 100).toFixed(0)}%
    </text>
  );
};

// ── KPI card ──────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 flex flex-col gap-1 shadow-sm">
      <p className="text-xs text-muted-foreground uppercase tracking-wider">{label}</p>
      <p className="text-2xl font-bold text-foreground truncate">{value}</p>
      {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
    </div>
  );
}

// ── section wrapper ───────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="text-base font-semibold text-foreground mb-3">{title}</h3>
      {children}
    </section>
  );
}

// ── main component ────────────────────────────────────────────────────────────

export default function ResultsDashboard({ data, onExportPDF, exporting }: Props) {
  // ── error state ────────────────────────────────────────────────────────────
  if (data.error) {
    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-6 flex items-start gap-4">
        <AlertCircle className="w-6 h-6 text-destructive shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-destructive mb-1">Column Detection Failed</p>
          <p className="text-sm text-muted-foreground">{data.error}</p>
          <p className="text-sm text-muted-foreground mt-2">
            <strong>Tip:</strong> Make sure your CSV has at least one date column (or YEAR + MONTH columns)
            and one numeric column containing sales, revenue, or amount figures.
          </p>
        </div>
      </div>
    );
  }

  const { summary, monthly_trend, category_breakdown, forecast, insights, anomalies } = data;

  // build a Set of anomaly periods for O(1) lookup in the bar chart
  const anomalyPeriods = new Set(anomalies.map((a) => a.period));

  // pre-compute total for pie percentages (recharts does this internally but we pass it to the label)
  const totalCatSales = category_breakdown.reduce((s, c) => s + c.total_sales, 0);

  return (
    <div className="space-y-8">
      {/* ── Row 1 — KPI cards ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard
          label="Total Records"
          value={summary.total_records.toLocaleString()}
        />
        <KpiCard
          label="Total Sales"
          value={fmtCurrency(summary.total_sales)}
        />
        <KpiCard
          label="Categories"
          value={summary.num_categories > 0 ? summary.num_categories.toString() : "—"}
        />
        <KpiCard
          label="Analysis Period"
          value={summary.period_start}
          sub={`to ${summary.period_end}`}
        />
      </div>

      {/* ── Row 2 — Bar + Pie ─────────────────────────────────────────────── */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Monthly Trend Bar Chart */}
        <Section title="Monthly Sales Trend">
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={monthly_trend} margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
                <XAxis
                  dataKey="period"
                  tick={{ fontSize: 10, fill: "#6b7280" }}
                  tickLine={false}
                  axisLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tickFormatter={fmtCurrency}
                  tick={{ fontSize: 10, fill: "#6b7280" }}
                  tickLine={false}
                  axisLine={false}
                  width={56}
                />
                <Tooltip content={<BarTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                <Bar dataKey="total_sales" radius={[3, 3, 0, 0]}>
                  {monthly_trend.map((entry) => (
                    <Cell
                      key={entry.period}
                      fill={anomalyPeriods.has(entry.period) ? ANOMALY_COLOR : THEME_PRIMARY}
                      fillOpacity={anomalyPeriods.has(entry.period) ? 1 : 0.85}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            {anomalies.length > 0 && (
              <p className="text-xs text-muted-foreground mt-2 text-center">
                🔴 Red bars indicate anomalous months (&gt;2σ from mean)
              </p>
            )}
          </div>
        </Section>

        {/* Category Breakdown Pie Chart */}
        <Section title="Category Breakdown">
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            {category_breakdown.length === 0 ? (
              <div className="flex items-center justify-center h-[250px] text-muted-foreground text-sm">
                No category column detected in your CSV.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={category_breakdown}
                    dataKey="total_sales"
                    nameKey="category"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    labelLine={false}
                    label={renderPieLabel}
                  >
                    {category_breakdown.map((_, idx) => (
                      <Cell
                        key={idx}
                        fill={PIE_COLORS[idx % PIE_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip content={<PieTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </Section>
      </div>

      {/* ── Row 3 — Forecast (full width) ────────────────────────────────── */}
      {forecast.length > 0 && (
        <Section title="12-Month Sales Forecast">
          <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
            <ResponsiveContainer width="100%" height={250}>
              <ComposedChart data={forecast} margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
                <XAxis
                  dataKey="period"
                  tick={{ fontSize: 10, fill: "#6b7280" }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tickFormatter={fmtCurrency}
                  tick={{ fontSize: 10, fill: "#6b7280" }}
                  tickLine={false}
                  axisLine={false}
                  width={56}
                />
                <Tooltip content={<ForecastTooltip />} cursor={{ stroke: "rgba(255,255,255,0.08)" }} />
                {/* Confidence band rendered as stacked areas */}
                <Area
                  dataKey="lower"
                  stroke="transparent"
                  fill={BAND_COLOR}
                  isAnimationActive={false}
                  legendType="none"
                />
                <Area
                  dataKey="upper"
                  stroke="transparent"
                  fill={BAND_COLOR}
                  isAnimationActive={false}
                  legendType="none"
                />
                <Line
                  type="monotone"
                  dataKey="forecast"
                  stroke={FORECAST_LINE}
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: FORECAST_LINE }}
                  activeDot={{ r: 5 }}
                />
                <ReferenceLine
                  x={forecast[0]?.period}
                  stroke="#ffffff30"
                  strokeDasharray="4 4"
                  label={{ value: "Forecast Start", fill: "#6b7280", fontSize: 10, position: "insideTopRight" }}
                />
              </ComposedChart>
            </ResponsiveContainer>
            <p className="text-xs text-muted-foreground text-center mt-2">
              Shaded band = ±20% confidence interval &nbsp;·&nbsp; Line = 6-month moving average
            </p>
          </div>
        </Section>
      )}

      {/* ── Row 4 — Insights ─────────────────────────────────────────────── */}
      {insights.length > 0 && (
        <Section title="Insights & Recommendations">
          <div className="grid sm:grid-cols-2 gap-3">
            {insights.map((text, i) => (
              <div
                key={i}
                className="rounded-xl border border-border bg-card px-4 py-3 flex items-start gap-3 shadow-sm"
              >
                <span className="text-xl leading-none mt-0.5 shrink-0">{insightIcon(text)}</span>
                <p className="text-sm text-muted-foreground leading-relaxed">{text}</p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* ── Export button ─────────────────────────────────────────────────── */}
      <div className="flex justify-end pt-2">
        <Button
          onClick={onExportPDF}
          disabled={exporting}
          size="lg"
          className="shadow-lg shadow-primary/20"
        >
          {exporting
            ? <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            : <Download className="w-4 h-4 mr-2" />}
          {exporting ? "Exporting..." : "Export PDF Report"}
        </Button>
      </div>
    </div>
  );
}
