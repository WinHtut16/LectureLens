import type { Config } from "tailwindcss"

export default {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0A0B0D",
        "bg-elev": "#101216",
        surface: { DEFAULT: "#15171C", 2: "#1B1E24", 3: "#21252C" },
        border: { DEFAULT: "#262A31", strong: "#343A44" },
        text: { DEFAULT: "#ECEEF1", muted: "#9AA0AB", faint: "#6B7280" },
        primary: {
          DEFAULT: "#6E8CFF",
          fill: "#5D77F0",
          hover: "#88A0FF",
          press: "#4F69E6",
        },
        highlight: "#F2C14E",
        success: "#4ECFA0",
        warn: "#F2C14E",
        danger: "#F87171",
      },
      fontFamily: {
        serif: ["Instrument Serif", "Georgia", "serif"],
        sans: ["Hanken Grotesk", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      fontSize: {
        display: ["3.5rem", { lineHeight: "1.05", letterSpacing: "-0.02em" }],
        h1: ["2.5rem", { lineHeight: "1.1" }],
        h2: ["1.875rem", { lineHeight: "1.15" }],
        h3: ["1.125rem", { lineHeight: "1.4", fontWeight: "600" }],
        base: ["0.9375rem", { lineHeight: "1.6" }],
        sm: ["0.8125rem", { lineHeight: "1.5" }],
        xs: ["0.75rem", { lineHeight: "1.5" }],
      },
      borderRadius: { sm: "6px", md: "10px", lg: "14px", xl: "20px" },
      boxShadow: {
        sm: "0 1px 2px rgba(0,0,0,.45)",
        md: "0 6px 22px rgba(0,0,0,.45)",
        lg: "0 20px 60px rgba(0,0,0,.55)",
        glow: "0 0 0 1px rgba(110,140,255,.45), 0 10px 36px rgba(110,140,255,.18)",
      },
    },
  },
  plugins: [],
} satisfies Config
