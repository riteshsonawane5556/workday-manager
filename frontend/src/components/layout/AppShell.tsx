import { useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { PendingPanel } from "@/components/layout/PendingPanel";
import { ChatArea } from "@/components/chat/ChatArea";
import { ChatInput } from "@/components/chat/ChatInput";

export function AppShell() {
  const [isThinking, setIsThinking] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <ChatArea isPending={isThinking} />
        <ChatInput onPendingChange={setIsThinking} />
      </div>
      <PendingPanel />
    </div>
  );
}
