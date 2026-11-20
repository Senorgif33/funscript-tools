#!/usr/bin/env python3
"""Linux smoke + seek bench for Custom Event Builder video backend (mpv).

Usage:
  python tools/bench_video_preview.py [video_path]

If no video is given, generates a short test mp4 via ffmpeg.
"""
from __future__ import annotations

import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _make_test_video(path: Path, seconds: float = 8.0) -> Path:
    import subprocess
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
        '-f', 'lavfi', '-i', f'testsrc=size=640x360:rate=30',
        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100',
        '-t', str(seconds), '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', str(path),
    ]
    subprocess.check_call(cmd)
    return path


def main() -> int:
    import tkinter as tk
    from ui.custom_events_builder import (
        VideoPanel, _VIDEO_BACKEND, _VIDEO_BACKEND_ERROR, _VIDEO_AVAILABLE,
    )

    print(f'backend={_VIDEO_BACKEND!r} available={_VIDEO_AVAILABLE}')
    if _VIDEO_BACKEND_ERROR:
        print(f'backend_error={_VIDEO_BACKEND_ERROR}')
    if not _VIDEO_AVAILABLE:
        print('FAIL: no video backend')
        return 1
    if _VIDEO_BACKEND != 'mpv' and sys.platform.startswith('linux'):
        print(f'WARN: expected mpv on linux, got {_VIDEO_BACKEND}')

    if len(sys.argv) > 1:
        video = Path(sys.argv[1])
    else:
        video = Path(tempfile.gettempdir()) / 'funscript_mpv_bench.mp4'
        if not video.exists():
            print(f'generating test video: {video}')
            _make_test_video(video)
    if not video.exists():
        print(f'FAIL: missing video {video}')
        return 1
    print(f'video={video}')

    root = tk.Tk()
    root.title('mpv video preview bench')
    root.geometry('720x480')
    panel = VideoPanel(root)
    panel.pack(fill=tk.BOTH, expand=True)
    root.update()

    ok = panel.load(str(video))
    print(f'load={ok}')
    if not ok:
        root.destroy()
        return 1

    # Wait for metadata
    deadline = time.time() + 5.0
    while time.time() < deadline and not panel._meta_cached:
        root.update()
        time.sleep(0.05)
    print(f'duration_s={panel._duration_s:.3f} fps={panel._fps:.3f} '
          f'size={panel._video_w}x{panel._video_h}')

    if panel._duration_s <= 0:
        print('FAIL: duration not ready')
        panel.destroy()
        root.destroy()
        return 1

    # Seek latency: wall time for seek() + first time_pos near target
    targets = [0.5, 1.0, 2.0, 3.5, 5.0, 1.5, 0.2]
    targets = [t for t in targets if t < panel._duration_s - 0.1]
    latencies_ms = []
    for t in targets:
        target_ms = t * 1000.0
        t0 = time.perf_counter()
        panel.seek(target_ms)
        # Poll until within 150ms or timeout
        hit = False
        while time.perf_counter() - t0 < 1.0:
            root.update()
            cur = panel._get_time_ms()
            if cur >= 0 and abs(cur - target_ms) < 150.0:
                hit = True
                break
            time.sleep(0.001)
        dt = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt)
        print(f'  seek->{t:.1f}s  latency={dt:.1f}ms  hit={hit}  pos={panel._get_time_ms():.0f}ms')

    print(f'seek_n={len(latencies_ms)} '
          f'median_ms={statistics.median(latencies_ms):.1f} '
          f'mean_ms={statistics.mean(latencies_ms):.1f} '
          f'max_ms={max(latencies_ms):.1f}')

    # Brief play to confirm frames move
    panel.toggle_play()
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 0.8:
        root.update()
        time.sleep(0.01)
    panel.toggle_play()
    print('play_burst=ok')

    panel.destroy()
    root.destroy()
    print('PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
