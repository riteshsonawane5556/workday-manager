import { EmailTriageCard } from "@/components/cards/EmailTriageCard";
import { CalendarActionCard } from "@/components/cards/CalendarActionCard";
import { formatTime } from "@/utils/time";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types/api";

interface Props {
  message: ChatMessage;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  const isError = message.role === "error";

  return (
    <div className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-4 py-3 text-sm",
          isUser && "bg-primary text-primary-foreground rounded-br-sm",
          !isUser && !isError && "bg-muted text-foreground rounded-bl-sm",
          isError && "bg-red-50 text-red-700 border border-red-200 rounded-bl-sm"
        )}
      >
        <p className="whitespace-pre-wrap leading-relaxed">{message.text}</p>

        {message.result?.email_result && (
          <EmailTriageCard result={message.result.email_result} />
        )}

        {message.result?.calendar_action_result && (
          <CalendarActionCard result={message.result.calendar_action_result} />
        )}

        {message.result?.clarification_question && (
          <div className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            <span className="font-semibold">Clarification needed: </span>
            {message.result.clarification_question}
          </div>
        )}

        <p
          className={cn(
            "mt-1 text-right text-[10px]",
            isUser ? "text-primary-foreground/60" : "text-muted-foreground"
          )}
        >
          {formatTime(message.timestamp)}
        </p>
      </div>
    </div>
  );
}
