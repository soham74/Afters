import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function ExperimentsPage() {
  return (
    <div className="p-8 space-y-6 max-w-[1100px]">
      <header>
        <div className="text-xs text-ink-muted uppercase tracking-wider font-medium mb-1">
          A/B test design
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Afters vs. self-organized post-date follow-up
        </h1>
        <p className="text-sm text-ink-muted mt-2 max-w-2xl leading-relaxed">
          the write-up the team would review before turning on routing traffic. this page is
          deliberately static: no live experimentation infra, just the thinking.
        </p>
      </header>

      <Section
        title="Hypothesis"
        kicker="why ship this"
        body={
          <>
            post-date users routed through afters will resolve their post-date intent
            (second date booked, group queue, or a clean close) within 24 hours at a
            materially higher rate than users left to self-organize over iMessage with no
            scaffolding. we expect a lift in the primary metric large enough to absorb the
            cost of the extra agent runtime.
          </>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Section
          title="Primary metric"
          kicker="decide on this alone"
          body={
            <>
              resolved-date rate within 24 hours of date completion. target: +15pp lift over
              the ~42% baseline estimated from pre-Afters ghost data.
            </>
          }
        />
        <Section
          title="Guardrail"
          kicker="stop if this moves"
          body={
            <>
              first-date attendance rate in the following week. stop rule: a sustained
              drop of more than 3pp for 5 consecutive days. we will not let post-date
              friction discourage next-week attendance.
            </>
          }
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Secondary metrics</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <Row label="second-date conversion" body="sessions ending both_again with a confirmed second-date booking." />
          <Row label="group acceptance" body="sessions ending both_group and matched into a group event within 7 days." />
          <Row label="ghost rate (directional)" body="sessions that time out without both responses. flagged directional, not primary, to avoid selection-bias interaction with user follow-up behavior." />
          <Row label="closure review health" body="approve / edit / reject distribution on the human-in-the-loop queue. tracked for drift of the Closure Agent." />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Sample size and duration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-ink leading-relaxed">
          <p>
            baseline: ~42% resolved within 24h. MDE: +10pp absolute. alpha 0.05, power 0.8
            on a one-sided proportion test.
          </p>
          <p>
            at roughly 140 completed-date pairs per campus per week, per-campus power is
            reached in ~3 weeks. we run 4 weeks to capture at least one full
            "second Wednesday" cycle per treated user so the group-acceptance secondary has
            room to land.
          </p>
          <p>
            unit of randomization is the user, not the pair. treatment assignment persists
            for the 4-week experiment window to avoid re-assignment contamination in a
            user's second week.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Per-campus rollout plan</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="space-y-2 text-sm text-ink">
            <RollupRow week="week 1" plan="10% treatment at UC Berkeley (smaller cohort, faster signal)." />
            <RollupRow week="week 2" plan="ramp UC Berkeley to 30%. begin 10% treatment at UC San Diego." />
            <RollupRow week="week 3" plan="both campuses at 50%." />
            <RollupRow week="week 4" plan="both campuses at 100%. full metric read at end of week." />
          </ol>
          <p className="text-xs text-ink-muted mt-3">
            each ramp is gated on the guardrail. if first-date attendance dips more than
            3pp for 5 days, pause and diagnose before ramping.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Known risks and mitigations</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <RiskRow
            risk="Closure Agent quality drift"
            mitigation="human-in-the-loop queue; every reviewer action is logged as an agent_trace of kind=human_feedback and trended weekly. rolling rejection rate above 25% auto-pages the on-call."
          />
          <RiskRow
            risk="Group Batcher sparsity at low-volume campus"
            mitigation="group events need 4 to 6 users with >= 2 overlapping tags. if UC San Diego treatment produces fewer than 4 eligible users in a week, pause Group Batcher at UC San Diego rather than send stale confirmations."
          />
          <RiskRow
            risk="Asymmetric branches produce embarrassing closures"
            mitigation="Closure Agent prompt explicitly forbids quoting the less-interested party verbatim. reject-regenerate budget of 1. second reject falls back to the deterministic template."
          />
          <RiskRow
            risk="Per-user token spend drifts past budget"
            mitigation="sonnet-4-5 only on venue + closure. debrief intake is haiku-4-5. cost trended on /traces in real time; hard cap at $0.25 per resolved session via a pre-call budget check (not shipped in this prototype)."
          />
        </CardContent>
      </Card>
    </div>
  );
}

function Section({
  title,
  kicker,
  body,
}: {
  title: string;
  kicker: string;
  body: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="text-[11px] uppercase tracking-wider text-ink-muted font-medium">
          {kicker}
        </div>
        <CardTitle className="text-sm mt-1">{title}</CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-ink leading-relaxed">{body}</CardContent>
    </Card>
  );
}

function Row({ label, body }: { label: string; body: string }) {
  return (
    <div className="flex gap-3 pb-2 border-b border-line last:border-none last:pb-0">
      <Badge variant="outline" className="shrink-0 mt-0.5 text-[10px]">
        {label}
      </Badge>
      <div className="text-ink leading-relaxed">{body}</div>
    </div>
  );
}

function RollupRow({ week, plan }: { week: string; plan: string }) {
  return (
    <li className="flex gap-3">
      <span className="shrink-0 w-16 text-ink-muted font-mono text-xs pt-0.5">{week}</span>
      <span>{plan}</span>
    </li>
  );
}

function RiskRow({ risk, mitigation }: { risk: string; mitigation: string }) {
  return (
    <div className="rounded-md border border-line p-3 bg-white">
      <div className="font-semibold text-ink">{risk}</div>
      <div className="text-ink-muted mt-1 leading-relaxed text-xs">{mitigation}</div>
    </div>
  );
}
