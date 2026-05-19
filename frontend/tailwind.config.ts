import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Decision colors. Used in result displays.
        decision: {
          pass: "#15803d",      // green-700
          reject: "#b91c1c",    // red-700
          manual: "#b45309",    // amber-700
        },
      },
      fontFamily: {
        // Operator UI uses a clean, slightly condensed sans for density.
        // No "fun" fonts — this is a compliance tool, not a marketing site.
        sans: ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
