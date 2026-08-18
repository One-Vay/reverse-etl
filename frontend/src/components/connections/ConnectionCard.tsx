import { Database, Pencil, Server, Trash2 } from "lucide-react";

import { ActionMenu } from "@/components/ui/ActionMenu";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";

interface ConnectionCardProps {
  icon?: "database" | "server";
  name: string;
  typeLabel: string;
  subtitle: string;
  meta: string;
  onEdit: () => void;
  onDelete: () => void;
}

export function ConnectionCard({
  icon = "database",
  name,
  typeLabel,
  subtitle,
  meta,
  onEdit,
  onDelete,
}: ConnectionCardProps) {
  const Icon = icon === "database" ? Database : Server;

  return (
    <Card className="relative p-4">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-semibold">{name}</p>
            <Badge variant="muted">{typeLabel}</Badge>
          </div>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">{subtitle}</p>
          <p className="mt-2 text-[11px] text-muted-foreground">{meta}</p>
        </div>
        <ActionMenu
          ariaLabel="Open connection menu"
          items={[
            { label: "Edit", icon: Pencil, onClick: onEdit },
            { label: "Delete", icon: Trash2, onClick: onDelete, destructive: true },
          ]}
        />
      </div>
    </Card>
  );
}
