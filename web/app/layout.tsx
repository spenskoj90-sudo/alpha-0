import "./globals.css";
import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Onest } from "next/font/google";

const uiFont = Inter({
  subsets: ["latin", "cyrillic"],
  display: "swap",
  variable: "--font-inter",
});

const brandFont = Onest({
  subsets: ["latin", "cyrillic"],
  display: "swap",
  variable: "--font-onest",
});

const technicalFont = JetBrains_Mono({
  subsets: ["latin", "cyrillic"],
  display: "swap",
  variable: "--font-jetbrains-mono",
});

export const metadata: Metadata = {
  title: "SENTINEL",
  description: "SENTINEL trusted intelligence control plane",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${uiFont.variable} ${brandFont.variable} ${technicalFont.variable}`}>
        {children}
      </body>
    </html>
  );
}
