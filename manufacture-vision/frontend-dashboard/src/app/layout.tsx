import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Manufacture Vision",
  description: "Industrial safety monitoring — PPE, Fire, Zone intrusion detection",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body
        className={inter.variable}
        style={{
          fontFamily: "var(--font-inter), Inter, system-ui, sans-serif",
          background: "var(--bg)",
          color: "var(--text)",
          height: "100%",
          WebkitFontSmoothing: "antialiased",
        }}
      >
        {children}
      </body>
    </html>
  );
}
