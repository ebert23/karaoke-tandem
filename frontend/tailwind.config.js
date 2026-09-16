/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#070b14",
          900: "#0d1422",
          800: "#151f31",
          700: "#202d42",
        },
        neon: {
          purple: "#7c83ff",
          pink: "#ff5468",
          pinklight: "#ff8b78",
          cyan: "#43e7d2",
        },
      },
      fontFamily: {
        display: ["'Space Grotesk'", "system-ui", "sans-serif"],
        body: ["'DM Sans'", "system-ui", "sans-serif"],
      },
      boxShadow: {
        neon: "0 12px 36px rgba(255, 84, 104, 0.22), 0 0 28px rgba(67, 231, 210, 0.12)",
        "neon-sm": "0 8px 24px rgba(255, 84, 104, 0.2)",
      },
      backgroundImage: {
        "grid-glow":
          "radial-gradient(circle at 15% 10%, rgba(124,131,255,0.18), transparent 32%), radial-gradient(circle at 90% 15%, rgba(255,84,104,0.13), transparent 30%), radial-gradient(circle at 50% 100%, rgba(67,231,210,0.08), transparent 40%)",
      },
      animation: {
        pulseGlow: "pulseGlow 2.4s ease-in-out infinite",
        floatSlow: "floatSlow 6s ease-in-out infinite",
        retoEntrada: "retoEntrada 0.55s cubic-bezier(0.34, 1.56, 0.64, 1) both",
        confettiCaer: "confettiCaer 1.8s ease-in forwards",
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { opacity: 1, filter: "drop-shadow(0 0 6px rgba(255,47,176,0.6))" },
          "50%": { opacity: 0.7, filter: "drop-shadow(0 0 14px rgba(168,85,247,0.8))" },
        },
        floatSlow: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-6px)" },
        },
        retoEntrada: {
          "0%": { transform: "scale(0.3) rotate(-8deg)", opacity: 0 },
          "50%": { transform: "scale(1.08) rotate(4deg)", opacity: 1 },
          "70%": { transform: "scale(0.96) rotate(-2deg)" },
          "100%": { transform: "scale(1) rotate(0deg)", opacity: 1 },
        },
        confettiCaer: {
          "0%": { transform: "translateY(-10vh) rotate(0deg)", opacity: 1 },
          "100%": { transform: "translateY(110vh) rotate(720deg)", opacity: 0 },
        },
      },
    },
  },
  plugins: [],
};
