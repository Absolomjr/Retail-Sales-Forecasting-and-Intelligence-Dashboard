/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // The same fixed categorical palette the notebook charts use, so a
        // colour means the same thing in the notebook and in the dashboard.
        series: {
          1: "#2a78d6", 2: "#eb6834", 3: "#1baf7a", 4: "#eda100",
          5: "#e87ba4", 6: "#008300", 7: "#4a3aa7", 8: "#e34948",
        },
        surface: { DEFAULT: "#fcfcfb", sunken: "#f4f3f0", raised: "#ffffff" },
        ink: { DEFAULT: "#0b0b0b", muted: "#52514e", faint: "#8a8880" },
        hairline: "#e6e5e0",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
