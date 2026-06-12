import {
  createContext,
  useContext,
  useReducer,
  type ReactNode,
} from "react";
import type { ChatMessage, OrchestratorResult } from "@/types/api";

interface SessionState {
  sessionId: string | null;
  messages: ChatMessage[];
}

type Action =
  | { type: "SET_SESSION_ID"; payload: string }
  | { type: "APPEND_MESSAGE"; payload: ChatMessage }
  | { type: "LOAD_SESSION"; payload: { sessionId: string; messages: ChatMessage[] } }
  | { type: "RESET_SESSION" };

interface SessionContextValue {
  state: SessionState;
  setSessionId: (id: string) => void;
  appendMessage: (msg: Omit<ChatMessage, "id" | "timestamp">) => void;
  appendResult: (result: OrchestratorResult) => void;
  loadSession: (sessionId: string, messages: ChatMessage[]) => void;
  resetSession: () => void;
}

const initialState: SessionState = { sessionId: null, messages: [] };

function reducer(state: SessionState, action: Action): SessionState {
  switch (action.type) {
    case "SET_SESSION_ID":
      return { ...state, sessionId: action.payload };
    case "APPEND_MESSAGE":
      return { ...state, messages: [...state.messages, action.payload] };
    case "LOAD_SESSION":
      return { sessionId: action.payload.sessionId, messages: action.payload.messages };
    case "RESET_SESSION":
      return initialState;
    default:
      return state;
  }
}

function makeId(): string {
  return Math.random().toString(36).slice(2);
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const setSessionId = (id: string) =>
    dispatch({ type: "SET_SESSION_ID", payload: id });

  const appendMessage = (msg: Omit<ChatMessage, "id" | "timestamp">) =>
    dispatch({
      type: "APPEND_MESSAGE",
      payload: { ...msg, id: makeId(), timestamp: new Date() },
    });

  const appendResult = (result: OrchestratorResult) => {
    dispatch({ type: "SET_SESSION_ID", payload: result.session_id });
    dispatch({
      type: "APPEND_MESSAGE",
      payload: {
        id: makeId(),
        role: "assistant",
        text: result.summary,
        result,
        timestamp: new Date(),
      },
    });
  };

  const loadSession = (sessionId: string, messages: ChatMessage[]) =>
    dispatch({ type: "LOAD_SESSION", payload: { sessionId, messages } });

  const resetSession = () => dispatch({ type: "RESET_SESSION" });

  return (
    <SessionContext.Provider
      value={{ state, setSessionId, appendMessage, appendResult, loadSession, resetSession }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be inside SessionProvider");
  return ctx;
}
