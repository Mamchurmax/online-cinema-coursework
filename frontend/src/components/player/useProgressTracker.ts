import { useQueryClient } from "@tanstack/react-query";
import { type RefObject, useEffect, useRef } from "react";

import { historyApi } from "../../api/history";

const SAVE_EVERY_SEC = 10;

/**
 * Saves the playback position to the watch history: every 10 s of playback,
 * on pause, at the end, and when the page is hidden or left (keepalive request).
 */
export function useProgressTracker(videoRef: RefObject<HTMLVideoElement | null>, videoAssetId: number) {
  const queryClient = useQueryClient();
  const lastSaved = useRef<number | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const save = (keepalive = false) => {
      const position = Math.floor(video.ended ? video.duration : video.currentTime);
      if (!Number.isFinite(position) || position === lastSaved.current) return;
      lastSaved.current = position;
      historyApi
        .saveProgress(videoAssetId, position, keepalive)
        .then(() => queryClient.invalidateQueries({ queryKey: ["history"] }))
        .catch(() => {
          lastSaved.current = null; // retry on the next tick
        });
    };

    const onTimeUpdate = () => {
      if (video.paused || video.seeking) return;
      if (lastSaved.current === null || Math.abs(video.currentTime - lastSaved.current) >= SAVE_EVERY_SEC) {
        save();
      }
    };
    const onPause = () => save();
    const onEnded = () => save();
    const onHidden = () => {
      if (document.visibilityState === "hidden") save(true);
    };
    const onPageHide = () => save(true);

    video.addEventListener("timeupdate", onTimeUpdate);
    video.addEventListener("pause", onPause);
    video.addEventListener("ended", onEnded);
    document.addEventListener("visibilitychange", onHidden);
    window.addEventListener("pagehide", onPageHide);
    return () => {
      video.removeEventListener("timeupdate", onTimeUpdate);
      video.removeEventListener("pause", onPause);
      video.removeEventListener("ended", onEnded);
      document.removeEventListener("visibilitychange", onHidden);
      window.removeEventListener("pagehide", onPageHide);
      if (video.currentTime > 0) save(true); // leaving the player inside the app
    };
  }, [videoRef, videoAssetId, queryClient]);
}
