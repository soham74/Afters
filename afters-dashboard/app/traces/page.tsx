"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TraceRow, type Trace } from "@/components/trace-row";
import { Button } from "@/components/ui/button";
import { MetricTile } from "@/components/metric-tile";
import { formatCost } from "@/lib/format";

const KINDS = ["llm", "deterministic", "human_feedback"] as const;

export default function TracesPage() {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [kindFilter, setKindFilter] = useState<string | undefined>();
  const [sort, setSort] = useState<"created_at" | "latency_ms" | "cost_usd">(
    "created_at",
  );

  async function load() {
    try {
      const data = await api.listTraces({ kind: kindFilter, limit: 200, sort });
      setTraces(data);
    } catch {}
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, [kindFilter, sort]);

  const metrics = useMemo(() => {
    const totalCost = traces.reduce((s, t) => s + (t.cost_usd || 0), 0);
    const totalTokens = traces.reduce((s, t) => s + (t.tokens_in + t.tokens_out), 0);
    const llm = traces.filter((t) => t.kind === "llm");
    const avgLatency = llm.length
      ? llm.reduce((s, t) => s + t.latency_ms, 0) / llm.length
      : 0;
    return { totalCost, totalTokens, avgLatency, llmCount: llm.length };
  }, [traces]);

  const histogram = useMemo(() => {
    const buckets = [0, 250, 500, 1000, 2000, 4000, 8000];
    const labels = ["<250ms", "<500ms", "<1s", "<2s", "<4s", "<8s", "8s+"];
    const counts = Array(buckets.length).fill(0);
    for (const t of traces) {
      if (t.kind !== "llm") continue;
      const idx = buckets.findIndex((b, i) => t.latency_ms <= b || i === buckets.length - 1);
      const final = idx < 0 ? buckets.length - 1 : idx;
      counts[final]++;
    }
    const max = Math.max(1, ...counts);
    return counts.map((c, i) => ({ label: labels[i], count: c, pct: c / max }));
  }, [traces]);

  return (
    <div className="p-8 space-y-6 max-w-[1400px]">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Agent Traces</h1>
        <p className="text-sm text-ink-muted mt-1">
          every LLM call, every deterministic agent, and every human-in-the-loop action. sorted by {sort.replace("_", " ")}.
        </p>
      </header>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricTile
          label="traces (window)"
          value={String(traces.length)}
          sublabel={`${metrics.llmCount} from LLM calls`}
        />
        <MetricTile
          label="avg LLM latency"
          value={`${Math.round(metrics.avgLatency)}ms`}
          sublabel="averaged over visible LLM traces"
        />
        <MetricTile
          label="tokens (window)"
          value={metrics.totalTokens.toLocaleString()}
          sublabel="in + out combined"
        />
        <MetricTile
          label="cost (window)"
          value={formatCost(metrics.totalCost)}
          sublabel="sonnet 4-5 + haiku 4-5 pricing"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">LLM latency histogram</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-end gap-1.5 h-24">
            {histogram.map((b) => {
              const hasData = b.count > 0;
              // Empty buckets render as a faint hairline at baseline so the
              // distribution reads as intentional rather than broken; populated
              // buckets get a proportional bar with a visible minimum so a
              // single 1-count doesn't disappear next to a bigger neighbor.
              const height = hasData
                ? `${Math.max(15, b.pct * 100)}%`
                : "2px";
              return (
                <div
                  key={b.label}
                  className="flex-1 flex flex-col items-center justify-end"
                >
                  <div
                    className={
                      hasData
                        ? "w-full bg-accent/70 rounded-sm"
                        : "w-full bg-line rounded-sm"
                    }
                    style={{ height }}
                  />
                  <div className="text-[10px] text-ink-muted mt-1">{b.label}</div>
                  <div
                    className={
                      hasData
                        ? "text-[10px] font-semibold tabular-nums"
                        : "text-[10px] tabular-nums text-ink-faint"
                    }
                  >
                    {b.count}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center gap-2 flex-wrap">
        <Button
          size="sm"
          variant={kindFilter == null ? "subtle" : "ghost"}
          onClick={() => setKindFilter(undefined)}
        >
          all kinds
        </Button>
        {KINDS.map((k) => (
          <Button
            key={k}
            size="sm"
            variant={kindFilter === k ? "subtle" : "ghost"}
            onClick={() => setKindFilter(kindFilter === k ? undefined : k)}
          >
            {k}
          </Button>
        ))}
        <div className="w-px h-6 bg-line mx-1" />
        <span className="text-xs text-ink-muted">sort by:</span>
        {(["created_at", "latency_ms", "cost_usd"] as const).map((s) => (
          <Button
            key={s}
            size="sm"
            variant={sort === s ? "subtle" : "ghost"}
            onClick={() => setSort(s)}
          >
            {s.replace("_", " ")}
          </Button>
        ))}
      </div>

      <div className="space-y-2">
        {traces.length === 0 && (
          <div className="text-center text-sm text-ink-muted py-12">
            no traces yet. trigger a scenario from /sessions.
          </div>
        )}
        {traces.map((t) => (
          <TraceRow key={t._id} trace={t} />
        ))}
      </div>
    </div>
  );
}
