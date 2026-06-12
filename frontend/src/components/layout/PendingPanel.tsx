import { useState } from "react";
import { ChevronRight, ChevronLeft, Inbox } from "lucide-react";
import { PendingItemCard } from "@/components/cards/PendingItemCard";
import { usePending } from "@/hooks/usePending";
import { cn } from "@/lib/utils";

export function PendingPanel() {
  const [collapsed, setCollapsed] = useState(false);
  const { query } = usePending();

  const items = query.data ?? [];
  const count = items.length;

  return (
    <div
      className={cn(
        "flex flex-col border-l bg-background transition-all duration-200",
        collapsed ? "w-10" : "w-80"
      )}
    >
      <div className="flex items-center justify-between border-b px-3 py-3">
        {!collapsed && (
          <div className="flex items-center gap-2 text-sm font-medium">
            <Inbox className="h-4 w-4" />
            Pending Approvals
            {count > 0 && (
              <span className="rounded-full bg-amber-500 px-2 py-0.5 text-[10px] font-bold text-white">
                {count}
              </span>
            )}
          </div>
        )}
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="ml-auto rounded p-1 hover:bg-muted"
          aria-label={collapsed ? "Expand panel" : "Collapse panel"}
        >
          {collapsed ? (
            <ChevronLeft className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>
      </div>

      {!collapsed && (
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {query.isLoading && (
            <p className="text-xs text-muted-foreground text-center py-4">
              Loading…
            </p>
          )}
          {!query.isLoading && count === 0 && (
            <p className="text-xs text-muted-foreground text-center py-4">
              No pending approvals
            </p>
          )}
          {items.map((item) => (
            <PendingItemCard key={item.id} item={item} />
          ))}
        </div>
      )}

      {collapsed && count > 0 && (
        <div className="flex justify-center pt-2">
          <span className="rounded-full bg-amber-500 px-1.5 py-0.5 text-[10px] font-bold text-white">
            {count}
          </span>
        </div>
      )}
    </div>
  );
}
