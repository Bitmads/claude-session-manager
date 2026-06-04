#!/usr/bin/env bash
# Compose the polished launch video from picker.mp4:
#   intro card  →  captioned demo  →  CTA card   (crossfaded, 1080p, silent)
# Runs ffmpeg inside the csm-vhs image (ffmpeg 7 + DejaVu fonts). Re-execs
# itself in the container when run from the host.
#   Usage:  cd demo && ./make_video.sh        (needs picker.mp4 + csm-vhs image)
set -euo pipefail

if [ "${IN_CONTAINER:-}" != "1" ]; then
  cd "$(dirname "$0")"
  [ -f picker.mp4 ] || { echo "picker.mp4 missing — run ./build.sh first"; exit 1; }
  exec docker run --rm -e IN_CONTAINER=1 -v "$PWD":/vhs --entrypoint bash csm-vhs /vhs/make_video.sh
fi

cd /vhs
FB=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
FR=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
BG=0x1e1e2e
BOX="box=1:boxcolor=0x11111b@0.72:boxborderw=18"
Q="-y -loglevel error"

# 1) intro / hook card (3.5s)
ffmpeg $Q -f lavfi -i color=c=$BG:s=1920x1080:r=25:d=3.5 -vf "
drawtext=fontfile=$FB:text='Claude Code has no session manager.':fontcolor=white:fontsize=56:x=(w-text_w)/2:y=(h/2)-70,
drawtext=fontfile=$FB:text='So I built one.':fontcolor=0x89dceb:fontsize=46:x=(w-text_w)/2:y=(h/2)+15,
fade=t=in:st=0:d=0.5,fade=t=out:st=3.0:d=0.5,setsar=1,format=yuv420p" -an _intro.mp4

# 2) CTA / outro card (4.5s)
ffmpeg $Q -f lavfi -i color=c=$BG:s=1920x1080:r=25:d=4.5 -vf "
drawtext=fontfile=$FB:text='csm':fontcolor=white:fontsize=110:x=(w-text_w)/2:y=(h/2)-175,
drawtext=fontfile=$FR:text='Claude Code session manager':fontcolor=0xcdd6f4:fontsize=42:x=(w-text_w)/2:y=(h/2)-35,
drawtext=fontfile=$FB:text='github.com/Bitmads/claude-session-manager':fontcolor=0x89dceb:fontsize=38:x=(w-text_w)/2:y=(h/2)+55,
drawtext=fontfile=$FR:text='Python stdlib only - no dependencies':fontcolor=0xa6adc8:fontsize=30:x=(w-text_w)/2:y=(h/2)+125,
fade=t=in:st=0:d=0.5,fade=t=out:st=4.0:d=0.5,setsar=1,format=yuv420p" -an _outro.mp4

# 3) demo scaled to 1080p + lower-third captions (timed to the walkthrough)
ffmpeg $Q -i picker.mp4 -vf "
scale=1920:1080:force_original_aspect_ratio=decrease,
pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=$BG,setsar=1,
drawtext=fontfile=$FB:text='Sessions grouped by task':fontcolor=white:fontsize=40:$BOX:x=(w-text_w)/2:y=h-150:enable='between(t,0.6,4.4)',
drawtext=fontfile=$FB:text='Scope - this folder, or everything':fontcolor=white:fontsize=40:$BOX:x=(w-text_w)/2:y=h-150:enable='between(t,4.8,6.6)',
drawtext=fontfile=$FB:text='Fuzzy-find across every project':fontcolor=white:fontsize=40:$BOX:x=(w-text_w)/2:y=h-150:enable='between(t,6.9,9.4)',
drawtext=fontfile=$FB:text='Four views - grouped or flat, by date or A to Z':fontcolor=white:fontsize=40:$BOX:x=(w-text_w)/2:y=h-150:enable='between(t,10.4,15.2)',
drawtext=fontfile=$FB:text='Cycle status with one keystroke':fontcolor=white:fontsize=40:$BOX:x=(w-text_w)/2:y=h-150:enable='between(t,15.5,17.9)',
drawtext=fontfile=$FB:text='Rename inline - never leave the picker':fontcolor=white:fontsize=40:$BOX:x=(w-text_w)/2:y=h-150:enable='between(t,18.2,20.9)',
drawtext=fontfile=$FB:text='Notes, branch and context in the detail panel':fontcolor=white:fontsize=40:$BOX:x=(w-text_w)/2:y=h-150:enable='between(t,22.6,26.6)',
fade=t=in:st=0:d=0.4,format=yuv420p" -an _demo.mp4

# 4) stitch with crossfades  (intro 3.5 ⨯ demo 26.92 ⨯ outro 4.5, 0.5s fades)
ffmpeg $Q -i _intro.mp4 -i _demo.mp4 -i _outro.mp4 -filter_complex "
[0][1]xfade=transition=fade:duration=0.5:offset=3.0[a];
[a][2]xfade=transition=fade:duration=0.5:offset=29.42[v]" \
  -map "[v]" -r 25 -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -movflags +faststart launch.mp4

rm -f _intro.mp4 _outro.mp4 _demo.mp4
echo "✓ launch.mp4"
