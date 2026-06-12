import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

export function usePending() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["pending"],
    queryFn: api.listPending,
    refetchInterval: 30_000,
  });

  const approve = useMutation({
    mutationFn: api.approvePending,
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["pending"] }),
  });

  const reject = useMutation({
    mutationFn: api.rejectPending,
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["pending"] }),
  });

  const editDraft = useMutation({
    mutationFn: api.editDraft,
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["pending"] }),
  });

  return { query, approve, reject, editDraft };
}
