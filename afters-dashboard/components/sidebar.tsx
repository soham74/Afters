"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutGrid,
  MessageSquare,
  Activity,
  BarChart3,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/sessions", label: "Sessions", icon: LayoutGrid },
  { href: "/chats", label: "Chats", icon: MessageSquare },
  { href: "/traces", label: "Agent Traces", icon: Activity },
  { href: "/metrics", label: "Metrics", icon: BarChart3 },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-56 shrink-0 border-r border-line bg-white flex flex-col">
      <div className="px-5 pt-6 pb-5 border-b border-line">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-md bg-accent flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="font-semibold text-sm tracking-tight">Afters</div>
            <div className="text-[11px] text-ink-muted leading-none mt-0.5">
              Ditto post-date console
            </div>
          </div>
        </div>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {NAV.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                active
                  ? "bg-accent-soft text-accent-deep"
                  : "text-ink hover:bg-bg-subtle",
              )}
            >
              <Icon className={cn("w-4 h-4", active && "text-accent")} />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-3 border-t border-line">
        <div className="px-3 py-2 text-[11px] text-ink-muted">
          <div>internal tools</div>
          <div className="mt-0.5 font-mono text-[10px]">v0.1.0</div>
        </div>
      </div>
    </aside>
  );
}
