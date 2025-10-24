"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ComponentProps } from "react";
import { cn } from "@/lib/utils";
import type { NavSection } from "@/config/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sparkles } from "lucide-react";

interface SidebarProps {
  sections: NavSection[];
}

export const Sidebar = ({ sections }: SidebarProps) => {
  const pathname = usePathname();

  return (
    <aside className="hidden border-r border-border/60 bg-surface/80 px-5 pb-6 pt-8 backdrop-blur-xl lg:flex lg:w-72 lg:flex-col xl:w-80">
      <div className="mb-8 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/90 text-primary-foreground shadow-float">
          <Sparkles className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm uppercase tracking-[0.3em] text-muted-foreground">TradingAgents</p>
          <p className="font-heading text-xl font-semibold leading-tight text-foreground">Control Center</p>
        </div>
      </div>

      <div className="mb-8">
        <Badge variant="accent" className="mb-3 inline-flex">
          Live Global Markets
        </Badge>
        <p className="text-sm text-muted-foreground">
          Multi-agent intelligence synthesizing market, research, and risk into decisive trading actions.
        </p>
      </div>

      <nav className="flex-1 space-y-8">
        {sections.map((section) => (
          <div key={section.title} className="space-y-4">
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-muted-foreground">
              {section.title}
            </p>
            <ul className="space-y-1.5">
              {section.items.map((item) => (
                <SidebarLink
                  key={item.href}
                  href={item.href}
                  icon={item.icon}
                  description={item.description}
                  isActive={pathname === item.href}
                >
                  {item.label}
                </SidebarLink>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="mt-8 rounded-lg border border-border/70 bg-surface-muted/50 p-4 shadow-subtle">
        <p className="text-sm font-medium text-foreground">Need a custom execution?</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Spin up a tailored agent stack for new strategies or backtests.
        </p>
        <Button className="mt-4 w-full" size="sm" variant="accent">
          Launch sandbox
        </Button>
      </div>
    </aside>
  );
};

interface SidebarLinkProps extends ComponentProps<typeof Link> {
  icon: (props: React.SVGProps<SVGSVGElement>) => JSX.Element;
  description?: string;
  isActive?: boolean;
}

const SidebarLink = ({ icon: Icon, description, isActive, className, children, ...props }: SidebarLinkProps) => (
  <li>
    <Link
      className={cn(
        "flex items-center gap-3 rounded-lg border border-transparent px-3 py-2 text-sm transition-all duration-200",
        "hover:border-border/60 hover:bg-surface-muted/70 hover:text-foreground",
        isActive && "border-border bg-surface-muted/80 text-foreground shadow-subtle",
        className,
      )}
      {...props}
    >
      <Icon className="h-5 w-5 text-muted-foreground" />
      <div className="flex flex-1 flex-col">
        <span className="font-medium">{children}</span>
        {description ? (
          <span className="text-xs text-muted-foreground/80">{description}</span>
        ) : null}
      </div>
    </Link>
  </li>
);
