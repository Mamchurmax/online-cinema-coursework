import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router";

import type { PlaybackInfo } from "../../api/types";
import { formatClock } from "../../utils/format";
import { useHls } from "./useHls";
import { useProgressTracker } from "./useProgressTracker";

interface VideoPlayerProps {
  info: PlaybackInfo;
  title: string;
  poster?: string | null;
}

type Phase = "ad" | "main";

export function VideoPlayer({ info, title, poster }: VideoPlayerProps) {
  const [phase, setPhase] = useState<Phase>(info.ad ? "ad" : "main");
  const finishAd = useCallback(() => setPhase("main"), []);

  return (
    <div className="player">
      {phase === "ad" && info.ad ? (
        <AdPlayer url={info.ad.url} name={info.ad.name} onFinished={finishAd} />
      ) : (
        <MainPlayer info={info} title={title} poster={poster} />
      )}
    </div>
  );
}

/** Pre-roll ad: cannot be skipped or seeked; the film starts when it ends. */
function AdPlayer({ url, name, onFinished }: { url: string; name: string; onFinished: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const { error } = useHls(videoRef, url);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [needsClick, setNeedsClick] = useState(false);

  // A broken ad must never block the film.
  useEffect(() => {
    if (error) onFinished();
  }, [error, onFinished]);

  const start = () => {
    videoRef.current
      ?.play()
      .then(() => setNeedsClick(false))
      .catch(() => setNeedsClick(true)); // autoplay with sound was blocked by the browser
  };

  return (
    <div className="player__stage">
      <video
        ref={videoRef}
        className="player__video"
        playsInline
        onCanPlay={start}
        onTimeUpdate={(e) => {
          const video = e.currentTarget;
          if (video.duration) setRemaining(Math.max(0, Math.ceil(video.duration - video.currentTime)));
        }}
        onEnded={onFinished}
        onContextMenu={(e) => e.preventDefault()}
      />
      <div className="player__ad-badge">
        Реклама{remaining !== null && ` · ${remaining} с`}
        <span className="player__ad-name">{name}</span>
      </div>
      <div className="player__ad-hint">Фільм почнеться автоматично. Premium — без реклами.</div>
      {needsClick && (
        <button className="player__start" onClick={start}>
          ▶ Почати
        </button>
      )}
    </div>
  );
}

function MainPlayer({ info, title, poster }: { info: PlaybackInfo; title: string; poster?: string | null }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hls = useHls(videoRef, info.master_url);
  useProgressTracker(videoRef, info.asset_id);

  // Continue from where the viewer stopped last time, with a way back to the start.
  const resumeAt = info.resume_position_sec;
  const [showResume, setShowResume] = useState(resumeAt > 0);
  const resumed = useRef(false);
  useEffect(() => {
    if (!showResume) return;
    const timer = setTimeout(() => setShowResume(false), 8000);
    return () => clearTimeout(timer);
  }, [showResume]);

  return (
    <>
      <div className="player__stage">
        <video
          ref={videoRef}
          className="player__video"
          controls
          playsInline
          autoPlay // the viewer has just pressed "Watch"; if the browser blocks it, controls remain
          poster={poster ?? undefined}
          aria-label={title}
          onLoadedMetadata={(event) => {
            if (resumeAt > 0 && !resumed.current) {
              resumed.current = true;
              event.currentTarget.currentTime = resumeAt;
            }
          }}
        />
        {showResume && (
          <div className="player__resume" role="status">
            Продовжуємо з {formatClock(resumeAt)}
            <button
              className="button button--ghost button--small"
              onClick={() => {
                if (videoRef.current) videoRef.current.currentTime = 0;
                setShowResume(false);
              }}
            >
              З початку
            </button>
          </div>
        )}
        {hls.error && (
          <div className="player__error" role="alert">
            {hls.error}
          </div>
        )}
      </div>
      <QualityBar info={info} hls={hls} />
    </>
  );
}

function QualityBar({ info, hls }: { info: PlaybackInfo; hls: ReturnType<typeof useHls> }) {
  const playing = hls.levels.find((level) => level.index === hls.currentLevel)?.label;

  return (
    <div className="quality-bar">
      <span className="quality-bar__label">Якість</span>
      <div className="segmented" role="group" aria-label="Якість відео">
        <button
          className={`segmented__item ${hls.autoLevel ? "segmented__item--active" : ""}`}
          aria-pressed={hls.autoLevel}
          onClick={() => hls.setLevel(-1)}
        >
          Авто{hls.autoLevel && playing ? ` (${playing})` : ""}
        </button>
        {hls.levels.map((level) => {
          const active = !hls.autoLevel && level.index === hls.currentLevel;
          return (
            <button
              key={level.index}
              className={`segmented__item ${active ? "segmented__item--active" : ""}`}
              aria-pressed={active}
              onClick={() => hls.setLevel(level.index)}
            >
              {level.label}
            </button>
          );
        })}
        {info.locked_qualities.map((quality) => (
          <button
            key={quality}
            className="segmented__item segmented__item--locked"
            disabled
            title="Доступно на тарифі Premium"
          >
            🔒 {quality}
          </button>
        ))}
      </div>
      <span className="quality-bar__plan">
        Тариф {info.plan_name}: до {info.max_quality}
        {info.locked_qualities.length > 0 && (
          <>
            {" · "}
            <Link to="/plans" className="link">
              Premium
            </Link>{" "}
            відкриває {info.locked_qualities.join(", ")} і прибирає рекламу
          </>
        )}
      </span>
    </div>
  );
}
