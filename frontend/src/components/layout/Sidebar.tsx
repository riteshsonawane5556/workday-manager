import { useEffect, useState } from "react";
import { PlusCircle, BriefcaseBusiness, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSession } from "@/store/sessionStore";
import { useSessions } from "@/hooks/useSessions";
import { api } from "@/api/client";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types/api";

export function Sidebar() {
  const { state, loadSession, resetSession } = useSession();
  const [nylasOk, setNylasOk] = useState<boolean | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const { data: sessions } = useSessions();

  useEffect(() => {
    api
      .health()
      .then((h) => setNylasOk(h.nylas === "connected"))
      .catch(() => setNylasOk(false));
  }, []);

  async function handleSessionClick(sessionId: string) {
    if (sessionId === state.sessionId || loadingId) return;
    setLoadingId(sessionId);
    try {
      const history = await api.getSessionHistory(sessionId);
      const messages: ChatMessage[] = history.turns.flatMap((turn) => [
        {
          id: Math.random().toString(36).slice(2),
          role: "user" as const,
          text: turn.role_user,
          timestamp: new Date(),
        },
        {
          id: Math.random().toString(36).slice(2),
          role: "assistant" as const,
          text: turn.role_assistant,
          timestamp: new Date(),
        },
      ]);
      loadSession(sessionId, messages);
    } catch {
      // silently ignore — network errors etc
    } finally {
      setLoadingId(null);
    }
  }

  return (
    <div className="flex h-full w-64 flex-col border-r bg-muted/30">
      <div className="flex items-center gap-2 border-b px-4 py-4">
        <BriefcaseBusiness className="h-5 w-5 text-primary" />
        <span className="font-semibold text-sm">Workday Manager</span>
        <span
          className={cn(
            "ml-auto h-2 w-2 rounded-full",
            nylasOk === null && "bg-gray-300",
            nylasOk === true && "bg-green-500",
            nylasOk === false && "bg-red-500"
          )}
          title={
            nylasOk === null
              ? "Checking…"
              : nylasOk
              ? "Nylas connected"
              : "Nylas error"
          }
        />
      </div>

      <div className="p-3">
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2"
          onClick={resetSession}
        >
          <PlusCircle className="h-4 w-4" />
          New Chat
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-1">
        {sessions && sessions.length > 0 && (
          <>
            <p className="px-2 py-1 text-[10px] text-muted-foreground uppercase tracking-wide">
              Sessions
            </p>
            {sessions.map((s) => (
              <button
                key={s.session_id}
                onClick={() => void handleSessionClick(s.session_id)}
                disabled={!!loadingId}
                className={cn(
                  "w-full text-left rounded-md px-2 py-2 text-xs flex items-start gap-2 hover:bg-muted transition-colors",
                  state.sessionId === s.session_id && "bg-muted font-medium",
                  loadingId === s.session_id && "opacity-60"
                )}
              >
                <MessageSquare className="h-3 w-3 mt-0.5 shrink-0 text-muted-foreground" />
                <span className="truncate">
                  {s.session_name ?? s.session_id.slice(0, 8) + "…"}
                </span>
              </button>
            ))}
          </>
        )}
      </div>

      <div className="border-t px-4 py-3">
        <p className="text-[10px] text-muted-foreground">
          {state.messages.length} message
          {state.messages.length !== 1 ? "s" : ""} this session
        </p>
      </div>
    </div>
  );
}
