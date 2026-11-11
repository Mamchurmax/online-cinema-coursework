import { useQuery } from "@tanstack/react-query";

import { healthApi } from "../api/catalog";

/** Polls the backend health endpoint; used for the status badge in the footer. */
export function useApiHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => healthApi.check(signal),
    refetchInterval: 30_000,
    retry: false,
  });
}
