import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useSession } from "@/store/sessionStore";

export function useOrchestrate() {
  const { state, appendMessage, appendResult } = useSession();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (message: string) =>
      api.orchestrate({
        message,
        session_id: state.sessionId ?? undefined,
      }),
    onMutate: (message: string) => {
      appendMessage({ role: "user", text: message });
    },
    onSuccess: (result) => {
      appendResult(result);
      void queryClient.invalidateQueries({ queryKey: ["pending"] });
      void queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
    onError: (err: Error) => {
      appendMessage({
        role: "error",
        text: `Something went wrong: ${err.message}`,
      });
    },
  });
}
