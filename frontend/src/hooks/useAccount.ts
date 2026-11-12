import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { billingApi, favoritesApi, notificationsApi } from "../api/billing";
import { useAuth } from "../auth/AuthProvider";

/** Query keys of everything that changes after a payment. */
export const AFTER_PAYMENT_KEYS = [["subscription"], ["payments"], ["notifications"], ["playback"]];

export function usePlans() {
  return useQuery({ queryKey: ["plans"], queryFn: ({ signal }) => billingApi.plans(signal), staleTime: 5 * 60_000 });
}

export function useMySubscription() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["subscription", user?.id],
    queryFn: ({ signal }) => billingApi.mySubscription(signal),
    enabled: Boolean(user),
  });
}

export function useMyPayments() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["payments", user?.id],
    queryFn: ({ signal }) => billingApi.myPayments(signal),
    enabled: Boolean(user),
    staleTime: 0,
  });
}

export function useNotifications() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["notifications", user?.id],
    queryFn: ({ signal }) => notificationsApi.list(signal),
    enabled: Boolean(user),
    refetchInterval: 30_000, // the bell picks up "subscription ends soon" without a reload
  });
}

export function useMarkNotificationsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });
}

export function useFavoriteIds() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["favorites", "ids", user?.id],
    queryFn: ({ signal }) => favoritesApi.ids(signal),
    enabled: Boolean(user),
    select: (ids) => new Set(ids),
  });
}

export function useFavorites() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["favorites", "list", user?.id],
    queryFn: ({ signal }) => favoritesApi.list(signal),
    enabled: Boolean(user),
    staleTime: 0,
  });
}

export function useToggleFavorite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ titleId, add }: { titleId: number; add: boolean }) =>
      add ? favoritesApi.add(titleId) : favoritesApi.remove(titleId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["favorites"] }),
  });
}
