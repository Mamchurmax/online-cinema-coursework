import type { HistoryEntry } from "../api/types";

/** Where a history item leads: straight back into the player (movie or episode). */
export function historyLink(entry: HistoryEntry): string {
  return entry.episode ? `/watch/${entry.title_id}?episode=${entry.episode.id}` : `/watch/${entry.title_id}`;
}

export function minutesLeft(entry: HistoryEntry): string {
  if (entry.completed) return "Переглянуто";
  const minutes = Math.max(1, Math.round((entry.duration_sec - entry.progress_sec) / 60));
  return `Залишилось ${minutes} хв`;
}
