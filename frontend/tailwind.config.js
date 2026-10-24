/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // A precision-instrument palette: cool paper, graphite ink, one
        // confident electric-indigo accent, and restrained status hues.
        canvas: "#F5F6F9",
        surface: "#FFFFFF",
        sunken: "#EDEFF4",
        ink: "#14161C",
        muted: "#5D6472",
        faint: "#949BA8",
        line: { DEFAULT: "#E6E8EF", strong: "#D4D8E1" },
        accent: {
          DEFAULT: "#4A3AEC",
          hover: "#3A2BCB",
          soft: "#ECEAFD",
          ring: "#4A3AEC",
        },
        ok: { DEFAULT: "#0E9D6B", soft: "#E4F5EE" },
        warn: { DEFAULT: "#B0730C", soft: "#F9F0DC" },
        fail: { DEFAULT: "#D54150", soft: "#FBE8EA" },
      },
      fontFamily: {
        display: ['"Space Grotesk"', "system-ui", "sans-serif"],
        sans: ['"Inter"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
      borderRadius: {
        lg: "0.7rem",
        xl: "1rem",
      },
      boxShadow: {
        card: "0 1px 2px rgba(20,22,28,0.04), 0 1px 1px rgba(20,22,28,0.03)",
        lift: "0 10px 34px -14px rgba(28,26,74,0.22)",
        glow: "0 0 0 1px rgba(74,58,236,0.12), 0 8px 28px -12px rgba(74,58,236,0.30)",
      },
      keyframes: {
        "fill-in": {
          from: { transform: "scaleX(0)" },
          to: { transform: "scaleX(1)" },
        },
        "rise": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fill-in": "fill-in 0.6s cubic-bezier(0.22,1,0.36,1) both",
        "rise": "rise 0.4s ease-out both",
      },
    },
  },
  plugins: [],
};
