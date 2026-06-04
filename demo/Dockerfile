# Extends the official VHS image (Debian-based, bundles ttyd + ffmpeg + fonts)
# with python3 + a UTF-8 locale so the curses TUI's box-drawing glyphs render.
FROM ghcr.io/charmbracelet/vhs:latest

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 locales \
 && sed -i 's/^# *\(en_US.UTF-8 UTF-8\)/\1/' /etc/locale.gen \
 && locale-gen \
 && mkdir -p /home/dev/payments /home/dev/auth /home/dev/platform \
 && rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    TERM=xterm-256color

# Build context is the repo root (see build.sh), so cc-sessions is at ./cc-sessions
COPY cc-sessions /usr/local/bin/cc-sessions
RUN chmod +x /usr/local/bin/cc-sessions \
 && ln -sf /usr/local/bin/cc-sessions /usr/local/bin/csm

# Keep VHS's ENTRYPOINT (/usr/bin/vhs) intact.
WORKDIR /vhs
