import type { ReactNode } from "react";

import { Sidebar } from "@/components/layout/sidebar";
import { TopNav } from "@/components/layout/top-nav";
import { navigation } from "@/config/navigation";

type AppShellProps = {
  children: ReactNode;
};

export const AppShell = ({ children }: AppShellProps) => {
  return (
    <div className="flex min-h-screen w-full bg-background/95">
      <Sidebar sections={navigation} />
      <div className="relative flex w-full flex-1 flex-col">
        <TopNav />
        <main className="flex-1 px-4 pb-10 pt-6 sm:px-8 lg:px-10 xl:px-12">
          <div className="mx-auto w-full max-w-6xl space-y-8">{children}</div>
        </main>
      </div>
      <div className="pointer-events-none fixed inset-x-0 top-0 z-[-1] h-[520px] bg-hero-glow blur-3xl" />
    </div>
  );
};
