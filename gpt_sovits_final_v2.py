# gpt_sovits_final.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import threading
import os
import glob
import time
import re
import subprocess
from pathlib import Path


class TTSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GPT-SoVITS 语音合成工具")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)

        # 设置样式
        self.setup_styles()

        self.api_base = "http://127.0.0.1:9880"
        self.current_audio = None
        self.backend_available = False

        # 模型列表
        self.gpt_models = []
        self.sovits_models = []
        self.current_gpt = tk.StringVar()
        self.current_sovits = tk.StringVar()

        # 单次合成：参考音频列表（路径 + 参考文本）
        self.single_ref_list = []  # 每个元素: {"path": str, "text": str}

        # 批量合成：参考音频列表
        self.batch_ref_list = []  # 每个元素: {"path": str, "text": str}

        # 批量处理控制
        self.batch_running = False
        self.batch_paused = False
        self.batch_stop = False
        self.batch_file_list = []
        self.batch_current_index = 0

        # 命名规则
        self.naming_prefix = tk.StringVar(value="")
        self.naming_suffix = tk.StringVar(value="")
        self.naming_separator = tk.StringVar(value="_")

        # 配置参数
        self.init_config_vars()

        # 先创建UI
        self.setup_ui()

        # 后扫描模型和检测后端
        self.scan_local_models()
        self.check_backend()

    def setup_styles(self):
        """设置现代化样式"""
        style = ttk.Style()
        style.theme_use('clam')

        # 配色方案
        self.colors = {
            'primary': '#2196F3',  # 蓝色
            'success': '#4CAF50',  # 绿色
            'warning': '#FF9800',  # 橙色
            'danger': '#f44336',  # 红色
            'dark': '#333333',  # 深灰
            'light': '#f5f5f5',  # 浅灰
            'white': '#ffffff',  # 白色
            'border': '#e0e0e0',  # 边框色
            'text': '#424242',  # 文字色
            'text_light': '#757575'  # 浅文字色
        }

        # 配置ttk样式
        style.configure('TNotebook', background=self.colors['white'])
        style.configure('TNotebook.Tab', padding=[15, 8], font=('微软雅黑', 10))
        style.map('TNotebook.Tab',
                  background=[('selected', self.colors['primary']), ('active', '#E3F2FD')],
                  foreground=[('selected', self.colors['white'])])

        style.configure('TFrame', background=self.colors['white'])
        style.configure('TLabel', background=self.colors['white'], font=('微软雅黑', 9))
        style.configure('TLabelframe', background=self.colors['white'], relief='solid', borderwidth=1)
        style.configure('TLabelframe.Label', background=self.colors['white'], font=('微软雅黑', 10, 'bold'),
                        foreground=self.colors['primary'])

        style.configure('TButton', font=('微软雅黑', 9), padding=[10, 5])
        style.map('TButton', background=[('active', '#E3F2FD')])

        style.configure('TEntry', fieldbackground=self.colors['white'], borderwidth=1, relief='solid')
        style.configure('TCombobox', fieldbackground=self.colors['white'], borderwidth=1)

        style.configure('TProgressbar', thickness=8, background=self.colors['success'])

    def init_config_vars(self):
        """初始化配置参数"""
        self.top_k = tk.IntVar(value=10)
        self.top_p = tk.DoubleVar(value=0.8)
        self.temperature = tk.DoubleVar(value=0.8)
        self.repetition_penalty = tk.DoubleVar(value=1.2)
        self.speed_factor = tk.DoubleVar(value=1.0)
        self.sample_steps = tk.IntVar(value=4)
        self.text_split_method = tk.StringVar(value="cut5")

        # 文本分割参数
        self.max_chunk_size = tk.IntVar(value=500)
        self.enable_split = tk.BooleanVar(value=True)

        # 批量参数
        self.batch_source_dir = tk.StringVar()
        self.batch_target_dir = tk.StringVar()
        self.batch_file_pattern = tk.StringVar(value="*.txt")
        self.batch_delay = tk.DoubleVar(value=0.1)

    def setup_ui(self):
        # 顶部状态栏
        self.setup_status_bar()

        # 主框架 - 使用Notebook分页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        # 页面1：单次合成
        self.single_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.single_frame, text="🎙️ 单次合成")
        self.setup_single_tab()

        # 页面2：批量合成
        self.batch_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.batch_frame, text="📚 批量合成")
        self.setup_batch_tab()

        # 页面3：参数设置
        self.params_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.params_frame, text="⚙️ 参数设置")
        self.setup_params_tab()

        # 页面4：模型管理
        self.model_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.model_frame, text="🤖 模型管理")
        self.setup_model_tab()

    def setup_status_bar(self):
        """顶部状态栏"""
        status_frame = tk.Frame(self.root, bg=self.colors['light'], height=40)
        status_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
        status_frame.pack_propagate(False)

        # 后端状态
        self.status_label = tk.Label(status_frame, text="🔍 检测后端中...",
                                     bg=self.colors['light'], fg=self.colors['text'],
                                     font=('微软雅黑', 10))
        self.status_label.pack(side=tk.LEFT, padx=15, pady=8)

        # 当前模型信息
        model_info_frame = tk.Frame(status_frame, bg=self.colors['light'])
        model_info_frame.pack(side=tk.RIGHT, padx=15, pady=5)

        self.current_gpt_label = tk.Label(model_info_frame, text="GPT: 未加载",
                                          bg=self.colors['light'], fg=self.colors['text_light'],
                                          font=('微软雅黑', 9))
        self.current_gpt_label.pack(side=tk.LEFT, padx=(0, 10))

        self.current_sovits_label = tk.Label(model_info_frame, text="SoVITS: 未加载",
                                             bg=self.colors['light'], fg=self.colors['text_light'],
                                             font=('微软雅黑', 9))
        self.current_sovits_label.pack(side=tk.LEFT)

    def create_section_frame(self, parent, title, **kwargs):
        """创建统一风格的区块"""
        frame = ttk.LabelFrame(parent, text=title, padding="15")
        return frame

    def create_action_button(self, parent, text, command, color=None, **kwargs):
        """创建统一样式的按钮"""
        btn = tk.Button(parent, text=text, command=command,
                        bg=color or self.colors['primary'], fg=self.colors['white'],
                        font=('微软雅黑', 10), borderwidth=0, padx=15, pady=5,
                        cursor='hand2', activebackground='#1976D2', activeforeground='white')
        return btn

    def setup_single_tab(self):
        """单次合成页面 - 已移除模型选择"""
        # 主容器 - 左右分栏
        main_container = ttk.Frame(self.single_frame)
        main_container.pack(fill=tk.BOTH, expand=True)

        # 左侧面板 - 输入区域
        left_panel = ttk.Frame(main_container)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # 参考音频区域
        ref_frame = self.create_section_frame(left_panel, "🎵 参考音频设置")
        ref_frame.pack(fill=tk.X, pady=(0, 10))

        # 表头
        header_frame = tk.Frame(ref_frame, bg=self.colors['white'])
        header_frame.pack(fill=tk.X, pady=(0, 5))

        tk.Label(header_frame, text="序号", bg=self.colors['white'],
                 font=('微软雅黑', 9, 'bold'), width=5, anchor='w').pack(side=tk.LEFT)
        tk.Label(header_frame, text="参考音频路径", bg=self.colors['white'],
                 font=('微软雅黑', 9, 'bold'), width=35, anchor='w').pack(side=tk.LEFT, padx=(5, 0))
        tk.Label(header_frame, text="参考文本（必填）", bg=self.colors['white'],
                 font=('微软雅黑', 9, 'bold'), width=30, anchor='w').pack(side=tk.LEFT, padx=(5, 0))
        tk.Label(header_frame, text="操作", bg=self.colors['white'],
                 font=('微软雅黑', 9, 'bold'), width=8, anchor='w').pack(side=tk.LEFT, padx=(5, 0))

        # 分隔线
        separator = tk.Frame(ref_frame, height=1, bg=self.colors['border'])
        separator.pack(fill=tk.X, pady=(0, 5))

        # 说明文字
        tip_frame = tk.Frame(ref_frame, bg=self.colors['white'])
        tip_frame.pack(fill=tk.X, pady=(0, 5))
        tk.Label(tip_frame, text="💡 提示：第一个音频为主参考，参考文本建议填写音频对应的文字内容",
                 bg=self.colors['white'], fg=self.colors['text_light'],
                 font=('微软雅黑', 9)).pack(anchor='w')

        # 参考音频列表容器
        self.single_ref_container = ttk.Frame(ref_frame)
        self.single_ref_container.pack(fill=tk.X)

        # 添加按钮
        add_btn = self.create_action_button(ref_frame, "+ 添加参考音频",
                                            self.add_single_ref_audio, self.colors['success'])
        add_btn.pack(pady=(10, 0))

        # 默认添加一个空行
        self.single_ref_list = []
        self.add_single_ref_audio()

        # 合成文本区域
        text_frame = self.create_section_frame(left_panel, "📝 合成文本")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 语言选择行
        lang_frame = ttk.Frame(text_frame)
        lang_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(lang_frame, text="文本语言:").pack(side=tk.LEFT)
        self.text_lang = ttk.Combobox(lang_frame, values=["zh (中文)", "en (英文)", "ja (日文)"],
                                      width=15, state='readonly')
        self.text_lang.set("zh (中文)")
        self.text_lang.pack(side=tk.LEFT, padx=10)

        # 文本输入框
        text_container = tk.Frame(text_frame, bg=self.colors['white'])
        text_container.pack(fill=tk.BOTH, expand=True)

        self.text_input = tk.Text(text_container, height=10, font=('微软雅黑', 11),
                                  wrap=tk.WORD, relief='solid', borderwidth=1,
                                  fg=self.colors['text'], bg='#FAFAFA')
        self.text_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 滚动条
        text_scroll = ttk.Scrollbar(text_container, orient='vertical', command=self.text_input.yview)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_input.config(yscrollcommand=text_scroll.set)

        # 右侧面板 - 输出区域
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 保存设置
        save_frame = self.create_section_frame(right_panel, "💾 保存设置")
        save_frame.pack(fill=tk.X, pady=(0, 10))

        # 保存路径
        path_row = ttk.Frame(save_frame)
        path_row.pack(fill=tk.X, pady=5)
        ttk.Label(path_row, text="保存目录:", width=8).pack(side=tk.LEFT)
        self.save_path = tk.StringVar(value=os.getcwd())
        path_entry = ttk.Entry(path_row, textvariable=self.save_path, font=('微软雅黑', 9))
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        ttk.Button(path_row, text="浏览", command=self.browse_save_path, width=8).pack(side=tk.RIGHT)

        # 文件名
        name_row = ttk.Frame(save_frame)
        name_row.pack(fill=tk.X, pady=5)
        ttk.Label(name_row, text="文件名:", width=8).pack(side=tk.LEFT)
        self.custom_filename = tk.StringVar(value="output")
        name_entry = ttk.Entry(name_row, textvariable=self.custom_filename, font=('微软雅黑', 9))
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(name_row, text=".wav", font=('微软雅黑', 9)).pack(side=tk.LEFT)

        # 操作按钮
        btn_frame = ttk.Frame(right_panel)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        btn_container = tk.Frame(btn_frame, bg=self.colors['white'])
        btn_container.pack(fill=tk.X)

        self.synth_btn = self.create_action_button(btn_container, "🔊 开始合成",
                                                   self.synthesize, self.colors['success'])
        self.synth_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.play_btn = self.create_action_button(btn_container, "▶ 播放",
                                                  self.play_audio, self.colors['primary'])
        self.play_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.play_btn.config(state=tk.DISABLED)

        self.export_btn = self.create_action_button(btn_container, "💾 导出",
                                                    self.export_audio, self.colors['warning'])
        self.export_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.export_btn.config(state=tk.DISABLED)

        # 进度条
        self.progress = ttk.Progressbar(right_panel, mode='indeterminate')

        # 信息标签
        self.info_label = tk.Label(right_panel, text="", bg=self.colors['white'],
                                   font=('微软雅黑', 9))
        self.info_label.pack(pady=(10, 0))

    def add_single_ref_audio(self):
        """添加单次合成的参考音频"""
        idx = len(self.single_ref_list)
        frame = tk.Frame(self.single_ref_container, bg=self.colors['white'])
        frame.pack(fill=tk.X, pady=3)

        # 序号标签
        num_label = tk.Label(frame, text=f"{idx + 1}.", width=5, anchor='w',
                             bg=self.colors['white'], fg=self.colors['primary'],
                             font=('微软雅黑', 10, 'bold'))
        num_label.pack(side=tk.LEFT)

        # 音频路径输入
        path_var = tk.StringVar()
        path_entry = ttk.Entry(frame, textvariable=path_var, font=('微软雅黑', 9), width=35)
        path_entry.pack(side=tk.LEFT, padx=(5, 0))

        # 浏览按钮
        browse_btn = ttk.Button(frame, text="浏览", width=6,
                                command=lambda v=path_var: self.browse_ref_audio(v))
        browse_btn.pack(side=tk.LEFT, padx=2)

        # 参考文本 - 不再使用placeholder，直接留空让用户填写
        text_var = tk.StringVar()
        text_entry = ttk.Entry(frame, textvariable=text_var, font=('微软雅黑', 9), width=30)
        text_entry.pack(side=tk.LEFT, padx=(5, 0))

        # 添加必填提示
        if idx == 0:
            text_entry.config(foreground=self.colors['danger'])
            tk.Label(frame, text="*", bg=self.colors['white'], fg=self.colors['danger'],
                     font=('微软雅黑', 10, 'bold')).pack(side=tk.LEFT, padx=(2, 0))

        # 删除按钮
        del_btn = ttk.Button(frame, text="删除", width=6,
                             command=lambda f=frame: self.remove_single_ref_audio(f))
        del_btn.pack(side=tk.LEFT, padx=(5, 0))

        self.single_ref_list.append({
            "frame": frame,
            "path_var": path_var,
            "text_var": text_var,
            "num_label": num_label,
            "text_entry": text_entry
        })

        self.update_single_ref_numbers()

    def remove_single_ref_audio(self, frame):
        """删除单次合成的参考音频"""
        if len(self.single_ref_list) <= 1:
            messagebox.showwarning("提示", "至少保留一个参考音频")
            return

        # 找到并删除对应的记录
        for i, ref in enumerate(self.single_ref_list):
            if ref["frame"] == frame:
                frame.destroy()
                self.single_ref_list.pop(i)
                break

        self.update_single_ref_numbers()

        # 更新第一个参考音频的必填标记
        if self.single_ref_list:
            first_ref = self.single_ref_list[0]
            first_ref["text_entry"].config(foreground=self.colors['danger'])
            # 检查是否已有红色星号，避免重复添加
            has_star = False
            for child in first_ref["frame"].winfo_children():
                if isinstance(child, tk.Label) and child.cget("text") == "*":
                    has_star = True
                    break
            if not has_star:
                tk.Label(first_ref["frame"], text="*", bg=self.colors['white'],
                         fg=self.colors['danger'], font=('微软雅黑', 10, 'bold')).pack(side=tk.LEFT, padx=(2, 0))

    def update_single_ref_numbers(self):
        """更新单次合成参考音频的序号"""
        for i, ref in enumerate(self.single_ref_list):
            ref["num_label"].config(text=f"{i + 1}.")
            # 第一个参考音频的文本用红色显示，表示必填
            if i == 0:
                ref["text_entry"].config(foreground=self.colors['danger'])
            else:
                ref["text_entry"].config(foreground='black')

    def browse_ref_audio(self, path_var):
        file_path = filedialog.askopenfilename(
            title="选择参考音频",
            filetypes=[("音频文件", "*.wav *.mp3 *.flac"), ("所有文件", "*.*")]
        )
        if file_path:
            path_var.set(file_path)

    def browse_save_path(self):
        dir_path = filedialog.askdirectory(title="选择保存文件夹")
        if dir_path:
            self.save_path.set(dir_path)

    def setup_batch_tab(self):
        """批量合成页面"""
        # 创建Canvas实现滚动
        canvas = tk.Canvas(self.batch_frame, bg=self.colors['white'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.batch_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 绑定滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # 提示信息
        info_frame = tk.Frame(scrollable_frame, bg='#E3F2FD', height=35)
        info_frame.pack(fill=tk.X, pady=(0, 15))
        info_frame.pack_propagate(False)
        tk.Label(info_frame, text="💡 批量合成：支持长文本自动分割（每500字一段），合成后自动合并",
                 bg='#E3F2FD', fg=self.colors['primary'], font=('微软雅黑', 10)).pack(pady=8)

        # 源文件夹
        source_frame = self.create_section_frame(scrollable_frame, "📂 源文件夹")
        source_frame.pack(fill=tk.X, pady=(0, 15))

        source_row = ttk.Frame(source_frame)
        source_row.pack(fill=tk.X)
        ttk.Entry(source_row, textvariable=self.batch_source_dir, font=('微软雅黑', 9)).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Button(source_row, text="浏览", command=self.browse_source_dir, width=10).pack(side=tk.RIGHT)

        filter_row = ttk.Frame(source_frame)
        filter_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(filter_row, text="文件类型:").pack(side=tk.LEFT)
        ttk.Entry(filter_row, textvariable=self.batch_file_pattern, width=12, font=('微软雅黑', 9)).pack(side=tk.LEFT,
                                                                                                         padx=10)
        ttk.Label(filter_row, text="(例如: *.txt)", foreground=self.colors['text_light']).pack(side=tk.LEFT)

        # 目标文件夹
        target_frame = self.create_section_frame(scrollable_frame, "💾 目标文件夹")
        target_frame.pack(fill=tk.X, pady=(0, 15))

        target_row = ttk.Frame(target_frame)
        target_row.pack(fill=tk.X)
        ttk.Entry(target_row, textvariable=self.batch_target_dir, font=('微软雅黑', 9)).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Button(target_row, text="浏览", command=self.browse_target_dir, width=10).pack(side=tk.RIGHT)

        # 命名规则
        naming_frame = self.create_section_frame(scrollable_frame, "📝 命名规则")
        naming_frame.pack(fill=tk.X, pady=(0, 15))

        naming_row = ttk.Frame(naming_frame)
        naming_row.pack(fill=tk.X)
        ttk.Label(naming_row, text="前缀:").pack(side=tk.LEFT)
        ttk.Entry(naming_row, textvariable=self.naming_prefix, width=12, font=('微软雅黑', 9)).pack(side=tk.LEFT,
                                                                                                    padx=5)
        ttk.Label(naming_row, text="分隔符:").pack(side=tk.LEFT, padx=(15, 0))
        ttk.Entry(naming_row, textvariable=self.naming_separator, width=4, font=('微软雅黑', 9)).pack(side=tk.LEFT,
                                                                                                      padx=5)
        ttk.Label(naming_row, text="后缀:").pack(side=tk.LEFT, padx=(15, 0))
        ttk.Entry(naming_row, textvariable=self.naming_suffix, width=12, font=('微软雅黑', 9)).pack(side=tk.LEFT,
                                                                                                    padx=5)

        example_row = ttk.Frame(naming_frame)
        example_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(example_row, text="示例: 前缀_0001_后缀.wav",
                  foreground=self.colors['text_light'], font=('微软雅黑', 9)).pack()

        # 参考音频区域
        ref_frame = self.create_section_frame(scrollable_frame, "🎵 参考音频设置")
        ref_frame.pack(fill=tk.X, pady=(0, 15))

        # 表头
        header_frame = tk.Frame(ref_frame, bg=self.colors['white'])
        header_frame.pack(fill=tk.X, pady=(0, 5))

        tk.Label(header_frame, text="序号", bg=self.colors['white'],
                 font=('微软雅黑', 9, 'bold'), width=5, anchor='w').pack(side=tk.LEFT)
        tk.Label(header_frame, text="参考音频路径", bg=self.colors['white'],
                 font=('微软雅黑', 9, 'bold'), width=35, anchor='w').pack(side=tk.LEFT, padx=(5, 0))
        tk.Label(header_frame, text="参考文本（必填）", bg=self.colors['white'],
                 font=('微软雅黑', 9, 'bold'), width=30, anchor='w').pack(side=tk.LEFT, padx=(5, 0))
        tk.Label(header_frame, text="操作", bg=self.colors['white'],
                 font=('微软雅黑', 9, 'bold'), width=8, anchor='w').pack(side=tk.LEFT, padx=(5, 0))

        # 分隔线
        separator = tk.Frame(ref_frame, height=1, bg=self.colors['border'])
        separator.pack(fill=tk.X, pady=(0, 5))

        tk.Label(ref_frame, text="💡 提示：第一个音频为主参考，参考文本建议填写音频对应的文字内容",
                 bg=self.colors['white'], fg=self.colors['text_light'],
                 font=('微软雅黑', 9)).pack(anchor='w', pady=(0, 5))

        self.batch_ref_container = ttk.Frame(ref_frame)
        self.batch_ref_container.pack(fill=tk.X)

        add_btn = self.create_action_button(ref_frame, "+ 添加参考音频",
                                            self.add_batch_ref_audio, self.colors['success'])
        add_btn.pack(pady=(10, 0))

        self.batch_ref_list = []
        self.add_batch_ref_audio()

        # 高级选项
        advanced_frame = self.create_section_frame(scrollable_frame, "⚙️ 高级选项")
        advanced_frame.pack(fill=tk.X, pady=(0, 15))

        split_row = ttk.Frame(advanced_frame)
        split_row.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(split_row, text="启用长文本自动分割", variable=self.enable_split).pack(side=tk.LEFT)
        ttk.Label(split_row, text="每段最大字符数:").pack(side=tk.LEFT, padx=(20, 5))
        ttk.Spinbox(split_row, from_=200, to=1000, textvariable=self.max_chunk_size, width=8).pack(side=tk.LEFT)
        ttk.Label(split_row, text="(建议500字)", foreground=self.colors['text_light']).pack(side=tk.LEFT, padx=5)

        delay_row = ttk.Frame(advanced_frame)
        delay_row.pack(fill=tk.X, pady=5)
        ttk.Label(delay_row, text="文件间延迟(秒):").pack(side=tk.LEFT)
        ttk.Spinbox(delay_row, from_=0, to=5, increment=0.1, textvariable=self.batch_delay, width=8).pack(side=tk.LEFT,
                                                                                                          padx=5)
        ttk.Label(delay_row, text="避免请求过快", foreground=self.colors['text_light']).pack(side=tk.LEFT, padx=5)

        # 文件列表
        list_frame = self.create_section_frame(scrollable_frame, "📋 待处理文件列表")
        list_frame.pack(fill=tk.X, pady=(0, 15))

        list_container = tk.Frame(list_frame, bg=self.colors['white'])
        list_container.pack(fill=tk.X)

        list_scroll = ttk.Scrollbar(list_container)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.batch_listbox = tk.Listbox(list_container, yscrollcommand=list_scroll.set,
                                        height=8, font=('微软雅黑', 9),
                                        bg='#FAFAFA', relief='solid', borderwidth=1)
        self.batch_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        list_scroll.config(command=self.batch_listbox.yview)

        ttk.Button(list_frame, text="🔄 刷新文件列表", command=self.refresh_file_list).pack(pady=(10, 0))

        # 进度条
        self.batch_progress = ttk.Progressbar(scrollable_frame, mode='determinate')
        self.batch_progress.pack(fill=tk.X, pady=(0, 10))

        # 状态信息
        self.batch_status = tk.StringVar(value="就绪")
        tk.Label(scrollable_frame, textvariable=self.batch_status,
                 bg=self.colors['white'], fg=self.colors['text_light'],
                 font=('微软雅黑', 9)).pack()

        # 控制按钮
        btn_frame = tk.Frame(scrollable_frame, bg=self.colors['white'])
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        self.start_batch_btn = self.create_action_button(btn_frame, "▶ 开始批量合成",
                                                         self.start_batch, self.colors['success'])
        self.start_batch_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.pause_batch_btn = self.create_action_button(btn_frame, "⏸ 暂停",
                                                         self.pause_batch, self.colors['warning'])
        self.pause_batch_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.pause_batch_btn.config(state=tk.DISABLED)

        self.stop_batch_btn = self.create_action_button(btn_frame, "⏹ 停止",
                                                        self.stop_batch, self.colors['danger'])
        self.stop_batch_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.stop_batch_btn.config(state=tk.DISABLED)

    def add_batch_ref_audio(self):
        """添加批量合成的参考音频"""
        idx = len(self.batch_ref_list)
        frame = tk.Frame(self.batch_ref_container, bg=self.colors['white'])
        frame.pack(fill=tk.X, pady=3)

        num_label = tk.Label(frame, text=f"{idx + 1}.", width=5, anchor='w',
                             bg=self.colors['white'], fg=self.colors['primary'],
                             font=('微软雅黑', 10, 'bold'))
        num_label.pack(side=tk.LEFT)

        path_var = tk.StringVar()
        path_entry = ttk.Entry(frame, textvariable=path_var, font=('微软雅黑', 9), width=35)
        path_entry.pack(side=tk.LEFT, padx=(5, 0))

        browse_btn = ttk.Button(frame, text="浏览", width=6,
                                command=lambda v=path_var: self.browse_ref_audio(v))
        browse_btn.pack(side=tk.LEFT, padx=2)

        text_var = tk.StringVar()
        text_entry = ttk.Entry(frame, textvariable=text_var, font=('微软雅黑', 9), width=30)
        text_entry.pack(side=tk.LEFT, padx=(5, 0))

        if idx == 0:
            text_entry.config(foreground=self.colors['danger'])
            tk.Label(frame, text="*", bg=self.colors['white'], fg=self.colors['danger'],
                     font=('微软雅黑', 10, 'bold')).pack(side=tk.LEFT, padx=(2, 0))

        del_btn = ttk.Button(frame, text="删除", width=6,
                             command=lambda f=frame: self.remove_batch_ref_audio(f))
        del_btn.pack(side=tk.LEFT, padx=(5, 0))

        self.batch_ref_list.append({
            "frame": frame,
            "path_var": path_var,
            "text_var": text_var,
            "num_label": num_label,
            "text_entry": text_entry
        })

        self.update_batch_ref_numbers()

    def remove_batch_ref_audio(self, frame):
        """删除批量合成的参考音频"""
        if len(self.batch_ref_list) <= 1:
            messagebox.showwarning("提示", "至少保留一个参考音频")
            return

        for i, ref in enumerate(self.batch_ref_list):
            if ref["frame"] == frame:
                frame.destroy()
                self.batch_ref_list.pop(i)
                break

        self.update_batch_ref_numbers()

        if self.batch_ref_list:
            first_ref = self.batch_ref_list[0]
            first_ref["text_entry"].config(foreground=self.colors['danger'])
            has_star = False
            for child in first_ref["frame"].winfo_children():
                if isinstance(child, tk.Label) and child.cget("text") == "*":
                    has_star = True
                    break
            if not has_star:
                tk.Label(first_ref["frame"], text="*", bg=self.colors['white'],
                         fg=self.colors['danger'], font=('微软雅黑', 10, 'bold')).pack(side=tk.LEFT, padx=(2, 0))

    def update_batch_ref_numbers(self):
        """更新批量合成参考音频的序号"""
        for i, ref in enumerate(self.batch_ref_list):
            ref["num_label"].config(text=f"{i + 1}.")
            if i == 0:
                ref["text_entry"].config(foreground=self.colors['danger'])
            else:
                ref["text_entry"].config(foreground='black')

    def setup_params_tab(self):
        """参数设置页面"""
        canvas = tk.Canvas(self.params_frame, bg=self.colors['white'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.params_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 基础参数
        basic_group = self.create_section_frame(scrollable_frame, "🎛️ 基础参数")
        basic_group.pack(fill=tk.X, pady=(0, 15))

        params = [
            ("Top K (采样范围)", self.top_k, 1, 100),
            ("Top P (核采样)", self.top_p, 0.1, 1.0),
            ("Temperature (温度)", self.temperature, 0.1, 2.0),
            ("重复惩罚", self.repetition_penalty, 1.0, 2.0),
            ("语速系数", self.speed_factor, 0.5, 2.0),
            ("采样步数(越小越快)", self.sample_steps, 1, 50),
        ]

        for label_text, var, min_val, max_val in params:
            row = ttk.Frame(basic_group)
            row.pack(fill=tk.X, pady=8)

            ttk.Label(row, text=f"{label_text}:", width=20, anchor='w').pack(side=tk.LEFT)

            if isinstance(var, tk.IntVar):
                scale = tk.Scale(row, from_=min_val, to=max_val, orient="horizontal",
                                 variable=var, length=300, bg=self.colors['white'],
                                 highlightthickness=0, troughcolor='#E0E0E0',
                                 activebackground=self.colors['primary'])
            else:
                scale = tk.Scale(row, from_=min_val, to=max_val, resolution=0.01,
                                 orient="horizontal", variable=var, length=300,
                                 bg=self.colors['white'], highlightthickness=0,
                                 troughcolor='#E0E0E0', activebackground=self.colors['primary'])
            scale.pack(side=tk.LEFT, padx=10)

            value_label = tk.Label(row, textvariable=var, bg=self.colors['white'],
                                   fg=self.colors['primary'], font=('微软雅黑', 10, 'bold'), width=6)
            value_label.pack(side=tk.LEFT)

        # 分割方式
        split_row = ttk.Frame(basic_group)
        split_row.pack(fill=tk.X, pady=8)
        ttk.Label(split_row, text="文本分割方式:", width=20, anchor='w').pack(side=tk.LEFT)
        split_combo = ttk.Combobox(split_row, textvariable=self.text_split_method,
                                   values=["cut5", "cut0", "cut1", "cut2", "cut3", "cut4"],
                                   width=15, state='readonly')
        split_combo.pack(side=tk.LEFT, padx=10)

        # 重置按钮
        reset_btn = self.create_action_button(scrollable_frame, "🔄 重置所有参数",
                                              self.reset_params, self.colors['primary'])
        reset_btn.pack(pady=15)

    def setup_model_tab(self):
        """模型管理页面"""
        # 当前模型状态
        status_group = self.create_section_frame(self.model_frame, "📊 当前模型状态")
        status_group.pack(fill=tk.X, pady=(0, 15))

        self.model_gpt_label = tk.Label(status_group, text="GPT 模型: 未加载",
                                        bg=self.colors['white'], font=('微软雅黑', 10))
        self.model_gpt_label.pack(anchor='w', pady=5)

        self.model_sovits_label = tk.Label(status_group, text="SoVITS 模型: 未加载",
                                           bg=self.colors['white'], font=('微软雅黑', 10))
        self.model_sovits_label.pack(anchor='w', pady=5)

        # 模型列表 - 左右分栏
        list_group = self.create_section_frame(self.model_frame, "📋 可用模型列表")
        list_group.pack(fill=tk.BOTH, expand=True)

        # GPT模型列表
        gpt_container = ttk.Frame(list_group)
        gpt_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        tk.Label(gpt_container, text="GPT 模型", bg=self.colors['white'],
                 font=('微软雅黑', 10, 'bold')).pack(anchor='w', pady=(0, 5))

        gpt_list_frame = tk.Frame(gpt_container, bg=self.colors['white'])
        gpt_list_frame.pack(fill=tk.BOTH, expand=True)

        gpt_scroll = ttk.Scrollbar(gpt_list_frame)
        gpt_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.gpt_listbox = tk.Listbox(gpt_list_frame, yscrollcommand=gpt_scroll.set,
                                      height=12, font=('微软雅黑', 9),
                                      bg='#FAFAFA', relief='solid', borderwidth=1)
        self.gpt_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        gpt_scroll.config(command=self.gpt_listbox.yview)

        # SoVITS模型列表
        sovits_container = ttk.Frame(list_group)
        sovits_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        tk.Label(sovits_container, text="SoVITS 模型", bg=self.colors['white'],
                 font=('微软雅黑', 10, 'bold')).pack(anchor='w', pady=(0, 5))

        sovits_list_frame = tk.Frame(sovits_container, bg=self.colors['white'])
        sovits_list_frame.pack(fill=tk.BOTH, expand=True)

        sovits_scroll = ttk.Scrollbar(sovits_list_frame)
        sovits_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.sovits_listbox = tk.Listbox(sovits_list_frame, yscrollcommand=sovits_scroll.set,
                                         height=12, font=('微软雅黑', 9),
                                         bg='#FAFAFA', relief='solid', borderwidth=1)
        self.sovits_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sovits_scroll.config(command=self.sovits_listbox.yview)

        # 操作按钮
        btn_frame = tk.Frame(self.model_frame, bg=self.colors['white'])
        btn_frame.pack(fill=tk.X, pady=15)

        self.create_action_button(btn_frame, "🔄 刷新模型列表",
                                  self.refresh_models, self.colors['primary']).pack(
            side=tk.LEFT, padx=(0, 10))

        self.create_action_button(btn_frame, "✅ 切换选中模型",
                                  self.switch_selected_model, self.colors['success']).pack(side=tk.LEFT)

    # ========== 工具函数 ==========
    def browse_source_dir(self):
        dir_path = filedialog.askdirectory(title="选择txt文件所在文件夹")
        if dir_path:
            self.batch_source_dir.set(dir_path)
            self.refresh_file_list()

    def browse_target_dir(self):
        dir_path = filedialog.askdirectory(title="选择音频保存文件夹")
        if dir_path:
            self.batch_target_dir.set(dir_path)

    def refresh_file_list(self):
        source_dir = self.batch_source_dir.get()
        if not source_dir or not os.path.exists(source_dir):
            self.batch_listbox.delete(0, tk.END)
            return

        pattern = self.batch_file_pattern.get()
        files = glob.glob(os.path.join(source_dir, pattern))
        files.sort()

        self.batch_file_list = files
        self.batch_listbox.delete(0, tk.END)
        for f in files:
            self.batch_listbox.insert(tk.END, os.path.basename(f))

        self.batch_status.set(f"找到 {len(files)} 个文件")

    def split_text(self, text, max_len=500):
        """将长文本分割成多个片段"""
        if not self.enable_split.get() or len(text) <= max_len:
            return [text]

        sentences = re.split(r'([。！？；])', text)
        sentences = [''.join(i) for i in zip(sentences[0::2], sentences[1::2])]

        chunks = []
        current_chunk = ""

        for sent in sentences:
            if len(current_chunk) + len(sent) <= max_len:
                current_chunk += sent
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                if len(sent) > max_len:
                    for i in range(0, len(sent), max_len):
                        chunks.append(sent[i:i + max_len])
                    current_chunk = ""
                else:
                    current_chunk = sent

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def merge_audio_files(self, file_list, output_path):
        """合并多个音频文件"""
        if len(file_list) == 1:
            import shutil
            shutil.copy(file_list[0], output_path)
            return True

        try:
            list_file = output_path.replace(".wav", "_list.txt")
            with open(list_file, "w", encoding="utf-8") as f:
                for file_path in file_list:
                    f.write(f"file '{os.path.abspath(file_path)}'\n")

            cmd = f'ffmpeg -f concat -safe 0 -i "{list_file}" -c copy "{output_path}" -y'
            subprocess.run(cmd, shell=True, capture_output=True)

            os.remove(list_file)
            return os.path.exists(output_path)
        except Exception as e:
            print(f"合并失败: {e}")
            return False

    def get_ref_audio_list(self, ref_list):
        """获取参考音频路径和文本列表"""
        paths = []
        texts = []
        for ref in ref_list:
            path = ref["path_var"].get().strip()
            if path and os.path.exists(path):
                paths.append(path)
                text = ref["text_var"].get().strip()
                texts.append(text)
        return paths, texts

    # ========== 单次合成 ==========
    def synthesize(self):
        if not self.backend_available:
            messagebox.showwarning("提示", "后端未连接")
            return

        paths, texts = self.get_ref_audio_list(self.single_ref_list)
        if not paths:
            messagebox.showwarning("提示", "请至少添加一个有效的参考音频")
            return

        # 检查主参考音频的参考文本是否填写
        if not texts or not texts[0]:
            messagebox.showwarning("提示", "主参考音频的参考文本不能为空！\n请填写参考音频对应的文字内容。")
            return

        text = self.text_input.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("提示", "请输入要合成的文本")
            return

        lang_map = {"zh (中文)": "zh", "en (英文)": "en", "ja (日文)": "ja"}
        text_lang = lang_map.get(self.text_lang.get(), "zh")

        os.makedirs(self.save_path.get(), exist_ok=True)
        filename = self.custom_filename.get().strip()
        if not filename:
            filename = "output"
        output_path = os.path.join(self.save_path.get(), f"{filename}.wav")

        self.synth_btn.config(state=tk.DISABLED)
        self.play_btn.config(state=tk.DISABLED)
        self.export_btn.config(state=tk.DISABLED)
        self.progress.pack(fill=tk.X, pady=(10, 0))
        self.progress.start()
        self.info_label.config(text="正在合成...", fg=self.colors['primary'])

        def do_synthesis():
            try:
                chunks = self.split_text(text, self.max_chunk_size.get())

                if len(chunks) == 1:
                    success, msg = self.synthesize_single(chunks[0], text_lang, paths, texts, output_path)
                    if success:
                        self.current_audio = output_path
                        self.root.after(0, lambda: self.on_success(f"合成成功！保存至: {output_path}"))
                    else:
                        self.root.after(0, lambda: self.on_error(f"合成失败: {msg}"))
                else:
                    self.info_label.config(text=f"长文本已分割为 {len(chunks)} 段，正在合成...",
                                           fg=self.colors['primary'])
                    temp_files = []
                    success_all = True

                    for i, chunk in enumerate(chunks):
                        temp_path = output_path.replace(".wav", f"_temp_{i}.wav")
                        success, msg = self.synthesize_single(chunk, text_lang, paths, texts, temp_path)
                        if success:
                            temp_files.append(temp_path)
                            self.root.after(0, lambda c=i + 1, t=len(chunks):
                            self.info_label.config(text=f"已合成 {c}/{t} 段", fg=self.colors['primary']))
                        else:
                            success_all = False
                            break

                    if success_all and self.merge_audio_files(temp_files, output_path):
                        for f in temp_files:
                            try:
                                os.remove(f)
                            except:
                                pass
                        self.current_audio = output_path
                        self.root.after(0, lambda: self.on_success(f"合成成功！保存至: {output_path}"))
                    else:
                        self.root.after(0, lambda: self.on_error("分段合成失败"))
            except Exception as e:
                self.root.after(0, lambda: self.on_error(f"异常: {str(e)}"))
            finally:
                self.root.after(0, self.stop_progress)

        threading.Thread(target=do_synthesis, daemon=True).start()

    def synthesize_single(self, text, text_lang, ref_paths, ref_texts, output_path):
        """合成单段文本"""
        params = {
            "text": text,
            "text_lang": text_lang,
            "ref_audio_path": ref_paths[0] if ref_paths else "",
            "aux_ref_audio_paths": ref_paths[1:] if len(ref_paths) > 1 else [],
            "prompt_text": ref_texts[0] if ref_texts else "",
            "prompt_lang": "zh",
            "media_type": "wav",
            "top_k": self.top_k.get(),
            "top_p": self.top_p.get(),
            "temperature": self.temperature.get(),
            "repetition_penalty": self.repetition_penalty.get(),
            "speed_factor": self.speed_factor.get(),
            "sample_steps": self.sample_steps.get(),
            "text_split_method": self.text_split_method.get()
        }

        try:
            response = requests.post(f"{self.api_base}/tts", json=params, timeout=180)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return True, "成功"
            else:
                return False, response.text
        except Exception as e:
            return False, str(e)

    def on_success(self, message):
        self.info_label.config(text=message, fg=self.colors['success'])
        self.play_btn.config(state=tk.NORMAL)
        self.export_btn.config(state=tk.NORMAL)
        messagebox.showinfo("成功", "合成完成！")
        self.play_audio()

    def on_error(self, message):
        self.info_label.config(text=message, fg=self.colors['danger'])
        messagebox.showerror("错误", message)

    def stop_progress(self):
        self.progress.stop()
        self.progress.pack_forget()
        self.synth_btn.config(state=tk.NORMAL if self.backend_available else tk.DISABLED)

    def play_audio(self):
        if self.current_audio and os.path.exists(self.current_audio):
            os.startfile(self.current_audio)

    def export_audio(self):
        if not self.current_audio or not os.path.exists(self.current_audio):
            messagebox.showwarning("提示", "没有可导出的音频")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV 文件", "*.wav"), ("所有文件", "*.*")]
        )
        if file_path:
            import shutil
            shutil.copy(self.current_audio, file_path)
            messagebox.showinfo("成功", f"已保存到: {file_path}")

    # ========== 批量合成 ==========
    def start_batch(self):
        if not self.backend_available:
            messagebox.showwarning("提示", "后端未连接")
            return

        source_dir = self.batch_source_dir.get()
        if not source_dir or not os.path.exists(source_dir):
            messagebox.showwarning("提示", "请选择有效的源文件夹")
            return

        target_dir = self.batch_target_dir.get()
        if not target_dir:
            target_dir = source_dir
            self.batch_target_dir.set(target_dir)

        os.makedirs(target_dir, exist_ok=True)

        paths, texts = self.get_ref_audio_list(self.batch_ref_list)
        if not paths:
            messagebox.showwarning("提示", "请至少添加一个有效的参考音频")
            return

        # 检查主参考音频的参考文本是否填写
        if not texts or not texts[0]:
            messagebox.showwarning("提示", "主参考音频的参考文本不能为空！\n请填写参考音频对应的文字内容。")
            return

        self.refresh_file_list()
        if not self.batch_file_list:
            messagebox.showwarning("提示", "没有找到符合条件的文件")
            return

        self.batch_running = True
        self.batch_paused = False
        self.batch_stop = False
        self.batch_current_index = 0

        self.start_batch_btn.config(state=tk.DISABLED)
        self.pause_batch_btn.config(state=tk.NORMAL)
        self.stop_batch_btn.config(state=tk.NORMAL)

        self.batch_progress["maximum"] = len(self.batch_file_list)
        self.batch_progress["value"] = 0

        threading.Thread(target=self.batch_process, args=(paths, texts, target_dir), daemon=True).start()

    def batch_process(self, ref_paths, ref_texts, target_dir):
        lang_map = {"zh (中文)": "zh", "en (英文)": "en", "ja (日文)": "ja"}
        text_lang = lang_map.get("zh (中文)", "zh")

        prefix = self.naming_prefix.get()
        suffix = self.naming_suffix.get()
        separator = self.naming_separator.get()

        for i, file_path in enumerate(self.batch_file_list):
            while self.batch_paused and not self.batch_stop:
                time.sleep(0.5)

            if self.batch_stop:
                break

            self.batch_current_index = i
            filename = os.path.basename(file_path)
            name_without_ext = os.path.splitext(filename)[0]

            if prefix or suffix:
                parts = [p for p in [prefix, name_without_ext, suffix] if p]
                output_name = separator.join(parts)
            else:
                output_name = name_without_ext
            output_path = os.path.join(target_dir, f"{output_name}.wav")

            if os.path.exists(output_path):
                self.root.after(0, lambda f=filename: self.batch_status.set(f"跳过已存在: {f}"))
                self.root.after(0, lambda: self.batch_progress.step(1))
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read().strip()
                if not text:
                    self.root.after(0, lambda f=filename: self.batch_status.set(f"跳过空文件: {f}"))
                    self.root.after(0, lambda: self.batch_progress.step(1))
                    continue
            except Exception as e:
                self.root.after(0, lambda f=filename, err=str(e): self.batch_status.set(f"读取失败 {f}: {err}"))
                self.root.after(0, lambda: self.batch_progress.step(1))
                continue

            self.root.after(0, lambda f=filename, idx=i + 1, total=len(self.batch_file_list):
            self.batch_status.set(f"正在合成: {f} ({idx}/{total})"))

            chunks = self.split_text(text, self.max_chunk_size.get())

            if len(chunks) == 1:
                success, msg = self.synthesize_single(chunks[0], text_lang, ref_paths, ref_texts, output_path)
                if success:
                    self.root.after(0, lambda f=filename: self.batch_status.set(f"完成: {f}"))
                else:
                    self.root.after(0, lambda f=filename, err=msg: self.batch_status.set(f"失败 {f}: {err}"))
            else:
                self.root.after(0, lambda f=filename, cnt=len(chunks):
                self.batch_status.set(f"分段合成 {f} ({cnt}段)"))

                temp_files = []
                success_all = True

                for j, chunk in enumerate(chunks):
                    temp_path = output_path.replace(".wav", f"_temp_{j}.wav")
                    success, msg = self.synthesize_single(chunk, text_lang, ref_paths, ref_texts, temp_path)
                    if success:
                        temp_files.append(temp_path)
                    else:
                        success_all = False
                        self.root.after(0, lambda f=filename, err=msg: self.batch_status.set(f"分段失败 {f}: {err}"))
                        break

                if success_all and self.merge_audio_files(temp_files, output_path):
                    for tf in temp_files:
                        try:
                            os.remove(tf)
                        except:
                            pass
                    self.root.after(0, lambda f=filename: self.batch_status.set(f"完成: {f}"))
                else:
                    self.root.after(0, lambda f=filename: self.batch_status.set(f"合并失败: {f}"))

            self.root.after(0, lambda: self.batch_progress.step(1))
            time.sleep(self.batch_delay.get())

        self.batch_running = False
        self.root.after(0, self.batch_finished)

    def batch_finished(self):
        self.start_batch_btn.config(state=tk.NORMAL)
        self.pause_batch_btn.config(state=tk.DISABLED, text="⏸ 暂停")
        self.stop_batch_btn.config(state=tk.DISABLED)

        if self.batch_stop:
            self.batch_status.set("批量合成已停止")
        else:
            self.batch_status.set("批量合成完成！")
            messagebox.showinfo("完成", "批量合成已完成！")

    def pause_batch(self):
        if not self.batch_running:
            return

        if not self.batch_paused:
            self.batch_paused = True
            self.pause_batch_btn.config(text="▶ 继续")
            self.batch_status.set("已暂停")
        else:
            self.batch_paused = False
            self.pause_batch_btn.config(text="⏸ 暂停")
            self.batch_status.set("继续合成...")

    def stop_batch(self):
        self.batch_stop = True
        self.batch_paused = False
        self.batch_status.set("正在停止...")

    def open_output_folder(self):
        target_dir = self.batch_target_dir.get()
        if target_dir and os.path.exists(target_dir):
            os.startfile(target_dir)
        else:
            messagebox.showwarning("提示", "输出文件夹不存在")

    # ========== 模型管理 ==========
    def scan_local_models(self):
        self.gpt_models = []
        self.sovits_models = []

        gpt_dirs = ["GPT_weights_v2", "GPT_weights"]
        for gpt_dir in gpt_dirs:
            if os.path.exists(gpt_dir):
                for f in glob.glob(f"{gpt_dir}/*.ckpt") + glob.glob(f"{gpt_dir}/*.pth"):
                    name = os.path.basename(f).replace(".ckpt", "").replace(".pth", "")
                    if name not in self.gpt_models:
                        self.gpt_models.append(name)

        sovits_dirs = ["SoVITS_weights_v2", "SoVITS_weights"]
        for sovits_dir in sovits_dirs:
            if os.path.exists(sovits_dir):
                for f in glob.glob(f"{sovits_dir}/*.ckpt") + glob.glob(f"{sovits_dir}/*.pth"):
                    name = os.path.basename(f).replace(".ckpt", "").replace(".pth", "")
                    if name not in self.sovits_models:
                        self.sovits_models.append(name)

        if self.gpt_models:
            self.current_gpt.set(self.gpt_models[0])
        if self.sovits_models:
            self.current_sovits.set(self.sovits_models[0])

        if hasattr(self, 'gpt_listbox') and self.gpt_listbox:
            self.gpt_listbox.delete(0, tk.END)
            for m in self.gpt_models:
                self.gpt_listbox.insert(tk.END, m)

        if hasattr(self, 'sovits_listbox') and self.sovits_listbox:
            self.sovits_listbox.delete(0, tk.END)
            for m in self.sovits_models:
                self.sovits_listbox.insert(tk.END, m)

    def refresh_models(self):
        self.scan_local_models()

    def switch_model(self):
        if not self.backend_available:
            messagebox.showwarning("提示", "后端未连接")
            return

        gpt_model = self.current_gpt.get()
        sovits_model = self.current_sovits.get()

        def switch():
            try:
                if gpt_model:
                    gpt_path = f"GPT_weights_v2/{gpt_model}.ckpt"
                    if not os.path.exists(gpt_path):
                        gpt_path = f"GPT_weights_v2/{gpt_model}.pth"
                    if os.path.exists(gpt_path):
                        resp = requests.get(f"{self.api_base}/set_gpt_weights", params={"weights_path": gpt_path},
                                            timeout=30)
                        if resp.status_code == 200:
                            self.root.after(0, lambda: self.update_model_labels(gpt=gpt_model))

                if sovits_model:
                    sovits_path = f"SoVITS_weights_v2/{sovits_model}.pth"
                    if not os.path.exists(sovits_path):
                        sovits_path = f"SoVITS_weights_v2/{sovits_model}.ckpt"
                    if os.path.exists(sovits_path):
                        resp = requests.get(f"{self.api_base}/set_sovits_weights", params={"weights_path": sovits_path},
                                            timeout=30)
                        if resp.status_code == 200:
                            self.root.after(0, lambda: self.update_model_labels(sovits=sovits_model))

                messagebox.showinfo("成功", "模型切换完成")
            except Exception as e:
                if hasattr(self, 'info_label'):
                    self.info_label.config(text=f"切换失败: {str(e)}", fg=self.colors['danger'])

        threading.Thread(target=switch, daemon=True).start()

    def update_model_labels(self, gpt=None, sovits=None):
        """更新模型标签"""
        if gpt:
            short_name = gpt[:30] + "..." if len(gpt) > 30 else gpt
            self.current_gpt_label.config(text=f"GPT: {short_name}")
            if hasattr(self, 'model_gpt_label'):
                self.model_gpt_label.config(text=f"GPT 模型: {gpt}")
        if sovits:
            short_name = sovits[:30] + "..." if len(sovits) > 30 else sovits
            self.current_sovits_label.config(text=f"SoVITS: {short_name}")
            if hasattr(self, 'model_sovits_label'):
                self.model_sovits_label.config(text=f"SoVITS 模型: {sovits}")

    def switch_selected_model(self):
        gpt_selection = self.gpt_listbox.curselection()
        sovits_selection = self.sovits_listbox.curselection()

        if gpt_selection:
            self.current_gpt.set(self.gpt_listbox.get(gpt_selection[0]))
        if sovits_selection:
            self.current_sovits.set(self.sovits_listbox.get(sovits_selection[0]))

        self.switch_model()

    def reset_params(self):
        self.top_k.set(10)
        self.top_p.set(0.8)
        self.temperature.set(0.8)
        self.repetition_penalty.set(1.2)
        self.speed_factor.set(1.0)
        self.sample_steps.set(4)
        self.text_split_method.set("cut5")
        self.max_chunk_size.set(500)
        self.enable_split.set(True)
        if hasattr(self, 'info_label'):
            self.info_label.config(text="参数已重置为快速模式", fg=self.colors['success'])

    def check_backend(self):
        self.status_label.config(text="🔍 检测后端中...", fg=self.colors['warning'])

        def check():
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('127.0.0.1', 9880))
                sock.close()

                if result == 0:
                    self.backend_available = True
                    self.root.after(0, lambda: self.status_label.config(text="✅ 后端已连接", fg=self.colors['success']))
                    if hasattr(self, 'synth_btn'):
                        self.root.after(0, lambda: self.synth_btn.config(state=tk.NORMAL))
                else:
                    self.backend_unavailable()
            except:
                self.backend_unavailable()

        threading.Thread(target=check, daemon=True).start()

    def backend_unavailable(self):
        self.backend_available = False
        self.status_label.config(text="❌ 后端未启动！请先运行「启动后端.bat」", fg=self.colors['danger'])
        if hasattr(self, 'synth_btn'):
            self.synth_btn.config(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = TTSApp(root)
    root.mainloop()