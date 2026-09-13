from __future__ import annotations

import os
import subprocess
import threading
import time
import tkinter as tk
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .job_queue import FileJobQueue
from .llm import OpenAICompatibleClient
from .models import ApiSettings
from .paths import default_output_dir, queue_dir
from .plugin_installer import install_plugin
from .svg_guard import validate_svg


class PromptCanvasApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Krita 提示词画布")
        self.root.geometry("900x700")
        self.root.minsize(760, 620)
        self.queue = FileJobQueue(queue_dir())
        self.current_job_id: str | None = None
        self.poll_started = 0.0

        self.base_url = tk.StringVar(value=os.environ.get("KPC_API_BASE_URL", ""))
        self.api_key = tk.StringVar(value=os.environ.get("KPC_API_KEY", ""))
        self.model = tk.StringVar(value=os.environ.get("KPC_MODEL", ""))
        self.width = tk.IntVar(value=1200)
        self.height = tk.IntVar(value=800)
        self.output_dir = tk.StringVar(value=str(default_output_dir()))
        self.krita_path = tk.StringVar(value=os.environ.get("KPC_KRITA_PATH", ""))
        self.status = tk.StringVar(value="就绪")

        self._build_ui()

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(7, weight=1)

        ttk.Label(outer, text="Krita 提示词画布", font=("Microsoft YaHei UI", 20, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 16)
        )
        self._entry_row(outer, 1, "API 基础地址", self.base_url)
        self._entry_row(outer, 2, "模型名称", self.model)
        self._entry_row(outer, 3, "API 密钥", self.api_key, show="•")

        dimensions = ttk.Frame(outer)
        dimensions.grid(row=4, column=1, columnspan=2, sticky="w", pady=5)
        ttk.Label(outer, text="画布尺寸").grid(row=4, column=0, sticky="w", pady=5)
        ttk.Spinbox(dimensions, from_=256, to=4096, textvariable=self.width, width=8).pack(
            side="left"
        )
        ttk.Label(dimensions, text=" × ").pack(side="left")
        ttk.Spinbox(dimensions, from_=256, to=4096, textvariable=self.height, width=8).pack(
            side="left"
        )

        self._path_row(outer, 5, "输出文件夹", self.output_dir, directory=True)
        self._path_row(outer, 6, "Krita 程序", self.krita_path, directory=False)

        prompt_frame = ttk.LabelFrame(outer, text="绘画需求", padding=10)
        prompt_frame.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=(12, 8))
        prompt_frame.rowconfigure(0, weight=1)
        prompt_frame.columnconfigure(0, weight=1)
        self.prompt = tk.Text(
            prompt_frame, wrap="word", height=12, font=("Microsoft YaHei UI", 11)
        )
        self.prompt.grid(row=0, column=0, sticky="nsew")
        self.prompt.insert("1.0", "二次元风格画风，粉色短发少女在湖边运动前热身")

        actions = ttk.Frame(outer)
        actions.grid(row=8, column=0, columnspan=3, sticky="ew", pady=8)
        ttk.Button(actions, text="安装 / 更新 Krita 插件", command=self.install).pack(
            side="left"
        )
        ttk.Button(actions, text="启动 Krita", command=self.launch_krita).pack(
            side="left", padx=8
        )
        self.generate_button = ttk.Button(actions, text="开始创作", command=self.generate)
        self.generate_button.pack(side="right")

        ttk.Label(outer, textvariable=self.status).grid(
            row=9, column=0, columnspan=3, sticky="w", pady=(6, 2)
        )
        self.log = tk.Text(outer, height=8, wrap="word", state="disabled")
        self.log.grid(row=10, column=0, columnspan=3, sticky="ew")

    @staticmethod
    def _entry_row(parent, row: int, label: str, variable: tk.Variable, show: str = "") -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(parent, textvariable=variable, show=show).grid(
            row=row, column=1, columnspan=2, sticky="ew", pady=5
        )

    def _path_row(
        self, parent, row: int, label: str, variable: tk.StringVar, directory: bool
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=5)

        def browse() -> None:
            selected = (
                filedialog.askdirectory()
                if directory
                else filedialog.askopenfilename(
                    filetypes=[("Krita 程序", "krita.exe"), ("所有文件", "*")]
                )
            )
            if selected:
                variable.set(selected)

        ttk.Button(parent, text="浏览", command=browse).grid(row=row, column=2, padx=(8, 0))

    def _append_log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def install(self) -> None:
        try:
            package, desktop = install_plugin()
        except Exception as exc:
            messagebox.showerror("插件安装失败", str(exc))
            return
        self._append_log(f"插件程序已复制到：{package}")
        self._append_log(f"插件描述文件已复制到：{desktop}")
        messagebox.showinfo(
            "插件安装完成",
            "请在 Krita 中打开“设置 → 配置 Krita → Python 插件管理器”，"
            "启用“Krita 提示词画布桥接器”，然后重启一次 Krita。",
        )

    def launch_krita(self) -> None:
        executable = Path(self.krita_path.get().strip())
        if not executable.is_file():
            messagebox.showerror("未找到 Krita", "请先选择 Krita 可执行程序。")
            return
        try:
            subprocess.Popen([str(executable), "--nosplash"], close_fds=True)
        except OSError as exc:
            messagebox.showerror("无法启动 Krita", str(exc))
            return
        self._append_log(f"已启动 Krita：{executable}")

    def generate(self) -> None:
        request = self.prompt.get("1.0", "end").strip()
        try:
            settings = ApiSettings(
                base_url=self.base_url.get(), api_key=self.api_key.get(), model=self.model.get()
            )
            settings.validate()
            width, height = int(self.width.get()), int(self.height.get())
            if not 256 <= width <= 4096 or not 256 <= height <= 4096:
                raise ValueError("画布宽高必须在 256 至 4096 像素之间")
            if not request:
                raise ValueError("绘画需求不能为空")
            output = Path(self.output_dir.get()).expanduser()
        except Exception as exc:
            messagebox.showerror("设置无效", str(exc))
            return

        self.generate_button.configure(state="disabled")
        self.status.set("正在请求 AI 美术指导……")
        self._append_log("正在请求结构化 SVG 方案；API 密钥不会写入磁盘。")
        threading.Thread(
            target=self._prepare_job,
            args=(settings, request, width, height, output),
            daemon=True,
        ).start()

    def _prepare_job(
        self,
        settings: ApiSettings,
        request: str,
        width: int,
        height: int,
        output: Path,
    ) -> None:
        try:
            plan = OpenAICompatibleClient(settings).create_plan(request, width, height)
            safe_svg = validate_svg(plan.svg, plan.width, plan.height)
            plan = replace(plan, svg=safe_svg)
            job = self.queue.enqueue(plan, output)
        except Exception as exc:
            self.root.after(0, self._generation_failed, str(exc))
            return
        self.root.after(0, self._job_queued, job.job_id)

    def _generation_failed(self, detail: str) -> None:
        self.current_job_id = None
        self.generate_button.configure(state="normal")
        self.status.set("创作失败")
        self._append_log(detail)
        messagebox.showerror("创作失败", detail)

    def _job_queued(self, job_id: str) -> None:
        self.current_job_id = job_id
        self.poll_started = time.monotonic()
        self.status.set("方案验证通过，正在等待 Krita 桥接器……")
        self._append_log(f"任务 {job_id} 已加入队列。请保持 Krita 运行并启用桥接器。")
        self.root.after(500, self._poll_result)

    def _poll_result(self) -> None:
        if not self.current_job_id:
            return
        try:
            result = self.queue.read_result(self.current_job_id)
        except Exception as exc:
            self._generation_failed(f"无法读取 Krita 处理结果：{exc}")
            return
        if result is None:
            if time.monotonic() - self.poll_started > 180:
                self._generation_failed(
                    "Krita 在 180 秒内未完成任务，请检查桥接器是否已启用。"
                )
                return
            self.root.after(750, self._poll_result)
            return

        self.generate_button.configure(state="normal")
        self.current_job_id = None
        if result.get("status") != "success":
            self._generation_failed(str(result.get("error", "未知的 Krita 桥接器错误")))
            return
        png_path = str(result.get("png_path", ""))
        kra_path = str(result.get("kra_path", ""))
        self.status.set("作品渲染成功")
        self._append_log(f"PNG: {png_path}")
        self._append_log(f"KRA: {kra_path}")
        messagebox.showinfo("作品已完成", f"PNG：\n{png_path}\n\nKRA：\n{kra_path}")


def main() -> None:
    root = tk.Tk()
    PromptCanvasApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
