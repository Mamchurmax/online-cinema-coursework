import type { TitleType } from "../api/types";

export const TITLE_TYPE_LABEL: Record<TitleType, string> = {
  movie: "Фільм",
  series: "Серіал",
};

/** 136 -> "2 год 16 хв", 45 -> "45 хв". */
export function formatDuration(minutes: number | null): string | null {
  if (!minutes) return null;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (!hours) return `${rest} хв`;
  return rest ? `${hours} год ${rest} хв` : `${hours} год`;
}

/** 75 -> "1:15", 3725 -> "1:02:05". */
export function formatClock(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = String(seconds % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${s}` : `${m}:${s}`;
}

/** "8.20" -> "8.2"; null -> null. */
export function formatRating(rating: string | null): string | null {
  if (rating === null) return null;
  const value = Number(rating);
  return Number.isFinite(value) ? value.toFixed(1) : null;
}

/** Ukrainian plural: plural(5, ["тайтл", "тайтли", "тайтлів"]) -> "тайтлів". */
export function plural(count: number, [one, few, many]: [string, string, string]): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}
