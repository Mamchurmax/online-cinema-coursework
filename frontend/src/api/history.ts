import { apiGet, apiRequest } from "./client";
import type { HistoryEntry } from "./types";

export const historyApi = {
  saveProgress: (videoAssetId: number, positionSec: number, keepalive = false) =>
    apiRequest<HistoryEntry>("PUT", `/me/history/${videoAssetId}`, {
      json: { position_sec: Math.max(0, Math.floor(positionSec)) },
      keepalive,
    }),
  list: (signal?: AbortSignal) => apiGet<HistoryEntry[]>("/me/history", { limit: 100 }, signal),
  continueWatching: (signal?: AbortSignal) => apiGet<HistoryEntry[]>("/me/continue-watching", undefined, signal),
  remove: (videoAssetId: number) => apiRequest<void>("DELETE", `/me/history/${videoAssetId}`),
};
