import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";

import { AppShell } from "@/components/layout/app-shell";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
const grotesk = Space_Grotesk({ subsets: ["latin"], variable: "--font-heading" });
const jetBrains = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: {
    default: "TradingAgents Control Center",
    template: "%s | TradingAgents",
  },
  description:
    "Operational surface for orchestrating TradingAgents multi-agent research, risk, and execution workflows.",
  keywords: [
    "TradingAgents",
    "Tauric Research",
    "multi-agent",
    "trading",
    "LLM",
    "Next.js",
  ],
  openGraph: {
    title: "TradingAgents Control Center",
    description:
      "Monitor research-to-trade pipelines, debate outcomes, and risk posture through a cohesive command interface.",
    type: "website",
    siteName: "TradingAgents",
  },
  twitter: {
    card: "summary_large_image",
    title: "TradingAgents Control Center",
    description:
      "Monitor research-to-trade pipelines, debate outcomes, and risk posture through a cohesive command interface.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${grotesk.variable} ${jetBrains.variable} min-h-screen bg-background font-sans text-foreground antialiased`}
      >
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
