import os
import tkinter as tk
from tkinter import filedialog, messagebox
import chardet  # 需要安装：pip install chardet

SIZE = 3000

root = tk.Tk()
root.withdraw()

# ========== 第一步：选择输入文件 ==========
messagebox.showinfo("提示", "现在请选择要切分的文本文件")
INPUT = filedialog.askopenfilename(
    title="请选择要切分的文本文件",
    filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
)
if not INPUT:
    messagebox.showinfo("提示", "未选择文件，程序退出")
    exit()

print(f"已选择文件: {os.path.basename(INPUT)}")

# ========== 第二步：选择输出文件夹 ==========
messagebox.showinfo("提示", "现在请选择切片保存的文件夹")
OUT_DIR = filedialog.askdirectory(
    title="请选择切片保存的文件夹"
)
if not OUT_DIR:
    messagebox.showinfo("提示", "未选择文件夹，程序退出")
    exit()

print(f"保存路径: {OUT_DIR}")

os.makedirs(OUT_DIR, exist_ok=True)

# ========== 第三步：读取并处理文件 ==========
print("正在检测文件编码...")
# 自动检测文件编码
with open(INPUT, "rb") as f:
    raw_data = f.read(100000)  # 读取前100KB用于检测
    result = chardet.detect(raw_data)
    encoding = result["encoding"]
    confidence = result.get("confidence", 0) * 100
    print(f"检测到编码：{encoding} (置信度: {confidence:.1f}%)")

print("正在读取文件内容...")
# 使用检测到的编码读取
with open(INPUT, "r", encoding=encoding, errors="ignore") as f:
    paras = f.read().splitlines(keepends=True)

total_chars = sum(len(p) for p in paras)
print(f"文件总字符数: {total_chars}")

buf = ""
idx = 0
file_count = 0

print("\n开始切分文件...")
for i, p in enumerate(paras, 1):
    if len(buf) + len(p) > SIZE and buf:
        output_file = os.path.join(OUT_DIR, f"{idx:04d}.txt")
        with open(output_file, "w", encoding="utf-8") as out:
            out.write(buf)
        print(f"  生成切片 #{idx + 1}: {idx:04d}.txt ({len(buf)} 字符)")
        idx += 1
        buf = ""
    buf += p

    # 显示进度
    if i % 100 == 0:
        print(f"  处理进度: {i}/{len(paras)} 段落")

# 保存最后一个切片
if buf:
    output_file = os.path.join(OUT_DIR, f"{idx:04d}.txt")
    with open(output_file, "w", encoding="utf-8") as out:
        out.write(buf)
    print(f"  生成切片 #{idx + 1}: {idx:04d}.txt ({len(buf)} 字符)")
    idx += 1

print(f"\n处理完成！共生成 {idx} 个切片文件")

# ========== 第四步：完成提示 ==========
messagebox.showinfo(
    "完成",
    f"切分完成！\n\n"
    f"源文件: {os.path.basename(INPUT)}\n"
    f"总字符数: {total_chars}\n"
    f"生成切片: {idx} 个\n"
    f"保存位置: {OUT_DIR}"
)