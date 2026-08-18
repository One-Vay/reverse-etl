import type { SyncStatus } from "@/api/types";
import { Badge } from "@/components/ui/Badge";

const STATUS_CONFIG: Record<
  SyncStatus,
  { label: string; variant: "success" | "muted" | "warning" }
> = {
  active: { label: "Active", variant: "success" },
  paused: { label: "Paused", variant: "warning" },
  inactive: { label: "Inactive", variant: "muted" },
};

export function SyncStatusBadge({ status }: { status: SyncStatus }) {
  const config = STATUS_CONFIG[status];
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
