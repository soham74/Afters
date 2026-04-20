"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricTile } from "@/components/metric-tile";
import { formatPct } from "@/lib/format";
import { CheckCircle2, Users2, Group, Ghost, Database } from "lucide-react";

interface Metrics {
  total_sessions: number;
  resolved_rate_24h: number;
  resolved_24h_count: number;
  second_date_conversion: number;
  second_date_count: number;
  group_acceptance: number;
  group_count: number;
  ghost_rate: number;
  ghost_count: number;
  outcome_counts: Record<string, number>;
  model_signal_rows: number;
  timeseries: Array<{
    date: string;
    total: number;
    resolved_24h: number;
    rate: number | null;
  }>;
}

export default function MetricsPage() {
  const [m, setM] = useState<Metrics | null>(null);

  async function load() {
    try {
      setM(await api.metrics());
    } catch {}
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, []);

  if (!m) {
    return <div className="p-8 text-sm text-ink-muted">loading metrics</div>;
  }

  return (
    <div className="p-8 space-y-6 max-w-[1400px]">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Metrics</h1>
        <p className="text-sm text-ink-muted mt-1">
          live over the seeded cohort plus any sessions triggered this session.
          targets in the A/B design on /experiments.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricTile
          label="resolved within 24h"
          value={formatPct(m.resolved_rate_24h)}
          sublabel={`${m.resolved_24h_count} of ${m.total_sessions} sessions`}
          accent
          icon={<CheckCircle2 className="w-4 h-4 text-accent" />}
        />
        <MetricTile
          label="second-date conversion"
          value={formatPct(m.second_date_conversion)}
          sublabel={`${m.second_date_count} of ${m.total_sessions} sessions ended both_again`}
          icon={<Users2 className="w-4 h-4 text-ink-muted" />}
        />
        <MetricTile
          label="group acceptance"
          value={formatPct(m.group_acceptance)}
          sublabel={`${m.group_count} of ${m.total_sessions} sessions ended both_group`}
          icon={<Group className="w-4 h-4 text-ink-muted" />}
        />
        <MetricTile
          label="ghost rate"
          value={formatPct(m.ghost_rate)}
          sublabel={`${m.ghost_count} of ${m.total_sessions} sessions timed out`}
          icon={<Ghost className="w-4 h-4 text-ink-muted" />}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricTile
          label="model signal density"
          value={String(m.model_signal_rows)}
          sublabel="rows written to feedback_training.jsonl"
          icon={<Database className="w-4 h-4 text-ink-muted" />}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">outcome breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2 text-xs">
            {Object.entries(m.outcome_counts)
              .sort((a, b) => b[1] - a[1])
              .map(([outcome, count]) => (
                <div
                  key={outcome}
                  className="rounded-md border border-line bg-white px-3 py-2 flex flex-col"
                >
                  <span className="text-ink-muted text-[10px] uppercase tracking-wider">
                    {outcome}
                  </span>
                  <span className="font-semibold tabular-nums text-sm mt-0.5">
                    {count}{" "}
                    <span className="text-ink-muted font-normal text-[11px]">
                      ({m.total_sessions > 0
                        ? ((count / m.total_sessions) * 100).toFixed(1)
                        : "0"}
                      %)
                    </span>
                  </span>
                </div>
              ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">resolved-within-24h, last 14 days</CardTitle>
        </CardHeader>
        <CardContent>
          <Timeseries data={m.timeseries} />
        </CardContent>
      </Card>
    </div>
  );
}

function Timeseries({
  data,
}: {
  data: Array<{ date: string; total: number; resolved_24h: number; rate: number | null }>;
}) {
  const width = 900;
  const height = 200;
  const padX = 32;
  const padY = 24;
  const innerW = width - padX * 2;
  const innerH = height - padY * 2;
  const n = data.length;
  if (n === 0) return null;
  const maxTotal = Math.max(1, ...data.map((d) => d.total));

  const points = data.map((d, i) => {
    const x = padX + (i / Math.max(1, n - 1)) * innerW;
    const y = padY + innerH - (d.rate ?? 0) * innerH;
    return { x, y, d };
  });
  const path = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
      <defs>
        <linearGradient id="series" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#FF6B5E" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#FF6B5E" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0, 0.25, 0.5, 0.75, 1].map((t) => (
        <g key={t}>
          <line
            x1={padX}
            x2={width - padX}
            y1={padY + innerH - t * innerH}
            y2={padY + innerH - t * innerH}
            stroke="#E5E5E5"
            strokeDasharray="2 3"
          />
          <text
            x={padX - 6}
            y={padY + innerH - t * innerH + 3}
            textAnchor="end"
            fontSize="10"
            fill="#A3A3A3"
          >
            {Math.round(t * 100)}%
          </text>
        </g>
      ))}
      <path
        d={`${path} L ${points[points.length - 1].x} ${padY + innerH} L ${points[0].x} ${padY + innerH} Z`}
        fill="url(#series)"
      />
      <path d={path} fill="none" stroke="#FF6B5E" strokeWidth="2" />
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r={3} fill="#FF6B5E" />
          {i % 2 === 0 && (
            <text
              x={p.x}
              y={height - 6}
              textAnchor="middle"
              fontSize="10"
              fill="#737373"
            >
              {p.d.date.slice(5)}
            </text>
          )}
        </g>
      ))}
    </svg>
  );
}
