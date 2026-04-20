"use client";

import { useEffect, useRef, useState } from "react";
import { Lock, Send } from "lucide-react";
import { api, messaging } from "@/lib/api";
import { formatTime, initials } from "@/lib/format";
import { cn } from "@/lib/utils";

interface Message {
  _id: string;
  user_id: string;
  direction: "inbound" | "outbound";
  body: string;
  kind: "text" | "voice_note" | "card";
  card_meta?: any;
  session_id?: string | null;
  created_at: string;
}

interface User {
  _id: string;
  name: string;
  avatar_color: string;
}

export function IMessageChat({
  userId,
  userName,
  userColor,
  sessionId,
  disabled = false,
  disabledReason,
  pollMs = 1000,
}: {
  userId: string;
  userName?: string;
  userColor?: string;
  sessionId?: string;
  disabled?: boolean;
  disabledReason?: string;
  pollMs?: number;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let stop = false;
    async function tick() {
      try {
        const rows = await api.thread(userId, sessionId);
        if (!stop) setMessages(rows);
      } catch {
        // ignore, retry next tick
      }
    }
    tick();
    const t = setInterval(tick, pollMs);
    return () => {
      stop = true;
      clearInterval(t);
    };
  }, [userId, sessionId, pollMs]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  async function send() {
    if (!draft.trim() || sending || disabled) return;
    const body = draft.trim();
    setDraft("");
    setSending(true);
    setSendError(null);
    try {
      await messaging.reply({ user_id: userId, body });
    } catch (err: any) {
      const msg = String(err?.message ?? "send failed");
      setSendError(
        msg.includes("409")
          ? "session not accepting replies."
          : "send failed. try again.",
      );
      setDraft(body);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex flex-col h-full bg-[#F7F7F8] rounded-lg border border-line overflow-hidden">
      <header className="flex items-center gap-2.5 px-4 py-3 border-b border-line bg-white">
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-semibold"
          style={{ backgroundColor: userColor ?? "#A3A3A3" }}
        >
          {userName ? initials(userName) : "?"}
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold">{userName ?? userId}</div>
          <div className="text-[11px] text-ink-muted">iMessage (simulated)</div>
        </div>
      </header>
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto thin-scroll px-3 py-4 space-y-2"
      >
        {messages.length === 0 && (
          <div className="text-center text-xs text-ink-muted py-12">
            no messages yet. trigger a scenario to populate this thread.
          </div>
        )}
        {messages.map((m) => (
          <div key={m._id} className="flex w-full">
            {m.kind === "card" && m.card_meta?.kind === "second_date_offer" ? (
              <div className="bubble-card text-sm w-full">
                <div className="text-[11px] uppercase tracking-wider text-ink-muted mb-1">
                  second date offer
                </div>
                <div className="font-semibold text-ink text-sm leading-tight">
                  {m.card_meta.venue_name}
                </div>
                <div className="text-xs text-ink-muted mt-0.5">
                  {m.card_meta.venue_address}
                </div>
                <div className="text-xs text-ink mt-2">
                  {new Date(m.card_meta.proposed_time).toLocaleString([], {
                    weekday: "short",
                    month: "short",
                    day: "numeric",
                    hour: "numeric",
                    minute: "2-digit",
                  })}
                </div>
                <div className="mt-2 pt-2 border-t border-line text-xs leading-snug text-ink">
                  {m.body}
                </div>
              </div>
            ) : (
              <div
                className={cn(
                  "bubble text-sm",
                  m.direction === "outbound"
                    ? "bubble-outbound"
                    : "bubble-inbound",
                  m.kind === "voice_note" && "italic",
                )}
                title={formatTime(m.created_at)}
              >
                {m.kind === "voice_note" && "[voice note] "}
                {m.body}
              </div>
            )}
          </div>
        ))}
      </div>
      {disabled ? (
        <div className="flex items-center justify-center gap-2 px-4 py-4 border-t border-line bg-bg-subtle text-xs text-ink-muted italic">
          <Lock className="w-3 h-3" />
          <span>{disabledReason ?? "chat disabled."}</span>
        </div>
      ) : (
        <>
          {sendError && (
            <div className="px-4 py-2 border-t border-line bg-danger/5 text-[11px] text-danger">
              {sendError}
            </div>
          )}
          <form
            className="flex items-center gap-2 px-3 py-3 border-t border-line bg-white"
            onSubmit={(e) => {
              e.preventDefault();
              send();
            }}
          >
            <input
              className="flex-1 h-9 px-3 rounded-full border border-line bg-[#F4F4F5] text-sm focus:outline-none focus:border-accent"
              placeholder={`iMessage ${userName?.split(" ")[0] ?? ""}`.trim()}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              disabled={sending}
            />
            <button
              type="submit"
              className="w-9 h-9 rounded-full bg-imessage-blue text-white flex items-center justify-center disabled:opacity-50"
              disabled={!draft.trim() || sending}
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </>
      )}
    </div>
  );
}
