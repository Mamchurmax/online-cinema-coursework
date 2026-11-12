// The light build has everything we use (no subtitles, DRM or alternate audio).
import Hls, { type ErrorData } from "hls.js/light";
import { type RefObject, useEffect, useRef, useState } from "react";

import { tokenStore } from "../../api/client";

export interface QualityLevel {
  index: number; // hls.js level index
  label: string; // "720p" — taken from the variant URL (…/720p/index.m3u8)
}

export interface HlsState {
  levels: QualityLevel[];
  currentLevel: number; // -1 while unknown
  autoLevel: boolean;
  error: string | null;
  setLevel: (index: number) => void; // -1 = automatic
}

/** Quality label from a variant URL; falls back to the picture height. */
function levelLabel(url: string | undefined, height: number): string {
  const match = url?.match(/\/(\d+p)\/[^/]*$/);
  return match ? match[1] : `${height}p`;
}

function describeError(data: ErrorData): string {
  const status = data.response?.code;
  if (status === 401) return "Сесія завершилася. Увійдіть знову.";
  if (status === 403) return "Ваш тариф не дозволяє переглядати це відео.";
  if (status === 404) return "Відеофайли не знайдено.";
  return "Не вдалося відтворити відео. Перевірте з'єднання та спробуйте ще раз.";
}

/**
 * Attaches an HLS stream to a <video>. Requests to our API (the plan-filtered
 * master playlist) carry the JWT; static segments under /media do not need it.
 */
export function useHls(videoRef: RefObject<HTMLVideoElement | null>, src: string | null): HlsState {
  const hlsRef = useRef<Hls | null>(null);
  const [levels, setLevels] = useState<QualityLevel[]>([]);
  const [currentLevel, setCurrentLevel] = useState(-1);
  const [autoLevel, setAutoLevel] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !src) return;
    setLevels([]);
    setCurrentLevel(-1);
    setAutoLevel(true);
    setError(null);

    if (!Hls.isSupported()) {
      // Native HLS (Safari) cannot send the Authorization header to our API.
      setError("Цей браузер не підтримує відтворення. Спробуйте Chrome, Firefox або Edge.");
      return;
    }

    const hls = new Hls({
      xhrSetup: (xhr, url) => {
        const token = tokenStore.get();
        if (token && new URL(url, window.location.origin).pathname.startsWith("/api/")) {
          xhr.setRequestHeader("Authorization", `Bearer ${token}`);
        }
      },
    });
    hlsRef.current = hls;

    hls.on(Hls.Events.MANIFEST_PARSED, (_event, data) => {
      setLevels(
        data.levels
          .map((level, index) => ({ index, label: levelLabel(level.url[0], level.height) }))
          .sort((a, b) => parseInt(a.label) - parseInt(b.label)),
      );
    });
    hls.on(Hls.Events.LEVEL_SWITCHED, (_event, data) => {
      setCurrentLevel(data.level);
      setAutoLevel(hls.autoLevelEnabled);
    });
    hls.on(Hls.Events.ERROR, (_event, data) => {
      if (data.fatal) {
        setError(describeError(data));
        hls.destroy();
      }
    });

    hls.loadSource(src);
    hls.attachMedia(video);
    return () => {
      hls.destroy();
      hlsRef.current = null;
    };
  }, [videoRef, src]);

  const setLevel = (index: number) => {
    const hls = hlsRef.current;
    if (!hls) return;
    hls.currentLevel = index; // switches immediately; -1 returns to automatic choice
    setAutoLevel(index === -1);
  };

  return { levels, currentLevel, autoLevel, error, setLevel };
}
