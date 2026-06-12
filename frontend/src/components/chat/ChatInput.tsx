import { useEffect, useState, type KeyboardEvent } from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useOrchestrate } from "@/hooks/useOrchestrate";

interface Props {
  onPendingChange?: (isPending: boolean) => void;
}

export function ChatInput({ onPendingChange }: Props) {
  const [text, setText] = useState("");
  const { mutate, isPending } = useOrchestrate();

  useEffect(() => {
    onPendingChange?.(isPending);
  }, [isPending, onPendingChange]);

  const submit = () => {
    const msg = text.trim();
    if (!msg || isPending) return;
    setText("");
    mutate(msg);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="border-t bg-background px-4 py-3">
      <div className="flex items-end gap-2 rounded-xl border bg-muted/40 px-3 py-2 focus-within:ring-2 focus-within:ring-ring">
        <textarea
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={isPending}
          placeholder={
            isPending ? "Waiting for response…" : "Message your Chief of Staff…"
          }
          className="flex-1 resize-none bg-transparent text-sm outline-none placeholder:text-muted-foreground disabled:opacity-50 max-h-32"
          style={{ height: "auto", minHeight: "1.5rem" }}
          onInput={(e) => {
            const t = e.currentTarget;
            t.style.height = "auto";
            t.style.height = `${t.scrollHeight}px`;
          }}
        />
        <Button
          size="icon"
          onClick={submit}
          disabled={!text.trim() || isPending}
          className="h-8 w-8 shrink-0"
        >
          {isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>
      <p className="mt-1 text-center text-[10px] text-muted-foreground">
        Enter to send · Shift+Enter for new line
      </p>
    </div>
  );
}
