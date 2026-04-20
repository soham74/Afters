"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import { api, UnreachableError } from "@/lib/api";
import { formatDuration, formatRelative } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ScenarioButtons } from "@/components/scenario-buttons";
import { OutcomeBadge, StateBadge } from "@/components/outcome-badge";
import { Button } from "@/components/ui/button";

interface Row {
  _id: string;
  date_id: string;
  match_id: string;
  campus: string;
  state: string;
  resolved_outcome: string | null;
  created_at: string;
  resolved_at: string | null;
  participant_names: string[];
  venue_name: string | null;
  time_to_resolution_seconds: number | null;
}

export default function SessionsPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterState, setFilterState] = useState<string | undefined>();
  const [filterCampus, setFilterCampus] = useState<string | undefined>();
  const [reachError, setReachError] = useState<string | null>(null);

  async function load() {
    try {
      const data = await api.listSessions({
        state: filterState,
        campus: filterCampus,
      });
      setRows(data);
      setReachError(null);
    } catch (err: any) {
      if (err instanceof UnreachableError) {
        setReachError(err.message);
      } else {
        setReachError(err?.message ?? "unknown error loading sessions");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, [filterState, filterCampus]);

  return (
    <div className="p-8 space-y-6 max-w-[1600px]">
      <header className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Sessions</h1>
          <p className="text-sm text-ink-muted mt-1">
            every post-date afters_session, live. click a row to open the detail view.
          </p>
        </div>
      </header>

      {reachError && (
        <div className="flex items-start gap-2.5 rounded-md border border-warning/40 bg-warning/5 p-3 text-xs text-warning">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="leading-snug">
            <div className="font-semibold">orchestrator unreachable</div>
            <div className="text-warning/80 mt-0.5">
              {reachError} the dashboard will keep retrying every 2s. run{" "}
              <code className="font-mono text-[11px]">pnpm dev:orchestrator</code>{" "}
              and watch its terminal for an import trace.
            </div>
          </div>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Demo controls</CardTitle>
          <CardDescription>
            trigger a scripted scenario to populate the chat and drive the flow end to end. use reset to clear and re-seed.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ScenarioButtons />
        </CardContent>
      </Card>

      <div className="flex items-center gap-2">
        <Button
          variant={filterState == null ? "subtle" : "ghost"}
          size="sm"
          onClick={() => setFilterState(undefined)}
        >
          all states
        </Button>
        {[
          "awaiting_first_response",
          "awaiting_second_response",
          "mutual_reveal_ready",
          "resolving",
          "resolved",
          "closed",
        ].map((s) => (
          <Button
            key={s}
            variant={filterState === s ? "subtle" : "ghost"}
            size="sm"
            onClick={() => setFilterState(filterState === s ? undefined : s)}
          >
            {s.replace(/_/g, " ")}
          </Button>
        ))}
        <div className="w-px h-6 bg-line mx-1" />
        <Button
          variant={filterCampus == null ? "subtle" : "ghost"}
          size="sm"
          onClick={() => setFilterCampus(undefined)}
        >
          all campuses
        </Button>
        {["UC Berkeley", "UC San Diego", "UCLA", "USC", "UC Davis", "San Jose State"].map((c) => (
          <Button
            key={c}
            variant={filterCampus === c ? "subtle" : "ghost"}
            size="sm"
            onClick={() => setFilterCampus(filterCampus === c ? undefined : c)}
          >
            {c}
          </Button>
        ))}
      </div>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>session</TableHead>
              <TableHead>participants</TableHead>
              <TableHead>campus</TableHead>
              <TableHead>venue</TableHead>
              <TableHead>state</TableHead>
              <TableHead>outcome</TableHead>
              <TableHead>time to resolve</TableHead>
              <TableHead>created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-ink-muted py-8">
                  loading sessions
                </TableCell>
              </TableRow>
            )}
            {!loading && rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-ink-muted py-8">
                  no sessions. trigger a scenario above.
                </TableCell>
              </TableRow>
            )}
            {rows.map((r) => (
              <TableRow key={r._id} className="cursor-pointer">
                <TableCell className="font-mono text-[11px] text-ink-muted">
                  <Link href={`/sessions/${r._id}`}>{r._id.slice(-8)}</Link>
                </TableCell>
                <TableCell>
                  <Link href={`/sessions/${r._id}`} className="hover:underline">
                    {r.participant_names.join(" + ")}
                  </Link>
                </TableCell>
                <TableCell className="text-ink-muted">{r.campus}</TableCell>
                <TableCell className="text-ink-muted">{r.venue_name ?? "·"}</TableCell>
                <TableCell>
                  <StateBadge state={r.state} />
                </TableCell>
                <TableCell>
                  <OutcomeBadge outcome={r.resolved_outcome} />
                </TableCell>
                <TableCell className="text-ink-muted tabular-nums">
                  {formatDuration(r.time_to_resolution_seconds)}
                </TableCell>
                <TableCell className="text-ink-muted text-xs">
                  {formatRelative(r.created_at)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
