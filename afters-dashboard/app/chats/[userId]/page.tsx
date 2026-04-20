"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import { IMessageChat } from "@/components/imessage-chat";

interface User {
  _id: string;
  name: string;
  avatar_color: string;
  campus: string;
  year: string;
  pronouns: string;
  profile: { persona_summary: string; interests: string[] };
}

export default function ChatPage({
  params,
}: {
  params: Promise<{ userId: string }>;
}) {
  const { userId } = use(params);
  const [user, setUser] = useState<User | null>(null);
  const [activeSession, setActiveSession] = useState<any>(null);

  useEffect(() => {
    api.getUser(userId).then(setUser).catch(() => {});
  }, [userId]);

  useEffect(() => {
    let stop = false;
    async function tick() {
      try {
        const s = await api.getActiveSession(userId);
        if (!stop) setActiveSession(s);
      } catch {}
    }
    tick();
    const t = setInterval(tick, 2000);
    return () => {
      stop = true;
      clearInterval(t);
    };
  }, [userId]);

  const participant = activeSession?.participants?.find(
    (p: any) => p.user_id === userId,
  );
  const awaitingReplies =
    activeSession?.state === "awaiting_first_response" ||
    activeSession?.state === "awaiting_second_response";
  const thisPending = participant?.response_state === "pending";
  const canType = Boolean(activeSession && awaitingReplies && thisPending);

  let disabledReason: string | undefined;
  if (!activeSession) {
    disabledReason =
      "no active session. use 'start live session' from sessions to open one.";
  } else if (!awaitingReplies) {
    disabledReason = "session resolved. no further replies processed.";
  } else if (!thisPending) {
    disabledReason = "already submitted. waiting on the other side.";
  }
  const disabled = !canType;

  return (
    <div className="p-8 space-y-6 max-w-[1400px]">
      <Link
        href="/chats"
        className="text-xs text-ink-muted hover:text-ink flex items-center gap-1"
      >
        <ArrowLeft className="w-3 h-3" /> back to threads
      </Link>
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
        <div className="h-[72vh]">
          <IMessageChat
            userId={userId}
            userName={user?.name}
            userColor={user?.avatar_color}
            disabled={disabled}
            disabledReason={disabledReason}
          />
        </div>
        {user && (
          <aside className="space-y-3 text-sm">
            <div className="flex items-center gap-3">
              <div
                className="w-11 h-11 rounded-full flex items-center justify-center text-white font-semibold"
                style={{ backgroundColor: user.avatar_color }}
              >
                {user.name
                  .split(/\s+/)
                  .map((s) => s.charAt(0))
                  .slice(0, 2)
                  .join("")
                  .toUpperCase()}
              </div>
              <div>
                <div className="font-semibold">{user.name}</div>
                <div className="text-xs text-ink-muted">
                  {user.year} · {user.pronouns} · {user.campus}
                </div>
              </div>
            </div>
            <div className="text-xs text-ink-muted leading-snug">
              {user.profile?.persona_summary}
            </div>
            <div className="flex flex-wrap gap-1">
              {user.profile?.interests?.map((i) => (
                <span
                  key={i}
                  className="text-[10px] bg-bg-subtle border border-line rounded-full px-2 py-0.5"
                >
                  {i}
                </span>
              ))}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
