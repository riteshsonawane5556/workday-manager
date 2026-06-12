export interface OrchestratorRequest {
  message: string;
  session_id?: string;
}

export interface ProcessingResult {
  processed: number;
  actionable: number;
  pending_ids: string[];
}

export interface CalendarActionResult {
  description: string;
  executed: boolean;
  awaiting_user: boolean;
}

export interface OrchestratorResult {
  summary: string;
  session_id: string;
  email_result: ProcessingResult | null;
  calendar_action_result: CalendarActionResult | null;
  clarification_question: string | null;
}

export interface DraftReply {
  subject: string;
  body: string;
  to: string;
}

export interface PendingItem {
  id: string;
  email_id: string;
  subject: string;
  sender: string;
  draft: DraftReply;
}

export interface HealthStatus {
  status: string;
  nylas: string;
}

export interface SessionSummary {
  session_id: string;
  session_name: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface SessionTurn {
  role_user: string;
  role_assistant: string;
}

export interface SessionHistory {
  session_id: string;
  turns: SessionTurn[];
}

export type MessageRole = "user" | "assistant" | "error";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  text: string;
  result?: OrchestratorResult;
  timestamp: Date;
}
