import { useState } from "react";

interface PosterProps {
  src: string | null;
  title: string;
  className?: string;
}

/** Poster image with a neutral placeholder when there is no image or it fails to load. */
export function Poster({ src, title, className = "" }: PosterProps) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return (
      <div className={`poster poster--empty ${className}`} role="img" aria-label={title}>
        <span>{title.slice(0, 1).toUpperCase()}</span>
      </div>
    );
  }

  return (
    <img
      className={`poster ${className}`}
      src={src}
      alt={title}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}
