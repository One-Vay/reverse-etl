import type { ReactNode } from "react";

import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";

interface AppShellProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
}

export function AppShell({ title, description, actions, children }: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar title={title} description={description} />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          {actions && (
            <div className="mb-5 flex flex-wrap items-center justify-end gap-2">
              {actions}
            </div>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}
