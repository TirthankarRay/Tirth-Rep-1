/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#0066CC",
          dark: "#003366",
          light: "#4A90E2",
        },
        sclc: {
          ls: "#4A90E2",
          es: "#E94B3C",
        },
        response: {
          cr: "#27AE60",
          pr: "#F39C12",
          sd: "#95A5A6",
          pd: "#E74C3C",
        },
      },
    },
  },
  plugins: [],
};
