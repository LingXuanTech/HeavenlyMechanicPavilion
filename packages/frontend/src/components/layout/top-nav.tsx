import Link from "next/link";
import { BookmarkCheck, Clock, Flag, Signal } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";

export const TopNav = () => {
  return (
    <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-border/60 bg-background/70 px-4 py-4 backdrop-blur-xl sm:px-8 lg:px-10 xl:px-12">
      <div className="flex flex-1 items-center gap-6">
        <div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="uppercase">
              Live Session
            </Badge>
            <span className="flex items-center text-xs text-muted-foreground">
              <Clock className="mr-1 h-3.5 w-3.5" /> 13:15 UTC
            </span>
          </div>
          <div className="mt-1 flex items-baseline gap-2">
            <h1 className="text-2xl font-heading font-semibold">NVDA | Earnings Catalyst</h1>
            <Flag className="h-4 w-4 text-success" />
            <p className="text-sm text-muted-foreground">Conviction 0.78</p>
          </div>
        </div>
        <div className="hidden items-center gap-3 md:flex">
          <NavPill icon={Signal} label="Market" value="Stable" className="text-info" />
          <NavPill icon={BookmarkCheck} label="Playbook" value="Earnings gap" />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Button variant="ghost" className="hidden md:inline-flex">
          Export briefing
        </Button>
        <Button size="sm">Launch execution</Button>
        <Link href="/profile" className="ml-2">
          <Avatar className="h-9 w-9 border border-primary/30">
            <AvatarFallback>TA</AvatarFallback>
          </Avatar>
        </Link>
      </div>
    </header>
  );
};

interface NavPillProps {
  icon: (props: React.SVGProps<SVGSVGElement>) => JSX.Element;
  label: string;
  value: string;
  className?: string;
}

const NavPill = ({ icon: Icon, label, value, className }: NavPillProps) => (
  <span
    className={cn(
      "inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-surface-muted/60 px-3 py-1 text-xs font-medium",
      "text-muted-foreground",
      className,
    )}
  >
    <Icon className="h-3.5 w-3.5" />
    <span>{label}</span>
    <span className="font-semibold text-foreground">{value}</span>
  </span>
);
