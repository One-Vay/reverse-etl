import { FlaskConical } from "lucide-react";

export function DemoDataBadge() {
  return (
    <span
      title="This backend endpoint doesn't exist yet — showing sample data as a preview of the feature."
      className="inline-flex items-center gap-1 rounded-full bg-warning/15 px-2 py-0.5 text-[11px] font-medium text-warning"
    >
      <FlaskConical className="h-3 w-3" /> Demo data
    </span>
  );
}
