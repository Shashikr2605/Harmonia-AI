import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        "h-primary":  "#7c3aed",
        "h-accent":   "#06d6a0",
        "h-surface":  "#0d0d1a",
        "h-base":     "#050508",
      },
      animation: {
        "fade-up": "fade-up 0.4s ease forwards",
        "wave":    "wave 1s ease-in-out infinite",
      },
      keyframes: {
        "fade-up": {
          "from": { opacity: "0", transform: "translateY(16px)" },
          "to":   { opacity: "1", transform: "translateY(0)" },
        },
        "wave": {
          "0%, 100%": { transform: "scaleY(0.4)" },
          "50%":      { transform: "scaleY(1)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
