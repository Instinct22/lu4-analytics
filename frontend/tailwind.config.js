/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#09090b",
          raised: "#18181b",
          overlay: "#27272a",
        },
        accent: {
          DEFAULT: "#f59e0b",
          muted: "#92400e",
          glow: "rgba(245, 158, 11, 0.15)",
        },
      },
      boxShadow: {
        panel: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 4px 24px -4px rgba(0,0,0,0.5)",
        glow: "0 0 40px -8px rgba(245, 158, 11, 0.25)",
      },
      backgroundImage: {
        "mesh-dark":
          "radial-gradient(at 0% 0%, rgba(245,158,11,0.08) 0px, transparent 50%), radial-gradient(at 100% 100%, rgba(39,39,42,0.8) 0px, transparent 50%)",
      },
    },
  },
  plugins: [],
};
