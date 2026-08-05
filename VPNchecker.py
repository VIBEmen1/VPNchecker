import asyncio
import base64
import html as html_module
import socket
import time
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from urllib.parse import urlparse, unquote

import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box

console = Console()


_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": _UA,
    "Accept": "text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "DNT": "1",
    "Connection": "close",
})
# Не сохраняем cookies между запросами
_SESSION.cookies.clear()

# === ПУТИ (рабочий стол) ===
def get_desktop_path() -> Path:
    home = Path.home()
    desktop = home / "Desktop"
    if not desktop.exists():
        desktop = home / "Рабочий стол"
        if not desktop.exists():
            desktop = Path(__file__).parent.resolve()
    return desktop

HTML_OUTPUT = get_desktop_path() / "working_keys.html"


BLACK_URL = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt"
BLACK_MOBILE_URL = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS_mobile.txt"
WHITE_URL = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-checked.txt"
WHITE_SNI_ALL_URL = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt"
WHITE_CIDR_ALL_URL = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt"
WHITE_MOBILE_REALITY_URL = "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt"

EXTRA_URLS = [
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/main/extra_converted_for_mirror.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/main/mermeroo_extra_sources.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/main/mermeroo_only_new_for_mirror.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/main/proxy_collect_extra_sources.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/main/proxy_collect_only_new_for_mirror.txt",
]

MAX_CONCURRENT_CHECKS = 50
TEST_TIMEOUT = 5.0
MAX_LATENCY_MS = 2000

COUNTRIES = {
    "Baltics":     ["lithuania", "estonia", "latvia"],
    "Finland":     ["finland"],
    "Germany":     ["germany"],
    "Sweden":      ["sweden"],
    "Netherlands": ["netherlands"],
    "Poland":      ["poland"],
}
COUNTRIES_ALL_KEYWORDS = [kw for kws in COUNTRIES.values() for kw in kws]
SKIP_COUNTRY_NAMES = {"anycast", "anycast-ip", "unknown"}
COUNTRY_PATTERN = re.compile(
    r'([A-Z][A-Za-z\u00C0-\u017E](?:[A-Za-z\u00C0-\u017E\s\-]*[A-Za-z\u00C0-\u017E])?)(?:\s*[,|])'
)



def play_beep():
    try:
        if sys.platform == "win32":
            import winsound
            winsound.Beep(1000, 400)
        else:
            print('\a', end='', flush=True)
    except Exception:
        pass



def copy_to_clipboard(text: str) -> bool:
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        pass
    try:
        import subprocess
        p = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
        p.communicate(text.encode('utf-8'))
        return p.returncode == 0
    except Exception:
        pass
    try:
        import subprocess
        p = subprocess.Popen(['xsel', '--clipboard', '--input'], stdin=subprocess.PIPE)
        p.communicate(text.encode('utf-8'))
        return p.returncode == 0
    except Exception:
        return False



def show_menu() -> Dict[str, Any]:
    console.clear()
    banner = """
 ██▒   █▓ ██▓███   ███▄    █  ▄████▄   ██░ ██ ▓█████  ▄████▄   ██ ▄█▀▓█████  ██▀███  
▓██░   █▒▓██░  ██▒ ██ ▀█   █ ▒██▀ ▀█  ▓██░ ██▒▓█   ▀ ▒██▀ ▀█   ██▄█▒ ▓█   ▀ ▓██ ▒ ██▒
 ▓██  █▒░▓██░ ██▓▒▓██  ▀█ ██▒▒▓█    ▄ ▒██▀▀██░▒███   ▒▓█    ▄ ▓███▄░ ▒███   ▓██ ░▄█ ▒
  ▒██ █░░▒██▄█▓▒ ▒▓██▒  ▐▌██▒▒▓▓▄ ▄██▒░▓█ ░██ ▒▓█  ▄ ▒▓▓▄ ▄██▒▓██ █▄ ▒▓█  ▄ ▒██▀▀█▄  
   ▒▀█░  ▒██▒ ░  ░▒██░   ▓██░▒ ▓███▀ ░░▓█▒░██▓░▒████▒▒ ▓███▀ ░▒██▒ █▄░▒████▒░██▓ ▒██▒
   ░ ▐░  ▒▓▒░ ░  ░░ ▒░   ▒ ▒ ░ ░▒ ▒  ░ ▒ ░░▒░▒░░ ▒░ ░░ ░▒ ▒  ░▒ ▒▒ ▓▒░░ ▒░ ░░ ▒▓ ░▒▓░
   ░ ░░  ░▒ ░     ░ ░░   ░ ▒░  ░  ▒    ▒ ░▒░ ░ ░ ░  ░  ░  ▒   ░ ░▒ ▒░ ░ ░  ░  ░▒ ░ ▒░
    """
    lines = banner.strip("\n").split("\n")
    colors = ["#ff0055", "#ff00aa", "#aa00ff", "#5500ff", "#0055ff", "#00aaff", "#00ffaa"]
    for i, line in enumerate(lines):
        console.print(f"[{colors[i % len(colors)]}]{line}[/]")
        time.sleep(0.04)

    console.print("\n[bold white]🚀 PRO Агрегатор и чекер VLESS ключей[/]\n", justify="center")

    menu = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    menu.add_column("Key", style="bold cyan", width=8)
    menu.add_column("Action", style="white")
    menu.add_row("[ 1 ]", "Глубокая проверка всех стран")
    menu.add_row("[ 2 ]", "Проверить только одну страну")
    menu.add_row("[ 3 ]", "Быстрый режим (меньше параллельных)")
    menu.add_row("[ 4 ]", "Только очень быстрые (< 300 мс)")

    console.print(Panel(menu, title="[bold]Выберите режим[/]", border_style="blue", expand=False))

    choice = Prompt.ask("\n[bold cyan]▶ Ваш выбор[/bold cyan]", choices=["1", "2", "3", "4"], default="1")

    settings = {
        "selected_country": None,
        "concurrency": MAX_CONCURRENT_CHECKS,
        "max_latency_filter": None,
        "auto_copy": True,
    }

    if choice == "2":
        console.print("\n[bold yellow]Доступные страны:[/bold yellow]")
        country_list = list(COUNTRIES.keys())
        for i, c in enumerate(country_list, 1):
            console.print(f"  [cyan]{i}.[/cyan] {c}")
        c_choice = Prompt.ask(
            "\n[bold cyan]▶ Номер страны[/bold cyan]",
            choices=[str(i) for i in range(1, len(country_list) + 1)]
        )
        settings["selected_country"] = country_list[int(c_choice) - 1]
        console.clear()
        console.print(f"[bold green]Страна: {settings['selected_country']}. Сбор ключей...[/]")
    elif choice == "3":
        settings["concurrency"] = 25
        console.clear()
        console.print("[bold green]Быстрый режим (concurrency=25).[/]")
    elif choice == "4":
        settings["max_latency_filter"] = 300
        console.clear()
        console.print("[bold green]Режим: только ключи < 300 мс.[/]")
    else:
        console.clear()
        console.print("[bold green]Полный режим. Сбор ключей...[/]")

    settings["auto_copy"] = Confirm.ask(
        "\n[cyan]Автоматически скопировать самый быстрый ключ в буфер?[/]", default=True
    )
    return settings



def fetch_keys(url: str) -> List[str]:
    try:
        resp = _SESSION.get(url, timeout=15)
        resp.raise_for_status()
        return [line.strip() for line in resp.text.splitlines() if line.strip().startswith("vless://")]
    except Exception:
        return []


def filter_keys(keys: List[str], mode: str) -> List[str]:
    if mode in COUNTRIES:
        return [k for k in keys if any(kw in k.lower() for kw in COUNTRIES[mode])]
    if mode.lower() == "other":
        return [
            k for k in keys
            if not any(kw in k.lower() for kw in COUNTRIES_ALL_KEYWORDS)
            and "russia" not in k.lower()
        ]
    return keys


def parse_key_info(key: str) -> Tuple[Optional[str], Optional[int], Optional[str], Optional[str]]:
    try:
        parsed = urlparse(key)
        if parsed.scheme != "vless":
            return None, None, None, None
        host, port = parsed.hostname, parsed.port
        fragment = unquote(parsed.fragment)
        country, flag = None, None
        if fragment:
            match = COUNTRY_PATTERN.search(fragment)
            if match:
                country = match.group(1).strip()
                flag = fragment[:match.start()].strip()
        return host, port, country, flag
    except ValueError:
        return None, None, None, None


async def check_tcp(host: str, port: int) -> Optional[float]:
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
    except OSError:
        return None

    async def ping_ip(ip: str) -> Optional[float]:
        start = time.perf_counter()
        try:
            fut = asyncio.open_connection(ip, port)
            reader, writer = await asyncio.wait_for(fut, timeout=TEST_TIMEOUT)
            sock = writer.get_extra_info('socket')
            if sock:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            latency = (time.perf_counter() - start) * 1000
            writer.close()
            await writer.wait_closed()
            return latency
        except Exception:
            return None

    tasks = [ping_ip(info[4][0]) for info in infos]
    results = await asyncio.gather(*tasks)
    valid = [r for r in results if r is not None and r <= MAX_LATENCY_MS]
    return round(min(valid), 1) if valid else None


async def check_mode_async(
    keys: List[str],
    progress: Progress,
    task_id,
    concurrency: int = MAX_CONCURRENT_CHECKS,
    max_latency_filter: Optional[float] = None,
) -> Dict[str, Any]:
    sem = asyncio.Semaphore(concurrency)

    async def bounded_test(key: str) -> Optional[Dict[str, Any]]:
        async with sem:
            host, port, _, _ = parse_key_info(key)
            latency = None
            if host and port:
                latency = await check_tcp(host, port)

            if latency is not None:
                if max_latency_filter is not None and latency > max_latency_filter:
                    progress.update(task_id, advance=1, last_ping=f"[dim yellow]{latency} мс (фильтр)[/]")
                    return None
                progress.update(task_id, advance=1, last_ping=f"[bold green]⚡ {latency} мс[/bold green]")
                return {"key": key, "host": host, "port": port, "latency_ms": latency}
            else:
                progress.update(task_id, advance=1, last_ping="[dim red]Таймаут[/dim red]")
                return None

    tasks = [bounded_test(key) for key in keys]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    valid = [r for r in results if isinstance(r, dict)]
    working = sorted(valid, key=lambda x: x["latency_ms"])
    progress.update(task_id, last_ping="[bold cyan]Готово![/bold cyan]")
    return {
        "all_working": working,
        "total_working": len(working),
        "total": len(keys),
    }



def generate_html_report(results: dict):
    cards_html = ""
    animation_delay = 0.1

    def build_card(title, data, flag=""):
        nonlocal animation_delay
        if not data.get("all_working"):
            return ""
        rows = ""
        for item in data["all_working"]:
            key = item["key"]
            latency = item["latency_ms"]
            host = item.get("host", "Unknown")

            if latency < 300:
                speed_class, icon = "fast pulse", "🚀"
            elif latency < 800:
                speed_class, icon = "med", "⚡"
            else:
                speed_class, icon = "slow", "🐢"

            # Ключ в base64 — нельзя внедрить JS через спецсимволы в ссылке
            key_b64 = base64.b64encode(key.encode("utf-8")).decode("ascii")
            safe_host = html_module.escape(host, quote=True)

            rows += f"""
            <div class="key-row">
                <div class="key-info">
                    <span class="latency {speed_class}">{icon} {latency} ms</span>
                    <span class="host" title="{safe_host}">{safe_host}</span>
                </div>
                <button class="copy-btn" data-key="{key_b64}" onclick="copyFromBtn(this)">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                    Copy
                </button>
            </div>
            """

        card = f"""
        <div class="card" style="animation-delay: {animation_delay}s">
            <h2>
                <div class="card-title">{flag} {title}</div>
                <span class="badge">{data['total_working']} working</span>
            </h2>
            <div class="key-list">{rows}</div>
        </div>
        """
        animation_delay += 0.1
        return card

    for country in COUNTRIES:
        if country in results:
            cards_html += build_card(country, results[country])

    if "other_countries" in results:
        for c_name, c_data in results["other_countries"].items():
            cards_html += build_card(c_name, c_data, flag=c_data.get("flag", "🌍"))

    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VLESS VPN Dashboard</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-main: #050505; --text-main: #f8fafc; --text-muted: #94a3b8;
                --card-bg: rgba(20, 21, 26, 0.6); --card-border: rgba(255, 255, 255, 0.08);
                --accent: #4f46e5; --accent-glow: rgba(79, 70, 229, 0.5);
                --fast: #10b981; --med: #f59e0b; --slow: #ef4444;
            }}
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ font-family: 'Outfit', sans-serif; background-color: var(--bg-main); color: var(--text-main); min-height: 100vh; position: relative; overflow-x: hidden; }}
            body::before, body::after {{ content: ''; position: fixed; width: 600px; height: 600px; border-radius: 50%; filter: blur(150px); z-index: -1; opacity: 0.4; pointer-events: none; }}
            body::before {{ background: radial-gradient(circle, rgba(79,70,229,0.8) 0%, rgba(0,0,0,0) 70%); top: -200px; left: -100px; }}
            body::after {{ background: radial-gradient(circle, rgba(236,72,153,0.5) 0%, rgba(0,0,0,0) 70%); bottom: -200px; right: -100px; }}
            .grid-bg {{ position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-image: linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px); background-size: 40px 40px; z-index: -2; pointer-events: none; }}
            header {{ text-align: center; padding: 4rem 2rem 3rem; animation: slideDown 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; }}
            h1 {{ font-size: 3.5rem; font-weight: 800; letter-spacing: -0.05em; margin-bottom: 1rem; background: linear-gradient(135deg, #fff 0%, #a5b4fc 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; filter: drop-shadow(0 0 20px rgba(255,255,255,0.1)); }}
            .subtitle {{ color: var(--text-muted); font-size: 1.1rem; font-weight: 400; }}
            .subtitle span {{ color: #fff; background: rgba(255,255,255,0.1); padding: 4px 10px; border-radius: 8px; font-size: 0.9em; }}
            .container {{ max-width: 1400px; margin: 0 auto; padding: 0 2rem 4rem; display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 1.5rem; }}
            .card {{ background: var(--card-bg); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid var(--card-border); border-radius: 24px; padding: 1.5rem; box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1); transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); opacity: 0; transform: translateY(30px); animation: slideUpFade 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; }}
            .card:hover {{ transform: translateY(-8px); border-color: rgba(255,255,255,0.2); box-shadow: 0 20px 40px -10px rgba(0,0,0,0.4), 0 0 20px var(--accent-glow); }}
            .card h2 {{ display: flex; justify-content: space-between; align-items: center; font-size: 1.3rem; font-weight: 600; margin-bottom: 1.2rem; padding-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.05); }}
            .card-title {{ display: flex; align-items: center; gap: 8px; }}
            .badge {{ font-size: 0.85rem; font-weight: 500; color: #a5b4fc; background: rgba(79, 70, 229, 0.15); padding: 4px 12px; border-radius: 20px; border: 1px solid rgba(79, 70, 229, 0.3); }}
            .key-list {{ max-height: 400px; overflow-y: auto; padding-right: 8px; }}
            .key-list::-webkit-scrollbar {{ width: 6px; }}
            .key-list::-webkit-scrollbar-track {{ background: rgba(0,0,0,0.1); border-radius: 10px; }}
            .key-list::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.1); border-radius: 10px; }}
            .key-row {{ display: flex; justify-content: space-between; align-items: center; padding: 1rem; border-radius: 16px; margin-bottom: 8px; background: rgba(255,255,255,0.02); border: 1px solid transparent; transition: all 0.2s ease; }}
            .key-row:hover {{ background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.1); }}
            .key-info {{ display: flex; flex-direction: column; gap: 8px; overflow: hidden; }}
            .latency {{ font-weight: 700; font-size: 0.85rem; width: max-content; display: flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 8px; }}
            .latency.fast {{ color: var(--fast); background: rgba(16, 185, 129, 0.1); box-shadow: inset 0 0 0 1px rgba(16, 185, 129, 0.2); }}
            .latency.med {{ color: var(--med); background: rgba(245, 158, 11, 0.1); box-shadow: inset 0 0 0 1px rgba(245, 158, 11, 0.2); }}
            .latency.slow {{ color: var(--slow); background: rgba(239, 68, 68, 0.1); box-shadow: inset 0 0 0 1px rgba(239, 68, 68, 0.2); }}
            .pulse {{ position: relative; }}
            .pulse::after {{ content: ''; position: absolute; left: -2px; top: -2px; right: -2px; bottom: -2px; border-radius: 10px; border: 1px solid var(--fast); opacity: 0; animation: pulsing 2s infinite cubic-bezier(0.66, 0, 0, 1); }}
            .host {{ font-size: 0.95rem; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 220px; font-weight: 300; }}
            .copy-btn {{ display: flex; align-items: center; gap: 6px; background: rgba(255,255,255,0.05); color: #fff; border: 1px solid rgba(255,255,255,0.1); padding: 0.5rem 1rem; border-radius: 12px; font-family: inherit; font-size: 0.85rem; font-weight: 500; cursor: pointer; transition: all 0.2s; }}
            .copy-btn:hover {{ background: #fff; color: #000; transform: scale(1.05); }}
            .copy-btn.success {{ background: var(--fast); color: #fff; border-color: var(--fast); }}
            #toast {{ position: fixed; bottom: -100px; left: 50%; transform: translateX(-50%); background: rgba(16, 185, 129, 0.9); backdrop-filter: blur(10px); color: #fff; padding: 12px 24px; border-radius: 100px; font-weight: 500; box-shadow: 0 10px 30px rgba(16, 185, 129, 0.3); transition: bottom 0.4s cubic-bezier(0.16, 1, 0.3, 1); z-index: 1000; display: flex; align-items: center; gap: 8px; }}
            #toast.show {{ bottom: 30px; }}
            @keyframes slideUpFade {{ from {{ opacity: 0; transform: translateY(40px); }} to {{ opacity: 1; transform: translateY(0); }} }}
            @keyframes slideDown {{ from {{ opacity: 0; transform: translateY(-20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
            @keyframes pulsing {{ 0% {{ transform: scale(1); opacity: 1; }} 100% {{ transform: scale(1.15); opacity: 0; }} }}
            @media (max-width: 768px) {{ h1 {{ font-size: 2.5rem; }} .container {{ grid-template-columns: 1fr; padding: 0 1rem 4rem; }} }}
        </style>
    </head>
    <body>
        <div class="grid-bg"></div>
        <header>
            <h1>VLESS Checker PRO</h1>
            <p class="subtitle">Актуальные данные на <span>{datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")}</span></p>
        </header>
        <div class="container">{cards_html}</div>
        <div id="toast">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
            Ключ успешно скопирован!
        </div>
        <script>
            function copyFromBtn(btn) {{
                try {{
                    const text = atob(btn.getAttribute('data-key') || '');
                    navigator.clipboard.writeText(text).then(() => {{
                        const toast = document.getElementById('toast');
                        toast.classList.add('show');
                        setTimeout(() => toast.classList.remove('show'), 3000);
                        const originalHTML = btn.innerHTML;
                        btn.innerHTML = '✔ Copied';
                        btn.classList.add('success');
                        setTimeout(() => {{ btn.innerHTML = originalHTML; btn.classList.remove('success'); }}, 2000);
                    }});
                }} catch (e) {{}}
            }}
        </script>
    </body>
    </html>
    """
    HTML_OUTPUT.write_text(html, encoding="utf-8")


# === MAIN ===
async def main():
    settings = show_menu()
    selected_country = settings["selected_country"]
    concurrency = settings["concurrency"]
    max_latency_filter = settings["max_latency_filter"]

    all_keys = []
    with console.status("[bold yellow]Сбор ключей со всех источников...[/]", spinner="dots"):
        urls_to_fetch = [
            BLACK_URL,
            BLACK_MOBILE_URL,
            WHITE_URL,
            WHITE_SNI_ALL_URL,
            WHITE_CIDR_ALL_URL,
            WHITE_MOBILE_REALITY_URL,
        ] + EXTRA_URLS
        for url in urls_to_fetch:
            all_keys.extend(fetch_keys(url))

    unique_keys = list(dict.fromkeys(all_keys))
    console.print(Panel(
        f"[bold green]✅ Загружено [white]{len(unique_keys)}[/white] уникальных ключей![/]",
        style="green"
    ))
    print()

    results = {}
    quality_stats = {"fast": 0, "med": 0, "slow": 0}

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TextColumn("{task.fields[last_ping]}"),
        TimeElapsedColumn(),
        console=console,
    )

    with progress:
        for country in COUNTRIES:
            if selected_country and country != selected_country:
                continue
            filtered = filter_keys(unique_keys, country)
            if not filtered:
                continue
            task_id = progress.add_task(
                f"[cyan]Проверка {country:<12}",
                total=len(filtered),
                last_ping="[dim]ожидание...[/dim]"
            )
            results[country] = await check_mode_async(
                filtered, progress, task_id,
                concurrency=concurrency,
                max_latency_filter=max_latency_filter
            )
            for k in results[country].get("all_working", []):
                if k["latency_ms"] < 300:
                    quality_stats["fast"] += 1
                elif k["latency_ms"] < 800:
                    quality_stats["med"] += 1
                else:
                    quality_stats["slow"] += 1

        if not selected_country:
            other_keys = filter_keys(unique_keys, "other")
            country_groups = defaultdict(list)
            country_flags = {}
            for key in other_keys:
                _, _, name, flag = parse_key_info(key)
                if not name or name.lower() in SKIP_COUNTRY_NAMES:
                    name = "Other"
                    flag = "🌍"
                country_groups[name].append(key)
                if name not in country_flags:
                    country_flags[name] = flag

            other_results = {}
            for name, keys in country_groups.items():
                task_id = progress.add_task(
                    f"[magenta]Проверка {name[:12]:<12}",
                    total=len(keys),
                    last_ping="[dim]ожидание...[/dim]"
                )
                checked = await check_mode_async(
                    keys, progress, task_id,
                    concurrency=concurrency,
                    max_latency_filter=max_latency_filter
                )
                checked["flag"] = country_flags.get(name, "🌍")
                other_results[name] = checked
                for k in checked.get("all_working", []):
                    if k["latency_ms"] < 300:
                        quality_stats["fast"] += 1
                    elif k["latency_ms"] < 800:
                        quality_stats["med"] += 1
                    else:
                        quality_stats["slow"] += 1
            results["other_countries"] = other_results

    # === ТАБЛИЦА ===
    console.print("\n")
    table = Table(title="🏆 ТОП ЛУЧШИХ ЛОКАЦИЙ", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Локация", justify="left")
    table.add_column("Рабочих", justify="center", style="green")
    table.add_column("Лучший пинг", justify="center", style="bold yellow")
    table.add_column("Средний", justify="center", style="cyan")
    table.add_column("Лучший IP", justify="left", style="dim white")

    all_summaries = []
    best_key = None
    best_ping = 99999.0

    for country in COUNTRIES:
        if country in results and results[country].get("all_working"):
            working = results[country]["all_working"]
            best = working[0]["latency_ms"]
            avg = round(sum(x["latency_ms"] for x in working) / len(working), 1)
            if best < best_ping:
                best_ping = best
                best_key = working[0]["key"]
            all_summaries.append({
                "name": country,
                "count": len(working),
                "ping": best,
                "avg": avg,
                "ip": working[0]["host"],
                "keys": working[:5],
            })

    if not selected_country and "other_countries" in results:
        for name, data in results["other_countries"].items():
            if data.get("all_working"):
                working = data["all_working"]
                best = working[0]["latency_ms"]
                avg = round(sum(x["latency_ms"] for x in working) / len(working), 1)
                flag = data.get("flag", "🌍")
                if best < best_ping:
                    best_ping = best
                    best_key = working[0]["key"]
                all_summaries.append({
                    "name": f"{flag} {name}",
                    "count": len(working),
                    "ping": best,
                    "avg": avg,
                    "ip": working[0]["host"],
                    "keys": working[:5],
                })

    all_summaries.sort(key=lambda x: x["ping"])
    for s in all_summaries[:15]:
        table.add_row(s["name"], str(s["count"]), f"⚡ {s['ping']} мс", f"{s['avg']} мс", s["ip"])
    console.print(table)

    total_working = quality_stats["fast"] + quality_stats["med"] + quality_stats["slow"]
    console.print(Panel(
        f"[bold green]🟢 Идеально (< 300 мс):[/] {quality_stats['fast']}\n"
        f"[bold yellow]🟡 Нормально (300–800 мс):[/] {quality_stats['med']}\n"
        f"[bold red]🔴 Медленно (> 800 мс):[/] {quality_stats['slow']}\n"
        f"[bold white]Всего рабочих:[/] {total_working}",
        title="📊 Статистика качества",
        border_style="blue",
        expand=False
    ))

    if all_summaries:
        console.print("\n[bold magenta]🔑 ТОП РАБОЧИХ КЛЮЧЕЙ:[/bold magenta]")
        for s in all_summaries[:7]:
            console.print(f"\n🌍 [bold white]{s['name']}[/] | ⚡ [yellow]{s['ping']} мс[/] | avg {s['avg']} мс")
            for i, k in enumerate(s["keys"], 1):
                console.print(f"   [dim]{i}.[/] [green]{k['key']}[/]")
    else:
        console.print("\n[bold red]Рабочих ключей не найдено.[/]")

    # === HTML (основной вывод) ===
    console.print("\n[bold yellow]Генерация HTML-дашборда...[/]")
    generate_html_report(results)
    console.print(f"  [green]✓[/] [white]{HTML_OUTPUT.name}[/]")

    play_beep()

    auto_msg = ""
    if settings["auto_copy"] and best_key:
        if copy_to_clipboard(best_key):
            auto_msg = (
                f"[bold cyan]📋 Самый быстрый ключ ({best_ping} мс) "
                f"скопирован в буфер. Ctrl+V в VPN-клиенте.[/]"
            )
        else:
            auto_msg = "[dim]Буфер недоступен (поставьте pyperclip или xclip).[/dim]"

    console.print(Panel(
        f"[bold green]🎉 Готово![/]\n\n"
        f"{auto_msg}\n\n"
        f"HTML-дашборд: [white]{HTML_OUTPUT.name}[/white] (рабочий стол)",
        title="Результат",
        border_style="green"
    ))


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold red]Остановлено пользователем[/]")
    except Exception:
        console.print("\n[bold red]❌ ОШИБКА:[/]\n")
        # show_locals=False — не светим пути/переменные окружения
        console.print_exception(show_locals=False)
    finally:
        input("\nНажмите ENTER для выхода...")
