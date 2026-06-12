import { useState } from "react";
import { ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { usePending } from "@/hooks/usePending";
import type { PendingItem } from "@/types/api";

interface Props {
  item: PendingItem;
}

export function PendingItemCard({ item }: Props) {
  const { approve, reject } = usePending();
  const [expanded, setExpanded] = useState(false);

  const isApproving = approve.isPending && approve.variables === item.id;
  const isRejecting = reject.isPending && reject.variables === item.id;

  return (
    <Card className="text-sm">
      <CardHeader className="pb-2">
        <p className="font-medium leading-snug">{item.subject}</p>
        <p className="text-xs text-muted-foreground">{item.sender}</p>
      </CardHeader>
      <CardContent className="pb-2">
        <p className="text-xs text-muted-foreground mb-1">
          To: {item.draft.to || <span className="italic">not set</span>}
        </p>
        <button
          className="flex items-center gap-1 text-xs text-primary"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? (
            <>
              <ChevronUp className="h-3 w-3" /> Hide draft
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3" /> Show draft
            </>
          )}
        </button>
        {expanded && (
          <p className="mt-2 whitespace-pre-wrap rounded bg-muted p-2 text-xs">
            {item.draft.body}
          </p>
        )}
      </CardContent>
      <CardFooter className="gap-2">
        <Button
          size="sm"
          variant="default"
          className="flex-1 bg-green-600 hover:bg-green-700 text-white"
          disabled={isApproving || isRejecting}
          onClick={() => approve.mutate(item.id)}
        >
          {isApproving ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            "Approve & Send"
          )}
        </Button>
        <Button
          size="sm"
          variant="destructive"
          className="flex-1"
          disabled={isApproving || isRejecting}
          onClick={() => reject.mutate(item.id)}
        >
          {isRejecting ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            "Reject"
          )}
        </Button>
      </CardFooter>
    </Card>
  );
}
