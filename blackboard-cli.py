from playwright.sync_api import sync_playwright
import questionary
from questionary import Style
from getpass import getpass
from urllib.parse import urljoin
import threading
import os
import time
import requests
import mimetypes

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn
from rich.text import Text
from rich.table import Table
from rich.rule import Rule
from rich import box
from rich.prompt import Prompt
from rich.theme import Theme

BASE = "https://bb.sustech.edu.cn"

# Windows 非法字符：\ / : * ? " < > |
def sanitize_filename(name: str) -> str:
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, "_")
    return name.strip()

# ── Theme ────────────────────────────────────────────────────────────────────
custom_theme = Theme({
    "primary":   "bold cyan",
    "secondary": "dim white",
    "success":   "bold green",
    "warning":   "bold yellow",
    "error":     "bold red",
    "info":      "bold blue",
    "muted":     "dim cyan",
    "highlight": "bold white on cyan",
})

console = Console(theme=custom_theme)

qs_style = Style([
    ("qmark",        "fg:#00d7ff bold"),
    ("question",     "fg:#ffffff bold"),
    ("answer",       "fg:#00d7ff bold"),
    ("pointer",      "fg:#00d7ff bold"),
    ("highlighted",  "fg:#000000 bg:#00d7ff bold"),
    ("selected",     "fg:#00d7ff"),
    ("separator",    "fg:#444444"),
    ("instruction",  "fg:#888888 italic"),
    ("text",         "fg:#cccccc"),
    ("disabled",     "fg:#666666 italic"),
])

# ── Helpers ──────────────────────────────────────────────────────────────────
def banner():
    console.print()
    art = Text()
    art.append("  ██████╗ ██████╗      ", style="bold cyan")
    art.append("██████╗  ██████╗ ██╗    ██╗███╗   ██╗", style="bold white")
    console.print(art)
    art2 = Text()
    art2.append("  ██╔══██╗██╔══██╗    ", style="bold cyan")
    art2.append("██╔══██╗██╔═══██╗██║    ██║████╗  ██║", style="bold white")
    console.print(art2)
    art3 = Text()
    art3.append("  ██████╔╝██████╔╝    ", style="bold cyan")
    art3.append("██║  ██║██║   ██║██║ █╗ ██║██╔██╗ ██║", style="bold white")
    console.print(art3)
    art4 = Text()
    art4.append("  ██╔══██╗██╔══██╗    ", style="bold cyan")
    art4.append("██║  ██║██║   ██║██║███╗██║██║╚██╗██║", style="bold white")
    console.print(art4)
    art5 = Text()
    art5.append("  ██████╔╝██████╔╝    ", style="bold cyan")
    art5.append("██████╔╝╚██████╔╝╚███╔███╔╝██║ ╚████║", style="bold white")
    console.print(art5)
    art6 = Text()
    art6.append("  ╚═════╝ ╚═════╝     ", style="bold cyan")
    art6.append("╚═════╝  ╚═════╝  ╚══╝╚══╝ ╚═╝  ╚═══╝", style="bold white")
    console.print(art6)

    console.print(Panel(
        "[secondary]Blackboard Course File Downloader[/secondary]\n"
        "[muted]SUSTech · bb.sustech.edu.cn[/muted]",
        border_style="cyan",
        padding=(0, 4),
    ))
    console.print()


def section(title: str):
    console.print()
    console.print(Rule(f"[primary] {title} [/primary]", style="cyan"))
    console.print()


def choose_in_thread(prompt_text, choices, multiple=False):
    result = []

    def worker():
        if multiple:
            result.append(questionary.checkbox(
                prompt_text, choices=choices, style=qs_style).ask())
        else:
            result.append(questionary.select(
                prompt_text, choices=choices, style=qs_style).ask())

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    return result[0]


def download_file_with_requests(context, furl, save_dir, fname):
    cookies   = context.cookies()
    cookie_dict = {c['name']: c['value'] for c in cookies}
    full_url  = urljoin(BASE, furl)

    try:
        r = requests.get(full_url, cookies=cookie_dict, stream=True)
        if r.status_code != 200:
            console.print(f"  [error]✗[/error] 下载失败 [secondary]({r.status_code})[/secondary]: [muted]{fname}[/muted]")
            return

        filename = sanitize_filename(fname)
        if "." not in filename:
            content_type = r.headers.get("Content-Type", "")
            ext = mimetypes.guess_extension(content_type.split(";")[0])
            if ext:
                filename = filename + ext

        save_path = os.path.join(save_dir, filename)
        total     = int(r.headers.get("content-length", 0))

        with Progress(
            SpinnerColumn(style="cyan"),
            TextColumn("[cyan]{task.description}"),
            BarColumn(bar_width=28, style="cyan", complete_style="bold cyan"),
            DownloadColumn(),
            TransferSpeedColumn(),
            console=console,
            transient=True,
        ) as prog:
            task = prog.add_task(f"[white]{filename[:48]}[/white]", total=total or None)
            with open(save_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
                    prog.advance(task, len(chunk))

        console.print(f"  [success]✓[/success] [white]{filename}[/white]")

    except Exception as e:
        console.print(f"  [error]✗ 下载错误:[/error] [secondary]{e}[/secondary]")


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    banner()

    # ── Credentials ───────────────────────────────────────────────────────────
    section("登录")
    username = Prompt.ask("[primary]用户名[/primary]")
    password = getpass("  密码: ")

    # ── Download directory ─────────────────────────────────────────────────────
    section("下载路径")
    default_dir  = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser("~")), "Downloads")
    download_dir = Prompt.ask(
        f"[primary]保存路径[/primary] [secondary](回车使用默认)[/secondary]",
        default=default_dir,
    ).strip() or default_dir
    os.makedirs(download_dir, exist_ok=True)
    console.print(f"  [muted]→ 保存至:[/muted] [white]{download_dir}[/white]")

    # ── Browser ────────────────────────────────────────────────────────────────
    section("启动浏览器")
    with sync_playwright() as p:
        browser = None
        for channel, label in [("msedge", "Edge"), ("chrome", "Chrome")]:
            try:
                with console.status(f"[cyan]正在启动 {label}...[/cyan]", spinner="dots"):
                    browser = p.chromium.launch(
                        headless=True,
                        channel=channel,
                        args=["--disable-blink-features=AutomationControlled"],
                    )
                console.print(f"  [success]✓[/success] 使用 [white]{label}[/white] 浏览器")
                break
            except Exception:
                console.print(f"  [warning]![/warning] {label} 不可用，尝试下一个...")

        if browser is None:
            console.print("[error]✗ 未找到可用浏览器[/error]")
            return

        context = browser.new_context()
        page    = context.new_page()

        # ── Login ──────────────────────────────────────────────────────────────
        with console.status("[cyan]正在连接 Blackboard...[/cyan]", spinner="dots"):
            page.goto(BASE)

        if "cas.sustech.edu.cn" in page.url:
            with console.status("[cyan]正在登录 CAS...[/cyan]", spinner="dots"):
                page.fill("input#username", username)
                page.fill("input#password", password)
                page.locator("button:has-text('登录')").click()
                page.wait_for_load_state("networkidle", timeout=30000)
                page.goto(BASE)
                page.wait_for_load_state("networkidle")
            console.print("  [success]✓[/success] 登录成功")
        else:
            console.print("  [info]i[/info] 已处于登录状态")

        # ── Course selection ───────────────────────────────────────────────────
        section("选择课程")
        with console.status("[cyan]正在加载课程列表...[/cyan]", spinner="dots"):
            course_links = page.locator("a[href*='execute/launcher?type=Course']")
            courses = [
                (course_links.nth(i).inner_text().strip(),
                 course_links.nth(i).get_attribute("href"))
                for i in range(course_links.count())
            ]

        if not courses:
            console.print("[error]✗ 未找到课程，请检查登录状态[/error]")
            context.close(); browser.close(); return

        console.print(f"  [muted]找到 {len(courses)} 门课程[/muted]")
        course_names        = [n for n, _ in courses]
        selected_course_name = choose_in_thread("请选择课程:", course_names)
        selected_course_url  = dict(courses)[selected_course_name]

        # ── Module selection ───────────────────────────────────────────────────
        section("选择模块")
        with console.status("[cyan]正在加载模块列表...[/cyan]", spinner="dots"):
            page.goto(urljoin(BASE, selected_course_url))
            page.wait_for_load_state("networkidle")
            time.sleep(1)
            nav_links = page.locator("li[id^='paletteItem'] a")
            modules = [
                (nav_links.nth(j).inner_text().strip(),
                 nav_links.nth(j).get_attribute("href"))
                for j in range(nav_links.count())
                if nav_links.nth(j).get_attribute("href")
            ]

        if not modules:
            console.print("[warning]! 该课程没有模块[/warning]")
            context.close(); browser.close(); return

        console.print(f"  [muted]找到 {len(modules)} 个模块[/muted]")
        module_options       = ["ALL FILES"] + [n for n, _ in modules]
        selected_module_name = choose_in_thread(
            f"请选择模块 ({selected_course_name}):", module_options)

        # ── Download ALL ───────────────────────────────────────────────────────
        if selected_module_name == "ALL FILES":
            section("批量下载 · 所有模块")
            total_files = 0

            for module_name, module_url in modules:
                console.print(f"\n  [primary]▸[/primary] [white]{module_name}[/white]")
                with console.status("[cyan]正在加载文件列表...[/cyan]", spinner="dots"):
                    page.goto(urljoin(BASE, module_url))
                    page.wait_for_load_state("networkidle")
                    time.sleep(1)
                    file_links = page.locator("a[href*='bbcswebdav']")
                    files = [
                        (file_links.nth(k).inner_text().strip(),
                         file_links.nth(k).get_attribute("href"))
                        for k in range(file_links.count())
                    ]

                if not files:
                    console.print("    [muted]— 无文件[/muted]")
                    continue

                for fname, furl in files:
                    download_file_with_requests(context, urljoin(BASE, furl), download_dir, fname)
                    total_files += 1

            console.print()
            console.print(Panel(
                f"[success]全部完成！共下载 {total_files} 个文件[/success]\n"
                f"[muted]保存至: {download_dir}[/muted]",
                border_style="green", padding=(0, 4),
            ))

        # ── Download single module ─────────────────────────────────────────────
        else:
            selected_module_url = dict(modules)[selected_module_name]

            section("选择文件")
            with console.status("[cyan]正在加载文件列表...[/cyan]", spinner="dots"):
                page.goto(urljoin(BASE, selected_module_url))
                page.wait_for_load_state("networkidle")
                time.sleep(1)
                file_links = page.locator("a[href*='bbcswebdav']")
                files = [
                    (file_links.nth(k).inner_text().strip(),
                     file_links.nth(k).get_attribute("href"))
                    for k in range(file_links.count())
                ]

            if not files:
                console.print(f"  [warning]![/warning] 模块 [{selected_module_name}] 没有文件")
            else:
                console.print(f"  [muted]找到 {len(files)} 个文件[/muted]")

                # Pretty file table preview
                tbl = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan",
                            border_style="dim", padding=(0, 1))
                tbl.add_column("#",    style="dim",   width=4)
                tbl.add_column("文件名", style="white")
                for idx, (fname, _) in enumerate(files, 1):
                    tbl.add_row(str(idx), fname)
                console.print(tbl)

                file_names     = [n for n, _ in files]
                selected_files = choose_in_thread(
                    "请选择要下载的文件（空格多选，↑↓导航）:", file_names, multiple=True)

                if not selected_files:
                    console.print("  [warning]! 未选择任何文件[/warning]")
                else:
                    section(f"下载 · {selected_module_name}")
                    count = 0
                    for fname, furl in files:
                        if fname in selected_files:
                            download_file_with_requests(
                                context, urljoin(BASE, furl), download_dir, fname)
                            count += 1

                    console.print()
                    console.print(Panel(
                        f"[success]下载完成！共 {count} 个文件[/success]\n"
                        f"[muted]保存至: {download_dir}[/muted]",
                        border_style="green", padding=(0, 4),
                    ))

        context.close()
        browser.close()
    console.print()


if __name__ == "__main__":
    main()