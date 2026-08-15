/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Ledger token system — grounded in actual M-Pesa/Airtel paper
        // transaction slips: warm paper ground, deep ink text, and the
        // two providers' own colors used functionally (to encode which
        // provider a card/line belongs to), not decoratively.
        paper: {
          DEFAULT: "#F6F3EC",
          raised: "#FFFFFF",
        },
        ink: {
          DEFAULT: "#191B1D",
          soft: "#5A5F66",
          faint: "#9A9E9E",
        },
        line: "#DFDACC",
        mpesa: {
          DEFAULT: "#0B6E3C",
          soft: "#E6F2EA",
        },
        airtel: {
          DEFAULT: "#B21E24",
          soft: "#FBEAEA",
        },
        money: {
          in: "#0B6E3C",
          out: "#191B1D",
        },
      },
      fontFamily: {
        // Display: a geometric system sans, set tight, for headings and
        // nav labels.
        display: [
          "Space Grotesk",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "sans-serif",
        ],
        // Body: readable system sans for everything conversational.
        body: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "sans-serif",
        ],
        // Ledger: tabular monospace used for EVERY amount in the app —
        // the signature typographic device, evoking a till receipt.
        ledger: [
          "IBM Plex Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Roboto Mono",
          "Menlo",
          "monospace",
        ],
      },
      backgroundImage: {
        // Perforation motif used at the base of "receipt" cards.
        perforate:
          "radial-gradient(circle at 6px 6px, transparent 5px, #F6F3EC 5.5px)",
      },
      backgroundSize: {
        perforate: "12px 12px",
      },
    },
  },
  plugins: [],
}
