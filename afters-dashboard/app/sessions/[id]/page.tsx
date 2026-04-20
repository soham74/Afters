"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { ArrowLeft, MapPin, Clock, Users2 } from "lucide-react";
import { api } from "@/lib/api";
import { formatDuration, formatRelative, formatTime, formatDate, initials } from "@/lib/format";
import { StateGraph } from "@/components/state-graph";
import { OutcomeBadge, StateBadge } from "@/components/outcome-badge";
import { TraceRow, type Trace } from "@/components/trace-row";
import { IMessageChat } from "@/components/imessage-chat";
import { ClosureReviewCard, type ClosureReview } from "@/components/closure-review-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface Participant {
  user_id: string;
  response_state: "pending" | "submitted" | "revealed";
  choice: string | null;
  interest_level: number | null;
  memorable_moments: string[];
  concerns: string[];
  wants_second_date: boolean | null;
  willing_to_group_hang: boolean | null;
  free_text_note: string | null;
  raw_reply_text: string | null;
  submitted_at: string | null;
  user: {
    _id: string;
    name: string;
    avatar_color: string;
    year: string;
    pronouns: string;
    profile: { persona_summary: string };
  } | null;
}

interface SessionDetail {
  session: {
    _id: string;
    state: string;
    resolved_outcome: string | null;
    campus: string;
    created_at: string;
    resolved_at: string | null;
    timeout_at: string;
    participants_hydrated: Participant[];
  };
  date: { scheduled_for: string; completed_at: string | null };
  venue: { name: string; address: string; tags: string[] };
  match: { compatibility_score: number; explanation: string };
  traces: Trace[];
  second_date: any | null;
  group_queue_entries: any[];
  closure_review: ClosureReview | null;
}

export default function SessionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [data, setData] = useState<SessionDetail | null>(null);

  async function load() {
    try {
      const d = await api.getSession(id);
      setData(d);
    } catch (err) {
      console.error(err);
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 1500);
    return () => clearInterval(t);
  }, [id]);

  if (!data) {
    return (
      <div className="p-8 text-sm text-ink-muted">loading session</div>
    );
  }

  const { session, date, venue, match, traces, second_date, group_queue_entries, closure_review } = data;
  const [a, b] = session.participants_hydrated;
  const ttr = session.resolved_at
    ? (new Date(session.resolved_at).getTime() - new Date(session.created_at).getTime()) / 1000
    : null;

  return (
    <div className="p-8 space-y-6 max-w-[1600px]">
      <header className="flex items-center justify-between">
        <div>
          <Link
            href="/sessions"
            className="text-xs text-ink-muted hover:text-ink flex items-center gap-1 mb-2"
          >
            <ArrowLeft className="w-3 h-3" /> back to sessions
          </Link>
          <h1 className="text-2xl font-semibold tracking-tight">
            {a?.user?.name ?? "?"} + {b?.user?.name ?? "?"}
          </h1>
          <div className="flex items-center gap-3 mt-2 text-xs text-ink-muted">
            <span className="font-mono">{session._id}</span>
            <span>{session.campus}</span>
            <span className="inline-flex items-center gap-1">
              <MapPin className="w-3 h-3" /> {venue?.name ?? "·"}
            </span>
            <span className="inline-flex items-center gap-1">
              <Clock className="w-3 h-3" /> {formatRelative(session.created_at)}
            </span>
            {ttr != null && (
              <span>resolved in {formatDuration(ttr)}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StateBadge state={session.state} />
          <OutcomeBadge outcome={session.resolved_outcome} />
        </div>
      </header>

      <Card>
        <CardContent className="pt-5">
          <StateGraph state={session.state} outcome={session.resolved_outcome} />
        </CardContent>
      </Card>

      {closure_review && (
        <ClosureReviewCard review={closure_review} onAction={load} />
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <Users2 className="w-4 h-4 text-accent" /> structured debriefs
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[a, b].map((p, i) => (
                  <DebriefPanel key={p?.user_id ?? i} p={p} />
                ))}
              </div>
            </CardContent>
          </Card>

          {second_date && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">second date proposal</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <div className="text-[11px] uppercase tracking-wider text-ink-muted">
                    ranked venues
                  </div>
                  <ol className="mt-2 space-y-2">
                    {second_date.proposed_venues?.map((pv: any, i: number) => (
                      <li key={i} className="border border-line rounded-md p-3 bg-white">
                        <div className="flex items-center gap-2">
                          <Badge variant={i === 0 ? "accent" : "outline"} className="text-[10px]">
                            rank {i + 1}
                          </Badge>
                          <div className="font-semibold text-sm">
                            {pv.venue?.name ?? pv.venue_id}
                          </div>
                          <div className="text-xs text-ink-muted">{pv.venue?.address}</div>
                        </div>
                        <div className="text-sm text-ink mt-1 leading-snug">{pv.reason}</div>
                      </li>
                    ))}
                  </ol>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-wider text-ink-muted">
                    proposed time slots
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {second_date.proposed_time_slots?.map((t: string) => (
                      <Badge key={t} variant="outline" className="text-xs">
                        {new Date(t).toLocaleString([], {
                          weekday: "short",
                          month: "short",
                          day: "numeric",
                          hour: "numeric",
                          minute: "2-digit",
                        })}
                      </Badge>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {group_queue_entries?.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">group queue entries</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {group_queue_entries.map((g: any) => (
                  <div key={g._id} className="border border-line rounded-md p-3 text-sm">
                    <div className="flex items-center gap-2">
                      <Badge variant="info">{g.status}</Badge>
                      <span className="font-mono text-[11px] text-ink-muted">{g.user_id.slice(-6)}</span>
                      {g.group_event_id && (
                        <span className="text-[11px] text-ink-muted">
                          → event {g.group_event_id}
                        </span>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {g.tags?.map((t: string) => (
                        <Badge key={t} variant="outline" className="text-[10px]">
                          {t}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-sm">agent traces for this session</h2>
            <span className="text-[11px] text-ink-muted">{traces.length} events</span>
          </div>
          <div className="space-y-2 max-h-[900px] overflow-y-auto thin-scroll pr-1">
            {traces.length === 0 && (
              <div className="text-center text-xs text-ink-muted py-8">no traces yet</div>
            )}
            {traces.map((t) => (
              <TraceRow key={t._id} trace={t} />
            ))}
          </div>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">iMessage (simulated)</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-[500px]">
            {[a, b].map((p, i) => {
              // Typeable iff the session is still collecting first-round replies
              // AND this specific user has not submitted yet.
              const awaitingReplies =
                session.state === "awaiting_first_response" ||
                session.state === "awaiting_second_response";
              const thisPending = p?.response_state === "pending";
              const canType = awaitingReplies && thisPending;

              let disabledReason: string | undefined;
              if (session.state === "resolved" || session.state === "closed") {
                disabledReason =
                  "session resolved. no further replies processed.";
              } else if (!awaitingReplies) {
                disabledReason =
                  "session resolving. no further replies processed.";
              } else if (!thisPending) {
                disabledReason =
                  "already submitted. waiting on the other side.";
              }

              return p?.user ? (
                <IMessageChat
                  key={p.user_id}
                  userId={p.user_id}
                  userName={p.user.name}
                  userColor={p.user.avatar_color}
                  disabled={!canType}
                  disabledReason={disabledReason}
                />
              ) : (
                <div key={i} className="text-sm text-ink-muted p-4">no user data</div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function DebriefPanel({ p }: { p: Participant | undefined }) {
  if (!p) return null;
  const user = p.user;
  return (
    <div className="rounded-md border border-line bg-white p-4">
      <div className="flex items-center gap-2">
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-semibold"
          style={{ backgroundColor: user?.avatar_color ?? "#A3A3A3" }}
        >
          {user ? initials(user.name) : "?"}
        </div>
        <div className="leading-tight">
          <div className="font-semibold text-sm">{user?.name ?? p.user_id}</div>
          <div className="text-[11px] text-ink-muted">
            {user?.year} {user?.pronouns}
          </div>
        </div>
        <div className="ml-auto">
          <Badge
            variant={
              p.response_state === "revealed"
                ? "success"
                : p.response_state === "submitted"
                  ? "info"
                  : "warning"
            }
          >
            {p.response_state}
          </Badge>
        </div>
      </div>
      {user?.profile?.persona_summary && (
        <div className="text-[11px] text-ink-muted italic mt-2 leading-snug">
          {user.profile.persona_summary}
        </div>
      )}
      {p.response_state === "pending" && (
        <div className="mt-3 text-xs text-ink-muted">waiting on their reply</div>
      )}
      {p.response_state !== "pending" && (
        <>
          <div className="mt-3 flex items-center gap-2">
            {p.choice && (
              <Badge variant={choiceVariant(p.choice)} className="text-xs">
                {p.choice}
              </Badge>
            )}
            <div className="text-xs text-ink-muted">
              interest{" "}
              <span className="font-mono tabular-nums text-ink">
                {p.interest_level ?? "?"}/10
              </span>
            </div>
            <div className="text-xs text-ink-muted">
              submitted {formatRelative(p.submitted_at)}
            </div>
          </div>
          {p.memorable_moments.length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] uppercase tracking-wider text-ink-muted mb-1">
                memorable moments
              </div>
              <ul className="text-xs text-ink space-y-0.5">
                {p.memorable_moments.map((m, i) => (
                  <li key={i} className="flex gap-1.5">
                    <span className="text-accent">·</span>
                    <span>{m}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {p.concerns.length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] uppercase tracking-wider text-ink-muted mb-1">
                concerns
              </div>
              <ul className="text-xs text-ink space-y-0.5">
                {p.concerns.map((m, i) => (
                  <li key={i} className="flex gap-1.5">
                    <span className="text-warning">·</span>
                    <span>{m}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {p.raw_reply_text && (
            <div className="mt-3">
              <div className="text-[10px] uppercase tracking-wider text-ink-muted mb-1">
                raw reply
              </div>
              <div className="text-xs text-ink italic leading-snug bg-bg-subtle rounded p-2 border border-line">
                {p.raw_reply_text}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function choiceVariant(choice: string): "success" | "info" | "default" {
  if (choice === "again") return "success";
  if (choice === "group") return "info";
  return "default";
}
