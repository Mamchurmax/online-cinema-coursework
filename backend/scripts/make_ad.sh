#!/usr/bin/env bash
# Generate a short demo pre-roll ad (no external footage needed) and convert it to HLS.
#
# Usage:  make_ad.sh OUTPUT_DIR [SECONDS]
#   docker compose run --rm backend bash scripts/make_ad.sh /media/hls/ads/demo
set -euo pipefail

output="${1:?Usage: $0 OUTPUT_DIR [SECONDS]}"
seconds="${2:-10}"
font=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
source_file="$(mktemp --suffix=.mp4)"
trap 'rm -f "$source_file"' EXIT

# Moving gradient background, a title and a countdown, plus a quiet tone.
ffmpeg -hide_banner -loglevel warning -y \
  -f lavfi -i "gradients=s=1280x720:c0=0xe5484d:c1=0x1b1f2a:x0=0:y0=0:x1=1280:y1=720:speed=0.02:d=${seconds}:r=24" \
  -f lavfi -i "sine=frequency=440:sample_rate=48000:duration=${seconds}" \
  -filter_complex "[0:v]drawtext=fontfile=${font}:text='Кінотеатр Premium':fontsize=72:fontcolor=white:x=(w-tw)/2:y=h/2-90,\
drawtext=fontfile=${font}:text='Дивіться без реклами у 1080p':fontsize=40:fontcolor=white@0.9:x=(w-tw)/2:y=h/2+10,\
drawtext=fontfile=${font}:text='Реклама\\: %{eif\\:${seconds}-t\\:d}':fontsize=28:fontcolor=white@0.8:x=w-tw-40:y=40[v];\
[1:a]volume=0.05[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset veryfast -pix_fmt yuv420p -c:a aac -b:a 96k \
  -t "$seconds" "$source_file"

"$(dirname "$0")/transcode.sh" "$source_file" "$output"
