import { ArrowRight, Pencil, Trash2, Waypoints } from "lucide-react";

import type { Mapping, Source } from "@/api/types";
import { ActionMenu } from "@/components/ui/ActionMenu";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";

interface MappingCardProps {
  mapping: Mapping;
  source?: Source;
  onEdit: () => void;
  onDelete: () => void;
}

export function MappingCard({ mapping, source, onEdit, onDelete }: MappingCardProps) {
  return (
    <Card className="p-4">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Waypoints className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold">{mapping.name}</p>
          <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="truncate">
              {source?.name ?? `Source #${mapping.source_id}`}
            </span>
            <span className="text-muted-foreground/60">/</span>
            <span className="truncate font-mono">{mapping.source_table}</span>
            <ArrowRight className="h-3 w-3 shrink-0" />
            <span className="truncate font-mono">{mapping.destination_entity}</span>
          </div>
          <div className="mt-2">
            <Badge variant="muted">
              {mapping.field_mappings.length} field
              {mapping.field_mappings.length === 1 ? "" : "s"} mapped
            </Badge>
          </div>
        </div>
        <ActionMenu
          ariaLabel="Open mapping menu"
          items={[
            { label: "Edit", icon: Pencil, onClick: onEdit },
            { label: "Delete", icon: Trash2, onClick: onDelete, destructive: true },
          ]}
        />
      </div>
    </Card>
  );
}
