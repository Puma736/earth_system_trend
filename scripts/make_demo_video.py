"""Graba la demo de 28 s (docs/demo_en_28s.mp4 y docs/demo_es_28s.mp4) en una sola pasada.

Requisitos: backend en 127.0.0.1:8000 y front en 127.0.0.1:3000 ya levantados, ffmpeg,
y `pip install playwright edge-tts` + `playwright install chromium`.

    python scripts/make_demo_video.py

- Playwright recorre la app a 1920x1080 con una marca de agua fija inyectada en el DOM.
- edge-tts genera la locución (inglés y español) y ajusta la velocidad para que quepa.
- ffmpeg sintetiza un pad ambiental (aevalsrc, sin material de terceros) al 12 % y mezcla todo.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import edge_tts
from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
FRONT = "http://127.0.0.1:3000"
BACK = "http://127.0.0.1:8000"
DURATION = 28.0
VOICE_START = 0.25
VOICE_MAX = 27.2  # la locución termina antes de que acabe el video
BAR_CLICKS = (7, 16)  # barras de 2010 y 2019 (la serie empieza en 2003)
WATERMARK = "SI-Assisted Demo | AI Voiceover | Git's Children - NASA Space Apps 2026"

VOICES = {
    "en": (
        "en-US-AndrewNeural",
        "How is Bolivia's climate changing, and is it statistically significant? Meet Earth System Trend "
        "Detective. Powered by over forty years of NASA POWER MERRA-2 reanalysis and MODIS FIRMS fire data, "
        "our platform applies Hamed-Rao Mann-Kendall tests, Sen's slope, Pettitt change-points, and False "
        "Discovery Rate control across Santa Cruz and Bolivia—revealing how severe droughts drive wildfire "
        "hotspots and turning satellite data into local action.",
    ),
    "es": (
        "es-BO-MarceloNeural",
        "¿Cómo está cambiando el clima en Bolivia y qué tan significativo es para la ciencia? Presentamos "
        "Earth System Trend Detective. Con más de cuarenta años de datos satelitales de NASA POWER MERRA-2 y "
        "focos de calor MODIS FIRMS, aplicamos pruebas de Mann-Kendall con corrección Hamed-Rao, pendiente de "
        "Sen, puntos de cambio de Pettitt y control FDR en Santa Cruz y Bolivia, revelando cómo la sequía "
        "impulsa los incendios forestales.",
    ),
}

# Marca de agua, cursor visible y desplazamiento suave. Se reinyecta en cada navegación.
INIT_JS = """
(() => {
  const TEXT = %s;
  function ensure() {
    if (!document.body) return;
    if (!document.getElementById('si-watermark')) {
      const badge = document.createElement('div');
      badge.id = 'si-watermark';
      badge.textContent = TEXT;
      badge.style.cssText = 'position:fixed;top:14px;right:16px;z-index:2147483647;pointer-events:none;' +
        'padding:9px 16px;border-radius:999px;font:600 15px/1.2 system-ui,Segoe UI,Arial,sans-serif;' +
        'letter-spacing:.02em;color:#fff;background:rgba(10,12,20,.82);border:1px solid rgba(255,255,255,.35);' +
        'box-shadow:0 4px 18px rgba(0,0,0,.45);backdrop-filter:blur(6px);white-space:nowrap';
      document.body.appendChild(badge);
    }
    if (!document.getElementById('si-cursor')) {
      const dot = document.createElement('div');
      dot.id = 'si-cursor';
      dot.style.cssText = 'position:fixed;left:-50px;top:-50px;width:22px;height:22px;margin:-11px 0 0 -11px;' +
        'border-radius:50%%;z-index:2147483646;pointer-events:none;background:rgba(255,255,255,.35);' +
        'border:2px solid #fff;box-shadow:0 0 0 2px rgba(0,0,0,.4);transition:transform .12s';
      document.body.appendChild(dot);
    }
  }
  document.addEventListener('DOMContentLoaded', ensure);
  setInterval(ensure, 100);
  window.addEventListener('mousemove', (e) => {
    const dot = document.getElementById('si-cursor');
    if (dot) { dot.style.left = e.clientX + 'px'; dot.style.top = e.clientY + 'px'; }
  }, true);
  window.addEventListener('mousedown', () => {
    const dot = document.getElementById('si-cursor');
    if (dot) { dot.style.transform = 'scale(.6)'; setTimeout(() => (dot.style.transform = ''), 160); }
  }, true);
  window.__glide = (target, ms) => {
    const from = window.scrollY, t0 = performance.now();
    const step = (now) => {
      const k = Math.min(1, (now - t0) / ms);
      const eased = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      window.scrollTo(0, from + (target - from) * eased);
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };
})();
""" % json.dumps(WATERMARK)


def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def probe(path: Path) -> float:
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]))


def warm_backend() -> None:
    """Deja calculadas las respuestas que usa el recorrido, para que nada cargue en cámara."""
    for url in [f"{BACK}/health", FRONT]:
        urllib.request.urlopen(url, timeout=30).read()
    for season in ("DRY", "FIRE"):
        for path in ("drought", "hotspots", "link", "lead"):
            urllib.request.urlopen(f"{BACK}/api/{path}?region=santa-cruz&season={season}", timeout=180).read()


def record(workdir: Path) -> Path:
    """Graba el recorrido y devuelve el video ya recortado a DURATION segundos."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(workdir),
            record_video_size={"width": 1920, "height": 1080},
        )
        context.add_init_script(INIT_JS)

        # El backend recalcula cada consulta (hasta ~9 s en FIRE). El ensayo guarda sus
        # respuestas reales y el recorrido en cámara las recibe al instante.
        replay: dict[str, tuple[int, dict, bytes]] = {}

        def serve(route) -> None:
            url = route.request.url
            if route.request.method != "GET" or "/api/geocode" in url:
                route.continue_()
                return
            if url not in replay:
                response = route.fetch(timeout=180_000)
                if not response.ok:
                    route.fulfill(response=response)
                    return
                replay[url] = (response.status, response.headers, response.body())
            status, headers, body = replay[url]
            route.fulfill(status=status, headers=headers, body=body)

        context.route("**/api/**", serve)
        created = time.monotonic()
        page = context.new_page()
        # Ensayo fuera de cámara (se recorta después): el backend deja calculadas las mismas
        # consultas que hará el recorrido, con las provincias que manda el navegador.
        page.goto(f"{FRONT}/analisis", wait_until="networkidle")
        page.wait_for_selector(".recharts-bar-rectangle", timeout=120_000)
        page.locator(".mantine-SegmentedControl-label", has_text="Burning peak").click()
        page.wait_for_load_state("networkidle")
        page.wait_for_selector(".recharts-scatter-symbol", timeout=120_000)
        for index in BAR_CLICKS:
            box = page.locator(".recharts-bar-rectangle").nth(index).bounding_box()
            page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(400)
        page.goto(f"{FRONT}/", wait_until="networkidle")
        page.wait_for_timeout(1500)
        slow: list[str] = []
        page.on("requestfinished", lambda r: "/api/" in r.url and r.timing["responseEnd"] > 700
                and slow.append(f"{r.timing['responseEnd']:.0f} ms {r.url.split('/api/')[1][:60]}"))
        start = time.monotonic()

        def until(second: float) -> None:
            left = second - (time.monotonic() - start)
            if left > 0:
                page.wait_for_timeout(left * 1000)

        def click(locator, steps: int = 18) -> None:
            box = locator.bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=steps)
            page.wait_for_timeout(120)
            page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

        def glide(y: int, ms: int) -> None:
            page.evaluate("([y, ms]) => window.__glide(y, ms)", [y, ms])

        def top_of(text: str) -> int:
            return int(page.evaluate(
                "(t) => { const h = [...document.querySelectorAll('h2')].find(e => e.textContent.includes(t));"
                " return h ? h.getBoundingClientRect().top + scrollY : 0; }", text))

        # 0-8 s: portada y tablero con el mapa y los 6 indicadores de sequía (MERRA-2).
        until(1.8)
        click(page.get_by_role("link", name="Explorar análisis"))
        page.wait_for_selector("text=Is the region drying out?")
        until(4.6)
        glide(top_of("Is the region drying out?") - 40, 1500)
        until(7.6)

        # 8-16 s: época FIRE, focos FIRMS por año y grilla de 0.5°; clic en barras.
        glide(0, 600)
        until(8.4)
        click(page.locator(".mantine-SegmentedControl-label", has_text="Burning peak"))
        until(9.6)
        glide(top_of("More hotspots than before?") - 110, 1400)
        until(11.6)
        bars = page.locator(".recharts-bar-rectangle")
        click(bars.nth(BAR_CLICKS[0]))
        until(13.6)
        click(bars.nth(BAR_CLICKS[1]))
        until(15.6)

        # 16-22 s: puente sequía-fuego (Spearman) y prueba con una estación de anticipación.
        glide(top_of("Are drier years also fire years?") - 130, 1500)
        until(18.6)
        dots = page.locator(".recharts-scatter-symbol")
        if dots.count():
            click(dots.nth(dots.count() // 2), steps=25)
        until(21.6)

        # 22-28 s: laboratorio estadístico /investigation.
        glide(0, 350)
        until(22.0)
        click(page.get_by_role("link", name="Investigation"), steps=10)
        page.wait_for_selector("button[type=submit]")
        until(23.4)
        click(page.locator("button[type=submit]").first)
        until(25.6)
        glide(140, 1200)
        until(DURATION + 1.5)

        if slow:
            print("slow API calls on camera:", *slow, sep="\n  ")
        video = page.video
        context.close()
        raw = Path(video.path())
        browser.close()

    clip = workdir / "walkthrough.mp4"
    run(["ffmpeg", "-y", "-ss", f"{start - created:.3f}", "-i", str(raw), "-t", str(DURATION), "-an",
         "-vf", "fps=30,scale=1920:1080:flags=lanczos,format=yuv420p",
         "-c:v", "libx264", "-preset", "slow", "-crf", "20", str(clip)])
    return clip


def voiceover(lang: str, workdir: Path) -> Path:
    """Locución neural. Si no cabe en VOICE_MAX, sube la velocidad lo justo."""
    voice, text = VOICES[lang]
    out = workdir / f"voice_{lang}.mp3"
    rate = 0
    for _ in range(4):
        for attempt in range(4):  # el servicio a veces responde sin audio; se reintenta
            try:
                asyncio.run(edge_tts.Communicate(text, voice, rate=f"{rate:+d}%").save(str(out)))
                break
            except edge_tts.exceptions.NoAudioReceived:
                if attempt == 3:
                    raise
                time.sleep(2)
        length = probe(out)
        print(f"voice {lang}: {voice} rate {rate:+d}% -> {length:.2f}s")
        if length <= VOICE_MAX - VOICE_START:
            break
        rate = int((1 + rate / 100) * length / (VOICE_MAX - VOICE_START - 0.3) * 100 - 100) + 1
    return out


def mix(clip: Path, voice: Path, out: Path) -> None:
    # Pad ambiental sintetizado: acorde La menor con novena, con un vaivén lento. Sin samples.
    pad = (
        "aevalsrc='(sin(2*PI*110*t)+0.8*sin(2*PI*164.81*t)+0.7*sin(2*PI*220.3*t)+0.5*sin(2*PI*261.63*t)"
        "+0.4*sin(2*PI*329.63*t)+0.25*sin(2*PI*493.88*t))/3.65*(0.75+0.25*sin(2*PI*0.11*t))'"
        f":s=44100:d={DURATION}"
    )
    graph = (
        f"[1:a]aformat=channel_layouts=stereo,lowpass=f=1800,volume=0.12,"
        f"afade=t=in:d=1.5,afade=t=out:st={DURATION - 2}:d=2[pad];"
        f"[2:a]aformat=channel_layouts=stereo,adelay={int(VOICE_START * 1000)}:all=1[vo];"
        f"[pad][vo]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]"
    )
    run(["ffmpeg", "-y", "-i", str(clip), "-f", "lavfi", "-i", pad, "-i", str(voice),
         "-filter_complex", graph, "-map", "0:v", "-map", "[a]",
         "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-maxrate", "3500k", "-bufsize", "7000k",
         "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
         "-t", str(DURATION), "-movflags", "+faststart", str(out)])


def main() -> None:
    warm_backend()
    DOCS.mkdir(exist_ok=True)
    workdir = Path(tempfile.mkdtemp(prefix="demo_video_"))
    try:
        voices = {lang: voiceover(lang, workdir) for lang in VOICES}
        clip = record(workdir)
        for lang, voice in voices.items():
            out = DOCS / f"demo_{lang}_28s.mp4"
            mix(clip, voice, out)
            length = probe(out)
            size = out.stat().st_size / 1e6
            print(f"{out.relative_to(ROOT)}: {length:.3f}s, {size:.1f} MB")
            assert 27.0 <= length <= 28.5, f"{out.name} dura {length:.2f}s (debe estar entre 27.0 y 28.5)"
            assert size < 15, f"{out.name} pesa {size:.1f} MB (máximo 15)"
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
