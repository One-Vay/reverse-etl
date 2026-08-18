import { ChevronDown, LayoutGrid, Search } from "lucide-react";
import { useMemo, useState } from "react";

import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { useDestinationEntities } from "@/hooks/useDestinations";
import { cn } from "@/lib/utils";

interface DestinationEntityPickerProps {
  destinationId: number | undefined;
  selectedEntity?: string;
  onSelect: (entity: string) => void;
}

/** Browses the entity types a destination exposes, so "destination entity"
 * can be picked by clicking rather than typed from memory. Collapsed by
 * default — the field it feeds stays a plain, freely-editable text input
 * above this, mirroring SourceTablePicker. */
export function DestinationEntityPicker({
  destinationId,
  selectedEntity,
  onSelect,
}: DestinationEntityPickerProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const entitiesQuery = useDestinationEntities(open ? destinationId : undefined);

  const filteredEntities = useMemo(() => {
    const entities = entitiesQuery.data ?? [];
    if (!search.trim()) return entities;
    const needle = search.trim().toLowerCase();
    return entities.filter((entity) => entity.toLowerCase().includes(needle));
  }, [entitiesQuery.data, search]);

  if (!destinationId) return null;

  return (
    <div className="rounded-md border border-border">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs font-medium text-muted-foreground hover:text-foreground"
      >
        <span className="flex items-center gap-1.5">
          <LayoutGrid className="h-3.5 w-3.5" />
          Browse entities on this destination
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
              placeholder="Filter entities…"
              className="pl-8"
              autoFocus
            />
          </div>

          <div className="max-h-48 overflow-y-auto scrollbar-thin">
            {entitiesQuery.isPending ? (
              <Spinner />
            ) : entitiesQuery.isError ? (
              <p className="px-2 py-3 text-center text-xs text-destructive">
                Couldn't load entities. Check the destination's connection.
              </p>
            ) : filteredEntities.length === 0 ? (
              <p className="px-2 py-3 text-center text-xs text-muted-foreground">
                {search ? "No entities match your search." : "No entities found."}
              </p>
            ) : (
              <ul className="flex flex-col">
                {filteredEntities.map((entity) => {
                  const isSelected = entity === selectedEntity;
                  return (
                    <li key={entity}>
                      <button
                        type="button"
                        onClick={() => {
                          onSelect(entity);
                          setOpen(false);
                        }}
                        className={cn(
                          "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm hover:bg-accent",
                          isSelected && "bg-primary/10 text-primary",
                        )}
                      >
                        <LayoutGrid className="h-3.5 w-3.5 shrink-0" />
                        <span className="truncate">{entity}</span>
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
