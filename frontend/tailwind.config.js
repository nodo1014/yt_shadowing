/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#3B82F6', // Blue 500
        secondary: '#6B7280', // Gray 500
        accent: '#10B981', // Emerald 500
        background: '#F3F4F6', // Gray 100
        text: '#1F2937', // Gray 800
      },
    },
  },
  plugins: [],
} 