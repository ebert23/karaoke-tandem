/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0a0a0f",
          900: "#121018",
          800: "#1a1725",
          700: "#241f33",
        },
        neon: {
          purple: "#a855f7",
          pink: "#ff2fb0",
          pinklight: "#ff7ac9",
          cyan: "#38f4ff",
        },
      },
      fontFamily: {
        display: ["'Poppins'", "system-ui", "sans-serif"],
        body: ["'Inter'", "system-ui", "sans-serif"],
      },
      boxShadow: {
        neon: "0 0 20px rgba(255, 47, 176, 0.45), 0 0 40px rgba(168, 85, 247, 0.25)",
        "neon-sm": "0 0 10px rgba(255, 47, 176, 0.4)",
      },
      backgroundImage: {
        "grid-glow":
          "radial-gradient(circle at 20% 20%, rgba(168,85,247,0.25), transparent 40%), radial-gradient(circle at 80% 0%, rgba(255,47,176,0.2), transparent 40%), radial-gradient(circle at 50% 100%, rgba(56,244,255,0.12), transparent 45%)",
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
