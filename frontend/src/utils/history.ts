import type { HistoryEntry } from "../api/types";

/** Where a history item leads: movies open the player, episodes the series page. */
export function historyLink(entry: HistoryEntry): string {
  return entry.episode ? `/titles/${entry.title_id}` : `/watch/${entry.title_id}`;
}

export function minutesLeft(entry: HistoryEntry): string {
  if (entry.completed) return "Переглянуто";
  const minutes = Math.max(1, Math.round((entry.duration_sec - entry.progress_sec) / 60));
  return `Залишилось ${minutes} хв`;
}
