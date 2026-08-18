import { KeyRound, Plus } from "lucide-react";

import { useSourceTableSchema } from "@/hooks/useSources";
import { cn } from "@/lib/utils";

interface SourceColumnPickerProps {
  sourceId: number | undefined;
  table: string | undefined;
  schema?: string;
  /** source_field values already present in field_mappings, so already-used
   * columns render as visibly "added" instead of looking pickable again. */
  usedColumns: string[];
  onPick: (columnName: string) => void;
}

/** Shows a source table's columns as one-click chips: clicking a column
 * appends a new field mapping row pre-filled with that column name. */
export function SourceColumnPicker({
  sourceId,
  table,
  schema = "public",
  usedColumns,
  onPick,
}: SourceColumnPickerProps) {
  const schemaQuery = useSourceTableSchema(sourceId, table, schema);

  if (!sourceId || !table) return null;

  if (schemaQuery.isLoading) {
    return (
      <p className="text-xs text-muted-foreground">Loading columns for "{table}"…</p>
    );
  }

  if (schemaQuery.isError) {
    return (
      <p className="text-xs text-destructive">
        Couldn't load columns for "{table}". Check the source's connection.
      </p>
    );
  }

  const columns = schemaQuery.data ?? [];
  if (columns.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">
        "{table}" has no columns, or the source doesn't support column discovery yet.
      </p>
    );
  }

  const usedSet = new Set(usedColumns.filter(Boolean));

  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-xs font-medium text-muted-foreground">
        Available columns — click to add
      </p>
      <div className="flex flex-wrap gap-1.5">
        {columns.map((column) => {
          const isUsed = usedSet.has(column.name);
          return (
            <button
              key={column.name}
              type="button"
              onClick={() => onPick(column.name)}
              title={`${column.data_type}${column.nullable ? "" : " · not null"}`}
              className={cn(
                "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs transition-colors",
                isUsed
                  ? "border-primary/30 bg-primary/10 text-primary"
                  : "border-border bg-background text-foreground hover:border-primary/40 hover:bg-accent",
              )}
            >
              {column.is_primary_key && <KeyRound className="h-3 w-3 shrink-0" />}
              {column.name}
              {!isUsed && <Plus className="h-3 w-3 shrink-0" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}
