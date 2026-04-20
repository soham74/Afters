"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Radio, RefreshCcw } from "lucide-react";
import { Button } from "./ui/button";
import { api } from "@/lib/api";

const SCENARIOS = [
  { name: "both_again", label: "Both Again" },
  { name: "both_group", label: "Both Group" },
  { name: "both_pass", label: "Both Pass" },
  { name: "asymmetric_again_pass", label: "Asymmetric: Again vs Pass" },
  { name: "asymmetric_again_group", label: "Asymmetric: Again vs Group" },
  { name: "timeout", label: "Timeout" },
];

export function ScenarioButtons() {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);

  async function trigger(name: string, label: string) {
    if (busy) return;
    setBusy(name);
    setLastResult(null);
    try {
      const result = await api.triggerScenario(name);
      if (result?.session_id) {
        setLastResult(`${label} triggered. session ${result.session_id.slice(-6)}.`);
        router.push(`/sessions/${result.session_id}`);
      } else {
        setLastResult(`${label} triggered.`);
      }
    } catch (err: any) {
      setLastResult(`error: ${err?.message ?? "unknown"}`);
    } finally {
      setBusy(null);
      router.refresh();
    }
  }

  async function reset() {
    if (busy) return;
    setBusy("reset");
    setLastResult(null);
    try {
      const result = await api.resetDemo();
      setLastResult(
        `reset complete. ${result?.users ?? "?"} users, ${result?.historical_sessions ?? "?"} historical sessions.`,
      );
      router.refresh();
    } catch (err: any) {
      setLastResult(`error: ${err?.message ?? "unknown"}`);
    } finally {
      setBusy(null);
    }
  }

  async function startLive() {
    if (busy) return;
    setBusy("live");
    setLastResult(null);
    try {
      const result = await api.startLiveSession();
      if (result?.session_id) {
        const pair = Array.isArray(result.pair)
          ? result.pair.join(" + ")
          : "new pair";
        setLastResult(
          `live session opened with ${pair} at ${result.campus}. type in either chat pane to drive it.`,
        );
        router.push(`/sessions/${result.session_id}`);
      }
    } catch (err: any) {
      setLastResult(`error: ${err?.message ?? "unknown"}`);
    } finally {
      setBusy(null);
      router.refresh();
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        {SCENARIOS.map((s) => (
          <Button
            key={s.name}
            variant="accent"
            size="sm"
            disabled={busy != null}
            onClick={() => trigger(s.name, s.label)}
          >
            {busy === s.name && (
              <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
            )}
            {s.label}
          </Button>
        ))}
        <Button
          variant="outline"
          size="sm"
          className="border-success text-success hover:bg-success/10 hover:text-success"
          disabled={busy != null}
          onClick={startLive}
          title="picks two free same-campus users and opens a blank session you drive by typing into either chat pane"
        >
          {busy === "live" ? (
            <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
          ) : (
            <Radio className="w-3.5 h-3.5 mr-1.5" />
          )}
          Start live session
        </Button>
        <div className="flex-1" />
        <Button
          variant="outline"
          size="sm"
          disabled={busy != null}
          onClick={reset}
        >
          {busy === "reset" ? (
            <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
          ) : (
            <RefreshCcw className="w-3.5 h-3.5 mr-1.5" />
          )}
          Reset demo data
        </Button>
      </div>
      <div className="text-[11px] text-ink-faint px-1 leading-snug">
        live mode: pick a fresh pair, type their replies yourself. if no one
        responds within 4 minutes the session resolves to{" "}
        <span className="font-mono">timed_out</span> (simulated ghosting).
        in production the real timeout is 48 hours.
      </div>
      {lastResult && (
        <div className="text-xs text-ink-muted px-1 font-mono">{lastResult}</div>
      )}
    </div>
  );
}
