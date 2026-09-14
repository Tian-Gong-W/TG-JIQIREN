import os
import sys
import subprocess
import time
import threading
import socket
import webview

# ====================================================
# 工具函数：自动寻找空闲端口
# ====================================================
def find_free_port(start=18000, end=18999):
    """在指定范围内自动找一个空闲端口"""
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return 18000  # 最后兜底


# ====================================================
# 工具函数：等待端口就绪
# ====================================================
def wait_for_port(port, timeout=30):
    """等待直到指定端口开始监听"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


# ====================================================
# 获取运行基础目录（兼容 PyInstaller 打包和直接运行）
# ====================================================
def get_base_dir():
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，资源放在 _MEIPASS 临时目录（onefile模式）
        # 但我们使用 onedir 模式，所以 exe 旁边就是资源
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


# ====================================================
# 主程序
# ====================================================
class TGApp:
    def __init__(self):
        self.base_dir = get_base_dir()
        self.tg_suite_dir = os.path.join(self.base_dir, "tg_suite")
        self.python_process = None
        self.port = find_free_port()  # 自动寻找空闲端口，不与其他程序冲突

        # 找到 Python 解释器：优先使用打包进来的 venv
        self.python_exe = self._find_python()

    def _find_python(self):
        """按优先级查找可用 Python"""
        candidates = [
            # 1. 同目录下的虚拟环境
            os.path.join(self.tg_suite_dir, ".venv", "Scripts", "python.exe"),
            os.path.join(self.tg_suite_dir, "venv", "Scripts", "python.exe"),
            # 2. 系统 Python
            "python.exe",
            "python3.exe",
            "python",
        ]
        for c in candidates:
            if os.path.isabs(c):
                if os.path.exists(c):
                    return c
            else:
                try:
                    result = subprocess.run(
                        [c, "--version"],
                        capture_output=True, timeout=3
                    )
                    if result.returncode == 0:
                        return c
                except Exception:
                    continue
        return "python"  # 最后兜底

    def install_deps_if_needed(self):
        """首次运行自动安装依赖"""
        req_file = os.path.join(self.tg_suite_dir, "requirements.txt")
        marker = os.path.join(self.tg_suite_dir, ".deps_installed")

        if os.path.exists(marker):
            return  # 已安装过，跳过

        if not os.path.exists(req_file):
            return

        print("[*] 首次运行，正在安装依赖，请稍候...")
        try:
            subprocess.run(
                [self.python_exe, "-m", "pip", "install", "-r", req_file, "-q",
                 "--disable-pip-version-check"],
                cwd=self.tg_suite_dir,
                timeout=300,
                check=True
            )
            # 写标记文件，下次不再重复安装
            with open(marker, "w") as f:
                f.write("ok")
            print("[*] 依赖安装完成！")
        except subprocess.CalledProcessError as e:
            print(f"[!] 依赖安装失败: {e}")

    def start_backend(self):
        """启动 FastAPI 后端"""
        env = os.environ.copy()
        env["TG_AUTH_DISABLED"] = "true"
        env["TG_ENV"] = "development"

        # 读取 .env 文件并注入
        env_file = os.path.join(self.tg_suite_dir, ".env")
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        env[k.strip()] = v.strip()

        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

        self.python_process = subprocess.Popen(
            [self.python_exe, "-m", "uvicorn", "server:app",
             "--host", "127.0.0.1",
             "--port", str(self.port),
             "--no-access-log"],
            cwd=self.tg_suite_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags
        )
        print(f"[*] 后端服务启动中 (PID: {self.python_process.pid})")

    def stop(self):
        """关闭所有后台进程"""
        if self.python_process:
            try:
                if os.name == 'nt':
                    subprocess.call(
                        ['taskkill', '/F', '/T', '/PID', str(self.python_process.pid)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                else:
                    self.python_process.terminate()
            except Exception:
                pass
        print("[*] 程序已退出")

    def run(self):
        # 第一步：安装依赖（如需）
        self.install_deps_if_needed()

        # 第二步：启动后端
        self.start_backend()

        # 第三步：等待端口就绪
        print(f"[*] 等待后端启动 (端口 {self.port})...")
        ready = wait_for_port(self.port, timeout=30)
        if not ready:
            # 超时后仍然尝试打开（有些环境较慢）
            print("[!] 后端启动超时，仍然尝试打开界面...")

        # 第四步：打开界面 (优先使用系统原生 WebView 窗口，失败时自动打开浏览器)
        url = f"http://127.0.0.1:{self.port}"
        print(f"[*] 打开控制台: {url}")

        try:
            window = webview.create_window(
                title="雲頂天宮 · Telegram 智能矩阵与商机中枢",
                url=url,
                width=1366,
                height=850,
                min_size=(900, 600),
                resizable=True,
                text_select=True,
            )
            webview.start(debug=False, private_mode=False)
        except Exception as e:
            import webbrowser
            print(f"[*] 原生窗口引擎初始化提示: {e}，正在使用默认浏览器打开...")
            webbrowser.open(url)
            print(f"[✓] 已在浏览器中打开: {url}")
            print("[*] 请保持此黑框运行，按 Ctrl+C 或关闭黑框退出程序...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

        # 第六步：窗口关闭后清理进程
        self.stop()


if __name__ == '__main__':
    app = TGApp()
    app.run()
