/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        // LeadRescue design palette
        cream: {
          DEFAULT: "#FAF8F4",
          dark: "#F5F2EC",
        },
        charcoal: {
          DEFAULT: "#1C1C1A",
          light: "#2A2A28",
          footer: "#161614",
        },
        copper: {
          DEFAULT: "#B87333",
          light: "#C4A882",
          gold: "#D4AF6A",
        },
        warm: {
          DEFAULT: "#8B7355",
          light: "#6B5D4A",
          muted: "#4A3F33",
        },
        sage: {
          DEFAULT: "#7A8C7E",
        },
        sand: {
          DEFAULT: "#E5DFD5",
        },
        whatsapp: {
          green: "#25D366",
          dark: "#0f1c14",
          darker: "#0b1612",
          border: "#1e3324",
          bubble: "#1e2e25",
          frame: "#1a2e1e",
        },
        nature: {
          DEFAULT: "#EEF0EC",
        },
      },
      fontFamily: {
        display: ['"Cormorant Garamond"', "serif"],
        body: ['"Inter"', "sans-serif"],
      },
    },
  },
  plugins: [],
};
