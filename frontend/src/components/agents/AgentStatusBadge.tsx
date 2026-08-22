import type { AgentStatus } from "@/api/types";
import { Badge } from "@/components/ui/Badge";

const STATUS_CONFIG: Record<
  AgentStatus,
  { label: string; variant: "success" | "muted" | "warning" }
> = {
  draft: { label: "Draft", variant: "warning" },
  ready: { label: "Ready", variant: "success" },
  archived: { label: "Archived", variant: "muted" },
};

export function AgentStatusBadge({ status }: { status: AgentStatus }) {
  const config = STATUS_CONFIG[status];
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
