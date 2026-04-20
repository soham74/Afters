"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Bot, Wrench, User2 } from "lucide-react";
import { Badge } from "./ui/badge";
import { formatCost, formatRelative } from "@/lib/format";
import { cn } from "@/lib/utils";

const KIND_ICON: Record<string, typeof Bot> = {
  llm: Bot,
  deterministic: Wrench,
  human_feedback: User2,
};

const KIND_VARIANT: Record<
  string,
  "accent" | "info" | "success"
> = {
  llm: "accent",
  deterministic: "info",
  human_feedback: "success",
};

export interface Trace {
  _id: string;
  session_id: string | null;
  agent_name: string;
  kind: "llm" | "deterministic" | "human_feedback";
  model: string | null;
  input_summary: string;
  prompt: string | null;
  output: any;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  latency_ms: number;
  summary: string;
  tags: string[];
  created_at: string;
}

export function TraceRow({ trace, defaultOpen = false }: { trace: Trace; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const Icon = KIND_ICON[trace.kind] ?? Bot;
  return (
    <div className="border border-line rounded-md bg-white">
      <button
        className="w-full flex items-start gap-3 px-3 py-2.5 text-left hover:bg-bg-subtle transition-colors"
        onClick={() => setOpen((o) => !o)}
      >
        <div className="mt-0.5">
          {open ? (
            <ChevronDown className="w-3.5 h-3.5 text-ink-muted" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-ink-muted" />
          )}
        </div>
        <div className="mt-0.5">
          <Icon className="w-4 h-4 text-ink-muted" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-sm">{trace.agent_name}</span>
            <Badge variant={KIND_VARIANT[trace.kind]} className="text-[10px]">
              {trace.kind}
            </Badge>
            {trace.model && (
              <span className="text-[11px] text-ink-muted font-mono">
                {trace.model}
              </span>
            )}
            <span className="text-[11px] text-ink-muted">
              {trace.latency_ms}ms
            </span>
            {trace.cost_usd > 0 && (
              <span className="text-[11px] text-ink-muted">
                {formatCost(trace.cost_usd)}
              </span>
            )}
            {trace.tokens_in + trace.tokens_out > 0 && (
              <span className="text-[11px] text-ink-muted">
                {trace.tokens_in}+{trace.tokens_out} tok
              </span>
            )}
            <span className="text-[11px] text-ink-faint ml-auto">
              {formatRelative(trace.created_at)}
            </span>
          </div>
          <div className={cn("text-sm text-ink mt-0.5 leading-snug", !open && "truncate")}>
            {trace.summary}
          </div>
        </div>
      </button>
      {open && (
        <div className="border-t border-line px-3 py-3 bg-bg-subtle/60 space-y-3 text-xs">
          <div>
            <div className="font-semibold text-ink-muted uppercase tracking-wider text-[10px] mb-1">
              Input
            </div>
            <div className="font-mono text-ink">{trace.input_summary}</div>
          </div>
          {trace.prompt && (
            <div>
              <div className="font-semibold text-ink-muted uppercase tracking-wider text-[10px] mb-1">
                Prompt
              </div>
              <pre className="font-mono text-[11px] text-ink whitespace-pre-wrap bg-white border border-line rounded p-2 max-h-64 overflow-auto thin-scroll">
                {trace.prompt}
              </pre>
            </div>
          )}
          {trace.output != null && (
            <div>
              <div className="font-semibold text-ink-muted uppercase tracking-wider text-[10px] mb-1">
                Output
              </div>
              <pre className="font-mono text-[11px] text-ink whitespace-pre-wrap bg-white border border-line rounded p-2 max-h-64 overflow-auto thin-scroll">
                {typeof trace.output === "string"
                  ? trace.output
                  : JSON.stringify(trace.output, null, 2)}
              </pre>
            </div>
          )}
          {trace.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {trace.tags.map((t) => (
                <Badge key={t} variant="outline" className="text-[10px]">
                  {t}
                </Badge>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
