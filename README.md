# Afters

Afters is the post-date follow-up flow for Ditto. After two users go on a Ditto first date, both get a short text asking how it went. They each pick one of three things: **Again** (want another date), **Group** (lower stakes group hang), or **Pass** (no thanks). Neither side sees the other's choice until both have replied. The system then books a second date, queues them for a group event, sends a soft close, or handles the awkward case where one wanted more and the other did not.

This is a take-home for the Ditto Product Engineer Intern role. The dashboard is the main thing reviewers should look at; iMessage is simulated.

## Try it

Open `http://localhost:3000/sessions`. Seven buttons at the top:

- **Both Again** — happy path. Picks a venue, schedules a time, sends both users a confirmation.
- **Both Group** — both go into the group queue.
- **Both Pass** — silent close, both get a friendly acknowledgment.
- **Asymmetric: Again vs Pass** — Closure Agent drafts a kind message for the Again user. You approve, edit, or reject it.
- **Asymmetric: Again vs Group** — same closure flow, plus the Again user is offered a group reroute.
- **Timeout** — only one user replies. After 4 minutes the session times out.
- **Start live session** — opens an empty session you drive yourself by typing into the chat panes.
- **Reset demo data** — wipes everything and re-runs the seed.

Click any of them and watch the chat fill in, the state graph advance, and the agent traces show up on the right.

## Stack

- **Dashboard** — Next.js 15, Tailwind, custom UI primitives.
- **Orchestrator** — Python (FastAPI) with LangGraph for the post-reveal branching, Pydantic for typed Anthropic outputs.
- **Messaging** — NestJS service that fakes iMessage send/receive.
- **Database** — MongoDB. Redis Streams for live event updates, Redis pub/sub for chat delivery.
- **Models** — Anthropic Claude Sonnet 4.5 for the Venue and Closure agents, Haiku 4.5 for Debrief Intake. Voice notes are stubbed.

## How to run

```bash
# Mongo + Redis
pnpm infra:up

# install
cd afters-orchestrator && pip install -e .[dev] && cd ..
pnpm install

# seed users, venues, and 30 historical sessions
pnpm seed

# all three services in one go
pnpm dev
```

Open `http://localhost:3000`, click **Both Again**.

### Env vars

Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`. Two other knobs:

- `TIMEOUT_SECONDS_OVERRIDE=240` — shrinks the real 48-hour timeout to 4 minutes for the demo.
- `MOCK_LLM=false` — flip to `true` to run scenarios offline against canned outputs.

### Eval harness

```bash
pnpm eval
```

Runs the Debrief Intake agent against 20 hand-labeled examples. Reports choice accuracy, precision, and recall.

## What's in the repo

```
afters/
├── afters-shared/         shared JSON Schemas + TypeScript types
├── afters-orchestrator/   Python: agents, graph, services, evals, seed
├── afters-messaging/      NestJS: fake iMessage layer
├── afters-dashboard/      Next.js dashboard (the demo surface)
└── docker-compose.yml     Mongo + Redis
```

## What it does

- Every agent call writes one row to `agent_traces`. Traces page shows them all with cost and latency.
- Every state change pushes an event to a Redis Stream so the dashboard updates live.
- Every resolved session writes a row to `feedback_training.jsonl`. Real training is not in scope, but the data path is there.
- Closure Agent messages go through a human review queue (approve / edit / reject). Reviewer actions are logged as traces too.

## What's not built

No real auth, no real iMessage integration, no real calendar. No matching algorithm — matches and first dates are seeded. No mobile app. No real ML training. The scope is strictly post-date.

## Author

Soham Kolhe — sohamkolhe@outlook.com
