#!/usr/bin/env bash
# Convert a video file into HLS with several qualities and a master playlist.
#
# Usage:  transcode.sh INPUT OUTPUT_DIR
# Result: OUTPUT_DIR/master.m3u8
#         OUTPUT_DIR/<quality>/index.m3u8 + seg_00000.ts ...   (quality: 360p, 720p, 1080p)
#         OUTPUT_DIR/meta.json  {"qualities": [...], "duration_sec": N}
#
# Run inside the backend container (it has ffmpeg), e.g.:
#   docker compose run --rm backend bash scripts/transcode.sh \
#       /media/source/Sintel.2010.1080p.mkv /media/hls/sintel
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 INPUT OUTPUT_DIR" >&2
  exit 1
fi

input="$1"
output="$2"

# name  width  height  video_bitrate  max_rate  buffer
LADDER=(
  "360p   640  360  800k  856k  1200k"
  "720p  1280  720 2800k 2996k  4200k"
  "1080p 1920 1080 5000k 5350k  7500k"
)
SEGMENT_SECONDS=6
# A rendition is made when the source is at least this share of its width,
# so a 1024 px source still gets 720p but a 720p source never becomes 1080p.
MIN_SOURCE_SHARE=0.8

read -r src_width src_height < <(
  ffprobe -v error -select_streams v:0 -show_entries stream=width,height \
    -of default=noprint_wrappers=1:nokey=1 "$input" | paste -sd' '
)
duration=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$input")
has_audio=$(ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$input" | head -n1)

renditions=()
for rung in "${LADDER[@]}"; do
  read -r name width _ _ _ _ <<<"$rung"
  if awk -v s="$src_width" -v w="$width" -v k="$MIN_SOURCE_SHARE" 'BEGIN { exit !(s >= w * k) }'; then
    renditions+=("$rung")
  fi
done
if [[ ${#renditions[@]} -eq 0 ]]; then
  renditions=("${LADDER[0]}")  # tiny sources still get the lowest quality
fi

echo "Source: ${src_width}x${src_height}, ${duration}s, audio: $([[ -n "$has_audio" ]] && echo yes || echo no)"

split="[0:v]split=${#renditions[@]}"
filters=""
maps=()
stream_map=""
qualities=()
for i in "${!renditions[@]}"; do
  read -r name width height bitrate maxrate bufsize <<<"${renditions[$i]}"
  split+="[v$i]"
  # Fit into WxH keeping the aspect ratio (2.35:1 films stay letterbox-free).
  filters+=";[v$i]scale=w=$width:h=$height:force_original_aspect_ratio=decrease:force_divisible_by=2[v${i}out]"
  maps+=(-map "[v${i}out]" "-c:v:$i" libx264 "-b:v:$i" "$bitrate" "-maxrate:v:$i" "$maxrate" "-bufsize:v:$i" "$bufsize")
  if [[ -n "$has_audio" ]]; then
    maps+=(-map 0:a:0)
    stream_map+="v:$i,a:$i,name:$name "
  else
    stream_map+="v:$i,name:$name "
  fi
  qualities+=("\"$name\"")
done

rm -rf "$output"
mkdir -p "$output"

audio_args=()
if [[ -n "$has_audio" ]]; then
  audio_args=(-c:a aac -b:a 128k -ac 2)
fi

ffmpeg -hide_banner -loglevel warning -stats -y -i "$input" \
  -filter_complex "${split}${filters}" \
  "${maps[@]}" \
  "${audio_args[@]}" \
  -preset veryfast -profile:v main -pix_fmt yuv420p \
  -force_key_frames "expr:gte(t,n_forced*${SEGMENT_SECONDS})" -sc_threshold 0 \
  -f hls -hls_time "$SEGMENT_SECONDS" -hls_playlist_type vod -hls_flags independent_segments \
  -hls_segment_filename "$output/%v/seg_%05d.ts" \
  -master_pl_name master.m3u8 \
  -var_stream_map "${stream_map% }" \
  "$output/%v/index.m3u8"

printf '{"qualities": [%s], "duration_sec": %d}\n' \
  "$(IFS=,; echo "${qualities[*]}")" "${duration%.*}" >"$output/meta.json"

echo "Done: $output (qualities: ${qualities[*]})"
