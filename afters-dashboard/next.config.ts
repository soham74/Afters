import type { NextConfig } from "next";
import path from "node:path";

// Monorepo root. next/dev sniffs upward looking for a lockfile and sometimes
// finds a stray package-lock.json in a parent directory (like ~). Pinning the
// tracing root here makes that inference deterministic.
const monorepoRoot = path.resolve(process.cwd(), "..");

const config: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["afters-shared"],
  typedRoutes: false,
  // Standalone output: produces .next/standalone with a self-contained
  // server.js + minimal node_modules so the Docker runtime stage stays small.
  // outputFileTracingRoot tells Next where the monorepo root is so workspace
  // deps (afters-shared) get traced into the standalone bundle correctly.
  output: "standalone",
  outputFileTracingRoot: monorepoRoot,
  env: {
    NEXT_PUBLIC_ORCHESTRATOR_BASE_URL:
      process.env.NEXT_PUBLIC_ORCHESTRATOR_BASE_URL ?? "http://localhost:8000",
    NEXT_PUBLIC_MESSAGING_BASE_URL:
      process.env.NEXT_PUBLIC_MESSAGING_BASE_URL ?? "http://localhost:3001",
  },
};

export default config;
