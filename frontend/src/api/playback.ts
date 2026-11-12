import { apiGet } from "./client";
import type { PlaybackInfo } from "./types";

export const playbackApi = {
  startTitle: (titleId: number, signal?: AbortSignal) =>
    apiGet<PlaybackInfo>(`/playback/titles/${titleId}`, undefined, signal),
  startEpisode: (episodeId: number, signal?: AbortSignal) =>
    apiGet<PlaybackInfo>(`/playback/episodes/${episodeId}`, undefined, signal),
};
