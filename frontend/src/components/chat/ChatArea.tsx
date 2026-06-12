import { useEffect, useRef } from "react";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { useSession } from "@/store/sessionStore";

interface Props {
  isPending: boolean;
}

export function ChatArea({ isPending }: Props) {
  const { state } = useSession();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [state.messages, isPending]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
      {state.messages.length === 0 && (
        <div className="flex h-full items-center justify-center">
          <div className="text-center text-muted-foreground">
            <p className="text-lg font-medium">Workday Manager</p>
            <p className="text-sm mt-1">
              Ask about your emails, calendar, or anything on your plate.
            </p>
          </div>
        </div>
      )}

      {state.messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}

      {isPending && (
        <div className="flex items-center gap-2 text-muted-foreground text-sm px-1">
          <span className="animate-pulse text-lg leading-none">●●●</span>
          <span>Working on it… (may take up to 30s)</span>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
