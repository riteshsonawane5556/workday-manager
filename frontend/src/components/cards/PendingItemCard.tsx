import { useState } from "react";
import { ChevronDown, ChevronUp, Loader2, Pencil, X, Check } from "lucide-react";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { usePending } from "@/hooks/usePending";
import type { DraftReply, PendingItem } from "@/types/api";

interface Props {
  item: PendingItem;
}

export function PendingItemCard({ item }: Props) {
  const { approve, reject, editDraft } = usePending();
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<DraftReply>(item.draft);

  const isApproving = approve.isPending && approve.variables === item.id;
  const isRejecting = reject.isPending && reject.variables === item.id;
  const isSaving = editDraft.isPending && editDraft.variables?.id === item.id;

  function startEdit() {
    setDraft(item.draft);
    setEditing(true);
    setExpanded(true);
  }

  function cancelEdit() {
    setDraft(item.draft);
    setEditing(false);
  }

  function saveEdit() {
    editDraft.mutate(
      { id: item.id, draft },
      { onSuccess: () => setEditing(false) }
    );
  }

  return (
    <Card className="text-sm">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="font-medium leading-snug">{item.subject}</p>
            <p className="text-xs text-muted-foreground">{item.sender}</p>
          </div>
          {!editing && (
            <button
              className="text-muted-foreground hover:text-foreground"
              onClick={startEdit}
              title="Edit draft"
            >
              <Pencil className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </CardHeader>
      <CardContent className="pb-2">
        {editing ? (
          <div className="flex flex-col gap-2">
            <div>
              <label className="text-xs text-muted-foreground">To</label>
              <input
                className="w-full rounded border bg-background px-2 py-1 text-xs mt-0.5"
                value={draft.to}
                onChange={(e) => setDraft((d) => ({ ...d, to: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Subject</label>
              <input
                className="w-full rounded border bg-background px-2 py-1 text-xs mt-0.5"
                value={draft.subject}
                onChange={(e) => setDraft((d) => ({ ...d, subject: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Body</label>
              <textarea
                className="w-full rounded border bg-background px-2 py-1 text-xs mt-0.5 min-h-[100px] resize-y"
                value={draft.body}
                onChange={(e) => setDraft((d) => ({ ...d, body: e.target.value }))}
              />
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" className="flex-1" onClick={cancelEdit} disabled={isSaving}>
                <X className="h-3 w-3 mr-1" /> Cancel
              </Button>
              <Button size="sm" className="flex-1" onClick={saveEdit} disabled={isSaving}>
                {isSaving ? <Loader2 className="h-3 w-3 animate-spin" /> : <><Check className="h-3 w-3 mr-1" /> Save</>}
              </Button>
            </div>
          </div>
        ) : (
          <>
            <p className="text-xs text-muted-foreground mb-1">
              To: {item.draft.to || <span className="italic">not set</span>}
            </p>
            <button
              className="flex items-center gap-1 text-xs text-primary"
              onClick={() => setExpanded((v) => !v)}
            >
              {expanded ? (
                <><ChevronUp className="h-3 w-3" /> Hide draft</>
              ) : (
                <><ChevronDown className="h-3 w-3" /> Show draft</>
              )}
            </button>
            {expanded && (
              <p className="mt-2 whitespace-pre-wrap rounded bg-muted p-2 text-xs">
                {item.draft.body}
              </p>
            )}
          </>
        )}
      </CardContent>
      {!editing && (
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
      )}
    </Card>
  );
}
