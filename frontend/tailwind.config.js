/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        panel: "#EEF1F5",
        ink: "#1B2433",
        steel: "#5B6B82",
        rule: "#CDD4DE",
        action: { DEFAULT: "#3B4FD8", hover: "#2F40B5" },
        ok: "#1F7A64",
        partial: "#9A6412",
        fail: "#B4441F",
      },
      fontFamily: {
        sans: ['"Instrument Sans"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
