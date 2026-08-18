import { ChevronDown, Database, Search, Table2 } from "lucide-react";
import { useMemo, useState } from "react";

import type { TableInfo } from "@/api/types";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { useSourceTables } from "@/hooks/useSources";
import { cn } from "@/lib/utils";

interface SourceTablePickerProps {
  sourceId: number | undefined;
  selectedTable?: string;
  onSelect: (table: TableInfo) => void;
}

/** Browses the tables/views a source exposes, so "source table" can be
 * picked by clicking rather than typed from memory. Collapsed by default —
 * the field it feeds stays a plain, freely-editable text input above this. */
export function SourceTablePicker({
  sourceId,
  selectedTable,
  onSelect,
}: SourceTablePickerProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const tablesQuery = useSourceTables(open ? sourceId : undefined);

  const filteredTables = useMemo(() => {
    const tables = tablesQuery.data ?? [];
    if (!search.trim()) return tables;
    const needle = search.trim().toLowerCase();
    return tables.filter((table) => table.name.toLowerCase().includes(needle));
  }, [tablesQuery.data, search]);

  if (!sourceId) return null;

  return (
    <div className="rounded-md border border-border">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs font-medium text-muted-foreground hover:text-foreground"
      >
        <span className="flex items-center gap-1.5">
          <Database className="h-3.5 w-3.5" />
          Browse tables from this source
        </span>
        <ChevronDown
          className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")}
        />
      </button>

      {open && (
        <div className="border-t border-border p-2">
          <div className="relative mb-2">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter tables…"
              className="pl-8"
              autoFocus
            />
          </div>

          <div className="max-h-48 overflow-y-auto scrollbar-thin">
            {tablesQuery.isLoading ? (
              <Spinner />
            ) : tablesQuery.isError ? (
              <p className="px-2 py-3 text-center text-xs text-destructive">
                Couldn't load tables. Check the source's connection.
              </p>
            ) : filteredTables.length === 0 ? (
              <p className="px-2 py-3 text-center text-xs text-muted-foreground">
                {search ? "No tables match your search." : "No tables found."}
              </p>
            ) : (
              <ul className="flex flex-col">
                {filteredTables.map((table) => {
                  const isSelected = table.name === selectedTable;
                  return (
                    <li key={`${table.schema}.${table.name}`}>
                      <button
                        type="button"
                        onClick={() => {
                          onSelect(table);
                          setOpen(false);
                        }}
                        className={cn(
                          "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm hover:bg-accent",
                          isSelected && "bg-primary/10 text-primary",
                        )}
                      >
                        <Table2 className="h-3.5 w-3.5 shrink-0" />
                        <span className="truncate">{table.name}</span>
                        <span className="ml-auto shrink-0 text-[11px] text-muted-foreground">
                          {table.schema} &middot; {table.kind}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
