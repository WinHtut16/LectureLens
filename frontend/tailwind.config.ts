import type { Config } from "tailwindcss";

// Design tokens live here (CLAUDE.md: use tokens, never raw hex in components).
// Extend the palette/spacing/typography as the design system grows.
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Placeholder semantic tokens — replace with the real palette.
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
      },
    },
  },
  plugins: [],
};

export default config;
