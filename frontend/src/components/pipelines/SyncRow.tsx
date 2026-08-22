import { ArrowRight, Pencil, Play, Trash2 } from "lucide-react";

import type { Destination, Mapping, Source, Sync } from "@/api/types";
import { SyncStatusBadge } from "@/components/pipelines/SyncStatusBadge";
import { Button } from "@/components/ui/Button";
import { formatRelativeTime, formatSchedule } from "@/lib/utils";

interface SyncRowProps {
  sync: Sync;
  source?: Source;
  destination?: Destination;
  mapping?: Mapping;
  onEdit: () => void;
  onDelete: () => void;
  onRunNow: () => void;
  isRunning?: boolean;
}

export function SyncRow({
  sync,
  source,
  destination,
  mapping,
  onEdit,
  onDelete,
  onRunNow,
  isRunning,
}: SyncRowProps) {
  return (
    <div className="flex flex-col gap-3 border-b border-border p-4 last:border-0 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-semibold">{sync.name}</p>
          <SyncStatusBadge status={sync.status} />
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
          <span className="truncate">{source?.name ?? `Source #${sync.source_id}`}</span>
          <ArrowRight className="h-3 w-3 shrink-0" />
          <span className="truncate">
            {destination?.name ?? `Destination #${sync.destination_id}`}
          </span>
          <span className="text-muted-foreground/60">via</span>
          <span className="truncate">
            {mapping?.name ?? `Mapping #${sync.mapping_id}`}
          </span>
        </div>
        <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
          <span className="font-mono">{formatSchedule(sync)}</span>
          <span>Last run: {formatRelativeTime(sync.last_run)}</span>
          <span>Next run: {formatRelativeTime(sync.next_run)}</span>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-1.5">
        <Button variant="outline" size="sm" onClick={onRunNow} loading={isRunning}>
          <Play className="h-3.5 w-3.5" /> Run now
        </Button>
        <Button variant="ghost" size="icon" onClick={onEdit} aria-label="Edit pipeline">
          <Pencil className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={onDelete}
          aria-label="Delete pipeline"
          className="text-destructive hover:bg-destructive/10"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
