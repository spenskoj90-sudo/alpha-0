import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "SENTINEL", description: "SENTINEL personal control plane" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
