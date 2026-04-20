import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        accent: {
          DEFAULT: "#FF6B5E",
          soft: "#FFE5E1",
          deep: "#E54A3D",
        },
        imessage: {
          blue: "#007AFF",
          grey: "#E9E9EB",
          bg: "#F7F7F8",
        },
        ink: {
          DEFAULT: "#0A0A0A",
          muted: "#737373",
          faint: "#A3A3A3",
        },
        bg: {
          DEFAULT: "#FAFAFA",
          subtle: "#F4F4F5",
        },
        line: {
          DEFAULT: "#E5E5E5",
          strong: "#D4D4D4",
        },
        success: "#10B981",
        warning: "#F59E0B",
        danger: "#EF4444",
        info: "#3B82F6",
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 2px rgba(0, 0, 0, 0.03), 0 4px 12px rgba(0, 0, 0, 0.04)",
        soft: "0 1px 2px rgba(0, 0, 0, 0.04)",
      },
    },
  },
  plugins: [],
};

export default config;
