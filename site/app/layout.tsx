import "./globals.css";
import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: {
    default: "SENTINEL — Trusted Intelligence for Players",
    template: "%s · SENTINEL",
  },
  description:
    "SENTINEL is a pre-release trusted intelligence platform spanning Android, Web Control Plane, Windows Companion and player-facing guidance.",
  icons: {
    icon: "/brand/icon-64.png",
  },
  robots: {
    index: false,
    follow: false,
  },
};

export const viewport: Viewport = {
  colorScheme: "dark light",
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#061018" },
    { media: "(prefers-color-scheme: light)", color: "#f4f8fb" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
