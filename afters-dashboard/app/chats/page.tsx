"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { MessageSquare } from "lucide-react";
import { api, messaging } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { formatRelative, initials } from "@/lib/format";

interface User {
  _id: string;
  name: string;
  campus: string;
  avatar_color: string;
}

export default function ChatsPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [threads, setThreads] = useState<Record<string, string>>({});

  useEffect(() => {
    let stop = false;
    async function tick() {
      try {
        const [us, ts] = await Promise.all([api.listUsers(), messaging.threads()]);
        if (stop) return;
        setUsers(us as User[]);
        const map: Record<string, string> = {};
        for (const t of ts) map[t.user_id] = t.last_at;
        setThreads(map);
      } catch {}
    }
    tick();
    const i = setInterval(tick, 2000);
    return () => {
      stop = true;
      clearInterval(i);
    };
  }, []);

  // Only surface users who actually have a thread. Seeded users with no
  // message history read as noise in this view, and the reviewer can always
  // trigger a scenario or "Start live session" to populate one.
  const withActivity = users
    .map((u) => ({ ...u, last_at: threads[u._id] }))
    .filter((u) => Boolean(u.last_at))
    .sort((a, b) => (b.last_at ?? "").localeCompare(a.last_at ?? ""));

  const hiddenCount = users.length - withActivity.length;

  return (
    <div className="p-8 space-y-6 max-w-[1600px]">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Chats</h1>
        <p className="text-sm text-ink-muted mt-1">
          per-user iMessage threads. open one to watch scenario replies land and type your own.
        </p>
      </header>
      <Card>
        <CardContent className="p-0">
          <ul className="divide-y divide-line">
            {withActivity.map((u) => (
              <li key={u._id}>
                <Link
                  href={`/chats/${u._id}`}
                  className="flex items-center gap-3 px-5 py-3.5 hover:bg-bg-subtle transition-colors"
                >
                  <div
                    className="w-9 h-9 rounded-full flex items-center justify-center text-white text-xs font-semibold"
                    style={{ backgroundColor: u.avatar_color }}
                  >
                    {initials(u.name)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <div className="font-semibold text-sm">{u.name}</div>
                      <span className="text-[11px] text-ink-muted">{u.campus}</span>
                    </div>
                    <div className="text-xs text-ink-muted mt-0.5">
                      {u.last_at ? (
                        <>last message {formatRelative(u.last_at)}</>
                      ) : (
                        <>no messages yet</>
                      )}
                    </div>
                  </div>
                  <MessageSquare className="w-4 h-4 text-ink-faint" />
                </Link>
              </li>
            ))}
            {users.length === 0 && (
              <li className="px-5 py-8 text-center text-sm text-ink-muted">
                no users seeded. run <code className="font-mono text-xs">pnpm seed</code>.
              </li>
            )}
            {users.length > 0 && withActivity.length === 0 && (
              <li className="px-5 py-8 text-center text-sm text-ink-muted">
                no threads yet. trigger a scenario or use &ldquo;start live
                session&rdquo; from the sessions page.
              </li>
            )}
          </ul>
        </CardContent>
      </Card>
      {hiddenCount > 0 && (
        <div className="text-[11px] text-ink-faint px-1">
          {hiddenCount} seeded user{hiddenCount === 1 ? "" : "s"} hidden (no
          messages yet). they will appear here once a session is opened for
          them.
        </div>
      )}
    </div>
  );
}
