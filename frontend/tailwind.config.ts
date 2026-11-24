/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        obsidian: "#06080F",
        aurora: {
          cyan: "#00F2FE",
          blue: "#4FACFE",
          violet: "#7F00FF",
          emerald: "#00F5A0",
          crimson: "#FF416C",
        },
      },
      backgroundImage: {
        "aurora-mesh":
          "radial-gradient(at 0% 0%, rgba(127, 0, 255, 0.15) 0px, transparent 50%), radial-gradient(at 100% 0%, rgba(0, 242, 254, 0.15) 0px, transparent 50%), radial-gradient(at 50% 100%, rgba(0, 245, 160, 0.1) 0px, transparent 50%)",
        "glass-gradient":
          "linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%)",
      },
      boxShadow: {
        "glass-edge": "inset 0 1px 1px 0 rgba(255, 255, 255, 0.1)",
        "aurora-glow": "0 0 25px -5px rgba(0, 242, 254, 0.3)",
        "node-active": "0 0 15px 2px rgba(0, 245, 160, 0.5)",
      },
    },
  },
  plugins: [],
};
