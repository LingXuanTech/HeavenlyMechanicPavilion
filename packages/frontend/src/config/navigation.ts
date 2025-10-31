import type { LucideIcon } from "lucide-react";
import {
  Activity,
  BookOpenCheck,
  Database,
  LayoutDashboard,
  LineChart,
  ShieldCheck,
  Workflow,
  TrendingUp,
  Settings,
  Boxes,
  BarChart3,
  Brain,
} from "lucide-react";

export type NavItem = {
  label: string;
  href: string;
  description?: string;
  icon: LucideIcon;
};

export type NavSection = {
  title: string;
  items: NavItem[];
};

export const navigation: NavSection[] = [
  {
    title: "Trading Intelligence",
    items: [
      {
        label: "Overview",
        href: "/",
        description: "Session health, conviction, and capital at risk",
        icon: LayoutDashboard,
      },
      {
        label: "Real-Time Dashboard",
        href: "/dashboard",
        description: "Live portfolio, signals, and agent activity",
        icon: TrendingUp,
      },
      {
        label: "Market Radar",
        href: "/market",
        description: "Live macro and technical briefing",
        icon: LineChart,
      },
      {
        label: "Research Streams",
        href: "/research",
        description: "Analyst threads and sourcing",
        icon: Workflow,
      },
    ],
  },
  {
    title: "Risk & Compliance",
    items: [
      {
        label: "Risk Center",
        href: "/risk",
        description: "Scenario analysis and exposure limits",
        icon: ShieldCheck,
      },
      {
        label: "Portfolio Vault",
        href: "/portfolio",
        description: "Positions, cash, and hedging",
        icon: Database,
      },
      {
        label: "Playbooks",
        href: "/playbooks",
        description: "Institutional procedures and guardrails",
        icon: BookOpenCheck,
      },
    ],
  },
  {
    title: "Operations",
    items: [
      {
        label: "Activity",
        href: "/activity",
        description: "Execution logs and event timelines",
        icon: Activity,
      },
      {
        label: "System Monitoring",
        href: "/monitoring",
        description: "Health metrics, alerts, and uptime",
        icon: BarChart3,
      },
    ],
  },
  {
    title: "Administration",
    items: [
      {
        label: "Vendor Management",
        href: "/admin/vendors",
        description: "Configure data vendors and routing priorities",
        icon: Settings,
      },
      {
        label: "Agent Marketplace",
        href: "/admin/agents",
        description: "Manage plugin inventory and prompts",
        icon: Boxes,
      },
      {
        label: "Agent LLM Config",
        href: "/admin/agents/llm-config",
        description: "Configure LLM settings for each agent",
        icon: Brain,
      },
    ],
  },
];
