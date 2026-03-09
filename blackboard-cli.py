import os
import time
import requests
import mimetypes
import threading
import platform
from pathlib import Path
from urllib.parse import urljoin
from getpass import getpass
from playwright.sync_api import sync_playwright
from datetime import datetime
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn
from rich.rule import Rule
from rich.text import Text
from rich.table import Table
from rich import box
from rich.prompt import Confirm, Prompt
from rich.theme import Theme

# ── 配置与常量 ──────────────────────────────────────────────────────────────
BASE = "https://bb.sustech.edu.cn"

custom_theme = Theme({
    "primary":   "bold cyan",
    "secondary": "dim white",
    "success":   "bold green",
    "warning":   "bold yellow",
    "error":     "bold red",
    "info":      "bold blue",
    "muted":     "dim cyan",
})
console = Console(theme=custom_theme)

# ── 工具函数 ──────────────────────────────────────────────────────────────────
def sanitize_filename(name: str) -> str:
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, "_")
    return name.strip()

def download_file(context, furl, save_dir, fname):
    """带进度条的下载函数"""
    cookies = {c['name']: c['value'] for c in context.cookies()}
    full_url = urljoin(BASE, furl)

    try:
        with requests.get(full_url, cookies=cookies, stream=True, timeout=30) as r:
            r.raise_for_status()
            
            # 后缀处理
            filename = sanitize_filename(fname)
            if "." not in filename:
                content_type = r.headers.get("Content-Type", "")
                ext = mimetypes.guess_extension(content_type.split(";")[0])
                if ext: filename += ext

            # 重名处理
            base, ext = os.path.splitext(filename)
            counter = 1
            save_path = os.path.join(save_dir, filename)
            while os.path.exists(save_path):
                filename = f"{base}_({counter}){ext}"
                save_path = os.path.join(save_dir, filename)
                counter += 1

            total = int(r.headers.get("content-length", 0))
            with Progress(
                SpinnerColumn(),
                TextColumn("[cyan]{task.description}"),
                BarColumn(bar_width=30),
                DownloadColumn(),
                TransferSpeedColumn(),
                console=console,
                transient=True,
            ) as prog:
                task = prog.add_task(f"[white]{filename[:30]}[/white]", total=total or None)
                with open(save_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=16384):
                        f.write(chunk)
                        prog.advance(task, len(chunk))
            
            console.print(f"  [success]✓[/success] [white]{filename}[/white]")
    except Exception as e:
        console.print(f"  [error]✗ 下载失败:[/error] {fname} ({e})")

# ── Shell 主类 ──────────────────────────────────────────────────────────────
class BlackboardShell:
    def __init__(self):
        
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        self.location = "ROOT"  # ROOT, COURSE, MODULE
        self.courses = []       # [(name, url), ...]
        self.modules = []       # [(name, url), ...]
        self.files = []         # [(name, url), ...]
        
        self.curr_course_name = ""
        self.curr_module_name = ""
        self.download_dir = ""


    def banner(self):
        from datetime import datetime
        console.clear()

        # ── Logo ──────────────────────────────────────────────────────────────────
        big = (
            "  ██████╗ ██████╗      ██████╗██╗     ██╗\n"
            "  ██╔══██╗██╔══██╗    ██╔════╝██║     ██║\n"
            "  ██████╔╝██████╔╝    ██║     ██║     ██║\n"
            "  ██╔══██╗██╔══██╗    ██║     ██║     ██║\n"
            "  ██████╔╝██████╔╝    ╚██████╗███████╗██║\n"
            "  ╚═════╝ ╚═════╝      ╚═════╝╚══════╝╚═╝\n"
        )
        console.print(Align.center(Text(big, style="bold cyan")))

        # ── 副标题 ────────────────────────────────────────────────────────────────
        subtitle = Text()
        subtitle.append("Blackboard CLI", style="bold white")
        subtitle.append("  ·  ", style="dim cyan")
        subtitle.append("v1.1.0", style="cyan")
        subtitle.append("  ·  ", style="dim cyan")
        subtitle.append("SUSTech", style="bold white")
        console.print(Align.center(subtitle))
        console.print()

        # ── 分隔线 + 元信息行 ─────────────────────────────────────────────────────
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        console.print(Rule(style="dim cyan"))

        meta = Text()
        meta.append("  🕐 ", style="dim")
        meta.append(now, style="dim white")
        meta.append("        ", style="")
        meta.append("💡 ", style="dim")
        meta.append("help", style="cyan")
        meta.append(" 查看命令", style="dim white")
        meta.append("        ", style="")
        meta.append("✦ ", style="dim cyan")
        meta.append("https://bb.sustech.edu.cn", style="dim white")

        console.print(Align.center(meta))
        console.print(Rule(style="dim cyan"))
        console.print()

    
    def login(self):
        self.banner()
        
        username = Prompt.ask("[primary]用户名[/primary]")
        password = getpass("  密码: ")
        # default_dir = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser("~")), "Downloads")
        default_dir = str(Path.home() / "Downloads")
        self.download_dir = Prompt.ask("[primary]保存路径[/primary]", default=default_dir).strip()
        
        os.makedirs(self.download_dir, exist_ok=True)
        self.playwright = sync_playwright().start()
        
        # 浏览器自动适配
        # channels = ["msedge", "chrome", None]
        system = platform.system()
        if system == "Windows":
            channels = ["msedge", "chrome", None]
        elif system == "Darwin":  # macOS
            # Mac 上 Chrome 和 Edge 的路径通常是标准的
            channels = ["chrome", "msedge", None]
        else:  # Linux
            # Linux 下 Chrome 通常叫 google-chrome，而 Edge 叫 microsoft-edge
            channels = ["google-chrome", "microsoft-edge", None]
        
        for channel in channels:
            try:
                with console.status(f"[cyan]尝试启动 {channel or '内置Chromium'}..."):
                    self.browser = self.playwright.chromium.launch(headless=True, channel=channel)
                break
            except: continue

        if not self.browser:
            console.print("[error]无法启动浏览器[/error]")
            console.print("\n[white]这通常是因为没有找到 Chrome/Edge，或者 Playwright 未初始化。[/white]")
            
            # 根据系统给出具体的修复命令
            console.print("\n[info]💡 修复建议：[/info]")
            py_cmd = "python3" if system != "Windows" else "python"
            if system == "Linux":
                console.print(f"  [primary]1.[/primary] 运行以下命令安装内置浏览器：")
                console.print(f"     [bold white]{py_cmd} -m playwright install chromium[/bold white]")
                console.print(f"  [primary]2.[/primary] 如果运行报错提示缺少库，请联系管理员执行：")
                console.print(f"     [bold white]sudo {py_cmd} -m playwright install-deps chromium[/bold white]")
            else:
                console.print(f"  [primary]1.[/primary] 确保已安装 [bold]Chrome[/bold] 或 [bold]Edge[/bold]")
                console.print(f"  [primary]2.[/primary] 或者运行以下命令安装 Playwright 内置浏览器：")
                console.print(f"     [bold white]{py_cmd} -m playwright install chromium[/bold white]")
            return False

        self.context = self.browser.new_context()
        self.page = self.context.new_page()

        with console.status("[cyan]正在登录..."):
            self.page.goto(BASE)
            if "cas.sustech.edu.cn" in self.page.url:
                self.page.fill("input#username", username)
                self.page.fill("input#password", password)
                self.page.locator("button:has-text('登录')").click()
                self.page.wait_for_load_state("networkidle")

                if "cas.sustech.edu.cn" in self.page.url:
                    console.print("\n[error]× 登录未成功，请检查账号密码。[/error]")
                    self.browser.close()
                    self.playwright.stop()
                    return False
                self.page.goto(BASE)
                self.page.wait_for_load_state("networkidle")
        
        console.print("  [success]✓ 登录成功[/success]")
        self.fetch_courses()
        return True

    # ── 数据同步 ──────────────────────────────────────────────────────────────
    def fetch_courses(self):
        with console.status("[muted]抓取课程..."):
            course_links = self.page.locator("a[href*='execute/launcher?type=Course']")
            self.courses = [(course_links.nth(i).inner_text().strip(), course_links.nth(i).get_attribute("href"))
                            for i in range(course_links.count())]

    def fetch_modules(self, url):
        with console.status("[muted]进入课程..."):
            self.page.goto(urljoin(BASE, url))
            nav_links = self.page.locator("li[id^='paletteItem'] a")
            self.modules = [(nav_links.nth(j).inner_text().strip(), nav_links.nth(j).get_attribute("href"))
                            for j in range(nav_links.count()) if nav_links.nth(j).get_attribute("href")]

    def fetch_files(self, url):
        with console.status("[muted]扫描文件..."):
            self.page.goto(urljoin(BASE, url))
            file_links = self.page.locator("a[href*='bbcswebdav']")
            self.files = [(file_links.nth(k).inner_text().strip(), file_links.nth(k).get_attribute("href"))
                          for k in range(file_links.count())]

    # ── 命令处理 ──────────────────────────────────────────────────────────────
    def do_ls(self):
        table = Table(box=box.SIMPLE, header_style="bold cyan")
        table.add_column("ID", justify="right", style="dim", width=4)
        
        if self.location == "ROOT":
            table.title = "[bold]课程列表[/bold]"
            table.add_column("名称")
            for i, (n, _) in enumerate(self.courses, 1): table.add_row(str(i), n)
        elif self.location == "COURSE":
            table.title = f"[bold]课程: {self.curr_course_name}[/bold]"
            table.add_column("模块")
            for i, (n, _) in enumerate(self.modules, 1): table.add_row(str(i), n)
        elif self.location == "MODULE":
            table.title = f"[bold]模块: {self.curr_module_name}[/bold]"
            table.add_column("文件名")
            for i, (n, _) in enumerate(self.files, 1): table.add_row(str(i), n)
        console.print(table)

    def do_cd(self, arg):
        if arg == "..":
            if self.location == "MODULE":
                self.location = "COURSE"
                self.curr_module_name = ""
            elif self.location == "COURSE":
                self.location = "ROOT"
                self.curr_course_name = ""
            self.do_ls()
            return

        try:
            idx = int(arg) - 1
            if self.location == "ROOT":
                self.curr_course_name, url = self.courses[idx]
                self.fetch_modules(url)
                self.location = "COURSE"
            elif self.location == "COURSE":
                self.curr_module_name, url = self.modules[idx]
                self.fetch_files(url)
                self.location = "MODULE"
            self.do_ls()
        except:
            console.print("[error]无效的 ID[/error]")

    def fetch_all_files_in_course(self):
        """在 Course 层级递归获取所有模块的文件"""
        all_task_files = [] # 格式: [(filename, url, folder_name), ...]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[cyan]正在遍历模块... {task.fields[module]}"),
            console=console,
            transient=True
        ) as prog:
            task = prog.add_task("Scanning", total=len(self.modules), module="")
            
            for m_name, m_url in self.modules:
                prog.update(task, module=m_name)
                # 跳转到模块页面
                self.page.goto(urljoin(BASE, m_url))
                file_links = self.page.locator("a[href*='bbcswebdav']")
                
                # 收集该模块下的所有文件
                for k in range(file_links.count()):
                    f_name = file_links.nth(k).inner_text().strip()
                    f_url = file_links.nth(k).get_attribute("href")
                    # 记录文件名、URL 以及它所属的模块名（用于创建子文件夹）
                    all_task_files.append((f_name, f_url, m_name))
                
                prog.advance(task)
        return all_task_files

    def fetch_selected_modules_files(self, selected_modules):
        """通用递归抓取：进入指定的模块列表并收集所有文件信息"""
        all_task_files = [] 
        with Progress(
            SpinnerColumn(),
            TextColumn("[cyan]正在扫描模块... {task.fields[module]}"),
            console=console,
            transient=True
        ) as prog:
            task = prog.add_task("Scanning", total=len(selected_modules), module="")
            
            for m_name, m_url in selected_modules:
                prog.update(task, module=m_name)
                try:
                    self.page.goto(urljoin(BASE, m_url))
                    # 确保页面加载
                    self.page.wait_for_load_state("networkidle")
                    file_links = self.page.locator("a[href*='bbcswebdav']")
                    
                    count = file_links.count()
                    for k in range(count):
                        f_name = file_links.nth(k).inner_text().strip()
                        f_url = file_links.nth(k).get_attribute("href")
                        # 记录文件名、URL 和它所属的模块名（用于建文件夹）
                        all_task_files.append((f_name, f_url, m_name))
                except Exception as e:
                    console.print(f"[warning]扫描模块 {m_name} 失败: {e}[/warning]")
                
                prog.advance(task)
        return all_task_files

    def do_get(self, args):
        if self.location != "MODULE" and self.location != "COURSE":
            console.print("[error]请先进入课程或模块再执行 get 命令[/error]")
            return
        
        if not args:
            console.print("[warning]用法: get [ID1] [ID2] ... 或 get all[/warning]")
            return
        
        if self.location == "MODULE":
            indices = []
            if args and args[0] == "all":
                indices = list(range(len(self.files)))
            else:
                indices = [int(i)-1 for i in args if i.isdigit()]
            
            for i in indices:
                if 0 <= i < len(self.files):
                    download_file(self.context, self.files[i][1], self.download_dir, self.files[i][0])
        
        elif self.location == "COURSE":
            target_modules = []
            
            if args[0].lower() == "all":
                target_modules = self.modules
                msg = "全部模块"
            else:
                try:
                    # 将输入的数字 ID 转换为对应的模块对象
                    indices = [int(i)-1 for i in args if i.isdigit()]
                    target_modules = [self.modules[i] for i in indices if 0 <= i < len(self.modules)]
                    msg = f"选定的 {len(target_modules)} 个模块"
                except:
                    console.print("[error]无效的模块 ID，请输入数字或 'all'[/error]")
                    return

            if not target_modules:
                console.print("[error]未选中任何有效模块[/error]")
                return

            confirm = Prompt.ask(f"[primary]确定下载课程 [white]{self.curr_course_name}[/white] 的{msg}吗？[/primary] (y/n)", default="y")
            if confirm.lower() != 'y': return

            # 1. 递归扫描选中的模块
            all_files_to_download = self.fetch_selected_modules_files(target_modules)
            console.print(f"[info]扫描完成：共发现 {len(all_files_to_download)} 个文件。[/info]")

            # 2. 依次执行下载
            for fname, furl, mname in all_files_to_download:
                # 自动构建路径：下载目录/课程名/模块名
                module_dir = os.path.join(
                    self.download_dir, 
                    sanitize_filename(self.curr_course_name), 
                    sanitize_filename(mname)
                )
                os.makedirs(module_dir, exist_ok=True)
                download_file(self.context, furl, module_dir, fname)
            
            console.print(f"[success]✨ {msg} 下载任务已结束！[/success]")

    def run(self):
        if not self.login(): return
        while True:
            # 动态路径提示符
            path = f"/{self.curr_course_name}/{self.curr_module_name}".replace("//", "/")
            cmd_line = Prompt.ask(f"\n[bold cyan]BB[/bold cyan] [dim]{path}[/dim] >").strip().split()
            if not cmd_line: continue
            
            cmd, args = cmd_line[0].lower(), cmd_line[1:]
            
            if cmd in ["q", "exit"]: break
            elif cmd == "ls": self.do_ls()
            elif cmd == "cd": self.do_cd(args[0] if args else "")
            elif cmd == "get": self.do_get(args)
            elif cmd == "clear": self.banner()
            elif cmd == "help":
                console.print("[info]可用命令: ls, cd [ID], cd .., get [ID], get all, clear, exit[/info]")

        self.browser.close()
        self.playwright.stop()

if __name__ == "__main__":
    BlackboardShell().run()