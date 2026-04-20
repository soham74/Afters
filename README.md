# Afters

**Afters** is Ditto's post-date mutual-reveal flow. After two users go on a Ditto first date, both get a short prompt asking what they want next. Three choices, one rule: neither side sees the other's answer until both have answered. The system then routes the pair into a second date, a group hang, a dignified close, or an asymmetric handling with a human-reviewed closure message.

This repo is a take-home for the Ditto Product Engineer Intern role. The hero surface is the internal tools dashboard, not the iMessage side (which is simulated). Every moving part was chosen so it reads cleanly in a five-minute video.

## Watch the demo

Open the dashboard at `http://localhost:3000/sessions`. Six buttons up top, labeled exactly as written below. Each is a one-click scripted run that drives the full flow end to end while you watch traces land in real time.

- **Both Again**: the happy path. Debrief Intake (haiku) extracts both debriefs, Mutual Reveal Gate resolves `both_again`, Venue Agent (sonnet, RAG over seeded venues) ranks 3 picks, Scheduler proposes 3 slots, confirmation message lands in each user's iMessage pane.
- **Both Group**: rule-based batcher queues the pair for a group hang.
- **Asymmetric: Again vs Pass**: Closure Agent drafts a dignified message, routed to the human-in-the-loop review queue on the session detail page. Approve / edit / reject, with one regeneration budget and a deterministic fallback on the second reject.
- **Asymmetric: Again vs Group**: same closure flow, plus the Again party is offered a group reroute.
- **Timeout**: only one user replies. After `TIMEOUT_SECONDS_OVERRIDE` seconds (default 60) the Timeout Watcher flips the session and sends a soft-close message to the responder.
- **Reset demo data**: wipes sessions, traces, messages, closure reviews, second dates, and the group queue, then re-runs the seed. Users, matches, dates, and venues come back in full.

For the last 30 seconds of the video, open `/experiments` for the static A/B design write-up.

## How this maps to the Ditto JD

Each box below is directly mapped to a Ditto responsibility listed in the role.

| Responsibility | Where to look |
| --- | --- |
| **Agent orchestration** | `afters-orchestrator/afters/graph/machine.py` (LangGraph state machine, 5 outcome branches, deterministic Mutual Reveal Gate upstream). Every node writes an `agent_trace` row tagged with `kind`. |
| **Feedback loops** | `afters-orchestrator/afters/agents/scoring_agent.py` updates match compatibility after every resolved session and appends a learning-to-rank row to `feedback_training.jsonl`. `/metrics` surfaces "model signal density" over those rows. |
| **Stateful systems** | `afters-orchestrator/afters/db/mongo.py` + `redis_client.py`. MongoDB holds sessions, messages, traces, second dates, group queue, closure reviews. Redis Streams (`afters:events`) carries every state transition; Redis pub-sub (`afters:chat:{userId}`) carries chat deliveries. |
| **Internal tools** | `afters-dashboard/`. Sessions table, Session Detail with the SVG state graph + side-by-side structured debriefs + per-session trace firehose + closure review approve/edit/reject, Agent Traces firehose with latency histogram and running cost, Metrics tiles plus 14-day timeseries, iMessage-styled chat pane per user. |
| **Ranking systems** | `feedback_training.jsonl` accumulates one row per resolved session (pre-score, outcome, interest levels, venue tags, time-to-resolution, label). `/metrics` shows the row count live. Training a real ranker is intentionally out of scope; the evidence of the data path is what matters here. |
| **A/B testing** | `/experiments` page. Primary metric, guardrail, sample size math, per-campus rollout, risks + mitigations. Static write-up, rendered inside the dashboard so it travels with the prototype. |
| **Evaluation** | `afters-orchestrator/evals/`. 20 hand-labeled examples covering interested / uninterested / group-intent / ambiguous / voice-note-style / short-text-style inputs. Reports choice accuracy, precision + recall for `wants_second_date` and `willing_to_group_hang`, a confusion matrix, and cumulative latency. |

## Stack, and why

- **Next.js 15 App Router + Tailwind + hand-authored shadcn-style primitives** for the dashboard. Server components where they help, client components where we need polling. No component library ceremony: every primitive is in `components/ui/*` and fits on one screen.
- **FastAPI + LangGraph + Pydantic** for the orchestrator. FastAPI gives us ergonomic async endpoints; LangGraph models the post-reveal fan-out (the interesting agent-orchestration surface); Pydantic gives us structured Anthropic tool-use outputs that round-trip into Mongo without a custom serializer. Mutual Reveal Gate is *intentionally not inside the graph*: it is a deterministic prerequisite, and keeping it outside makes the LangGraph visualization on the dashboard show the interesting part.
- **NestJS** for the messaging service. A small surface (send, reply, thread) but the split is load-bearing on camera: orchestration is Python, delivery is TypeScript, the dashboard talks to both, and the one webhook from NestJS into the orchestrator is where a real iMessage integration would drop in.
- **MongoDB + Redis Streams + Redis pub-sub**. Mongo is the source of truth; Redis Streams give a replayable event log that the Traces view taps for live updates; pub-sub drives per-user chat deliveries.
- **Anthropic SDK** with `claude-sonnet-4-5` for reasoning (Venue Agent, Closure Agent) and `claude-haiku-4-5` for extraction (Debrief Intake). Structured output via tool-use with a Pydantic schema forced as the tool input.
- **Whisper stubbed deterministically.** Swap point is one function (`afters/whisper/stub.py`). The Debrief Intake Agent treats text and voice-note transcripts identically except for a flag in the trace summary.

## Cross-language type sharing

The shared contract is JSON Schema in `afters-shared/schemas/`. TypeScript types in `afters-shared/src/types.ts` are hand-written for DX (one file, ergonomic enums colocated with shapes). Pydantic models in `afters-orchestrator/afters/models.py` are hand-written for the same reason. Both codegen paths exist (`afters-shared/scripts/codegen-ts.ts`, `afters-orchestrator/scripts/codegen_pydantic.py`) so you can diff against the auto-generated output to catch drift. The schemas are the contract; the hand-written models are the ergonomic consumers of the contract.

## Observability in one sentence per line

- Every LLM call, every deterministic agent, and every reviewer action writes exactly one `agent_traces` row.
- Every row has a `summary` field that is a single declarative sentence (for example, "Debrief Intake extracted interest_level 8 and choice=again from Maya's voice note in 420ms using haiku.").
- The Traces view shows all three kinds interleaved with a tag filter, a latency histogram, and a running cost total.
- Every session state change pushes an event onto the `afters:events` Redis Stream for live dashboard updates.
- The Mutual Reveal Gate is a deterministic agent and writes its own trace so the "who chose what resolved to what" step is visible, not implicit.

## Running it

```bash
# bring up Mongo and Redis
pnpm infra:up

# python + node
cd afters-orchestrator && pip install -e .[dev] && cd ..
pnpm install

# seed 12 users, 30 venues, 6 current matches, 30 historical sessions
pnpm seed

# in three terminals (or `pnpm dev` for all three)
pnpm dev:orchestrator    # :8000
pnpm dev:messaging       # :3001
pnpm dev:dashboard       # :3000
```

Open `http://localhost:3000`. Click **Both Again**. Watch the chat animate, watch the state graph advance, watch the traces land.

### Env

Everything needed is in `.env.example`. Copy to `.env` and fill `ANTHROPIC_API_KEY`. Two knobs matter for the demo:

- `TIMEOUT_SECONDS_OVERRIDE=60`. Compresses the 48-hour mutual-reveal timeout so the Timeout scenario fires live. In production this is unset and the 48h default applies.
- `MOCK_LLM=false`. Flip to `true` to run scenarios fully offline against registered mocks (useful if the network is flaky). Real traces still write; the `model` field becomes `mock:claude-*`.

### Evals

```bash
pnpm eval
# or
cd afters-orchestrator && python -m evals.run_evals
```

Runs the 20 hand-labeled Debrief Intake examples. Reports choice accuracy, precision + recall for the two boolean fields, a 3x3 confusion matrix, and latency.

## Repository layout

```
afters/
├── afters-shared/            # JSON Schema single source of truth
│   ├── schemas/              # shared contracts (AftersSession, Trace, ...)
│   └── src/                  # hand-written TypeScript types and brand constants
├── afters-orchestrator/      # FastAPI + LangGraph (Python 3.12)
│   ├── afters/
│   │   ├── agents/           # Debrief Intake, Venue, Scheduler, Closure, Scoring, Group Batcher
│   │   ├── graph/            # LangGraph state machine
│   │   ├── services/         # session service, closure service, scenario runner
│   │   ├── api/              # FastAPI routers
│   │   ├── db/               # mongo + redis
│   │   ├── llm/              # Anthropic wrapper + tracing + MOCK_LLM registry
│   │   └── whisper/          # deterministic stub
│   ├── evals/                # 20-example harness for Debrief Intake
│   ├── scripts/              # seed.py, run_scenario.py, codegen_pydantic.py
│   └── feedback_training.jsonl
├── afters-messaging/         # NestJS 10 (TypeScript)
│   └── src/messages/         # send / reply / thread; webhook into orchestrator
├── afters-dashboard/         # Next.js 15 App Router (TypeScript)
│   ├── app/                  # sessions, sessions/[id], chats, chats/[userId], traces, metrics, experiments
│   ├── components/           # state-graph, imessage-chat, trace-row, scenario-buttons, ...
│   └── lib/                  # api client, formatters, brand tokens
├── docker-compose.yml        # Mongo 7 + Redis 7 (app services behind --profile all)
├── package.json              # pnpm workspace root, top-level dev scripts
├── pnpm-workspace.yaml
└── .env.example
```

## Deliberate tradeoffs

- **LangGraph starts at the Mutual Reveal Gate.** The gate runs in a plain FastAPI service method and the graph picks up on `outcome`. Alternative: put the gate inside the graph and use LangGraph's checkpointer to resume across user replies. Rejected because the pause/resume machinery would add more code than it clarifies for a five-minute video. The post-reveal fan-out is where agent orchestration gets interesting, so that is what the graph shows.
- **Tag-intersection retrieval in the Venue Agent, not embeddings.** Deterministic in the demo, zero extra infra, and the story on camera ("retrieval is rule-based so the LLM is doing ranking and reasoning only, not search") is cleaner.
- **Scheduling is deterministic, not an agent.** Calendar-intersection is a mock over `DEFAULT_HOURS` and `DEFAULT_WEEKDAYS`. The swap point for a real availability service is a single function.
- **Closure Agent goes through a human-in-the-loop queue.** Not auto-sent. One regeneration allowed; second reject falls back to a deterministic "hope it went well" template. Every reviewer action writes an `agent_trace` of `kind=human_feedback` so the observability story covers human loops, not just LLM traffic.
- **Hand-written models on both sides of the cross-language boundary.** DX wins for both TypeScript and Pydantic consumers. The codegen scripts exist for drift detection, not runtime generation. JSON Schema is the contract.
- **30 historical sessions seeded.** The Metrics tiles open at realistic numbers instead of zero. Outcome mix is tuned to hit a ~90% resolved-within-24h rate and ~10% ghost rate out of the box.

## What is deliberately not built

- No real authentication. No real Twilio / Sendblue / iMessage integration. No real calendaring. No real ML training; the `feedback_training.jsonl` rows exist to show the data path.
- No profile creation or matching algorithm. Matches and first dates are seeded; Afters runs strictly post-date.
- No mobile app and no analytics pipeline. `/metrics` is computed on demand from Mongo + the feedback file.
- No event streaming client library. The dashboard polls at 1 to 3 second intervals; it is enough for the demo and keeps the code on the screen.

## Author

Built by Soham Kolhe for the Ditto Product Engineer Intern role. Questions or feedback: `sohamkolhe@outlook.com`.
