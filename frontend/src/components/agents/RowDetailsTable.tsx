import type { RowDetail } from "@/api/types";
import { cn } from "@/lib/utils";

interface RowDetailsTableProps {
  rows: RowDetail[];
  /** Caption shown above the table, e.g. "3 of 15 rows selected". */
  caption?: string;
}

/** The full per-row breakdown behind a run or preview: every row's score,
 * the model's reason, whether it was (or would be) selected, and — for
 * selected rows — the exact record sent to the destination. This is what
 * makes an agent's output legible instead of a black box: no row's fate
 * is a mystery, and no destination record's fields are hidden from the
 * person operating the agent. */
export function RowDetailsTable({ rows, caption }: RowDetailsTableProps) {
  if (rows.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">No rows to show yet.</p>
    );
  }

  const recordColumns = Array.from(
    new Set(rows.flatMap((r) => (r.record ? Object.keys(r.record) : []))),
  );

  return (
    <div className="flex flex-col gap-2">
      {caption && <p className="text-xs text-muted-foreground">{caption}</p>}
      <div className="overflow-x-auto scrollbar-thin rounded-md border border-border">
        <table className="w-full min-w-[560px] text-left text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/30 text-xs text-muted-foreground">
              <th className="px-2 py-2 font-medium">Row</th>
              <th className="px-2 py-2 font-medium">Score</th>
              <th className="px-2 py-2 font-medium">Selected</th>
              <th className="px-2 py-2 font-medium">Reason</th>
              {recordColumns.map((col) => (
                <th key={col} className="px-2 py-2 font-medium">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((row) => (
              <tr
                key={row.index}
                className={cn(!row.selected && "text-muted-foreground/70")}
              >
                <td className="px-2 py-2 font-mono">{row.index}</td>
                <td className="px-2 py-2 font-mono">{row.score.toFixed(2)}</td>
                <td className="px-2 py-2">
                  {row.selected ? (
                    <span className="text-success">Yes</span>
                  ) : (
                    <span>No</span>
                  )}
                </td>
                <td className="max-w-[280px] px-2 py-2">{row.reason || "—"}</td>
                {recordColumns.map((col) => (
                  <td key={col} className="max-w-[200px] truncate px-2 py-2 font-mono">
                    {row.record?.[col] != null ? String(row.record[col]) : "—"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
