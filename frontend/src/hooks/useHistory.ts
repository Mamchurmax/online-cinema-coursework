import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { historyApi } from "../api/history";
import { useAuth } from "../auth/AuthProvider";

// Keys start with "history": they are dropped on sign-out (see AuthProvider).
export function useContinueWatching() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["history", "continue", user?.id],
    queryFn: ({ signal }) => historyApi.continueWatching(signal),
    enabled: Boolean(user),
    staleTime: 0,
  });
}

export function useWatchHistory() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["history", "all", user?.id],
    queryFn: ({ signal }) => historyApi.list(signal),
    enabled: Boolean(user),
    staleTime: 0,
  });
}

export function useRemoveFromHistory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (videoAssetId: number) => historyApi.remove(videoAssetId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["history"] }),
  });
}
