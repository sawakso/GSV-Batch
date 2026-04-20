@echo off
chcp 65001 >nul
title 小说文本剪切工具

cd /d "%~dp0"

echo ========================================
echo        小说文本剪切工具
echo ========================================
echo.
echo 正在启动...
timeout /t 1 /nobreak >nul

:: 使用 pythonw.exe 隐藏命令行，直接打开 GUI
start "" "%~dp0runtime\pythonw.exe" "%~dp0小说剪切.py"

exit