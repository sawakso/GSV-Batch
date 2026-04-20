@echo off
chcp 65001 >nul
title GPT-SoVITS 前端启动器

cd /d "%~dp0"

echo ========================================
echo      GPT-SoVITS 前端 GUI
echo ========================================
echo.

:: 检查后端服务
echo 正在检查后端服务...
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:9880/docs' -TimeoutSec 2 -UseBasicParsing; exit 0 } catch { exit 1 }" >nul 2>&1

if %errorlevel% equ 0 (
    echo [成功] 后端 API 已就绪
    goto :start_gui
)

:: 后端未就绪
echo [提示] 后端服务未启动或未就绪
echo.
choice /c yn /n /m "是否等待后端启动？(Y/N): "
if errorlevel 2 goto :start_gui

echo.
echo 等待后端服务就绪 (超时 60 秒将自动退出)...
set /a count=0
:wait_loop
timeout /t 2 /nobreak >nul
set /a count+=1

powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:9880/docs' -TimeoutSec 2 -UseBasicParsing; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo [成功] 后端服务已就绪！
    goto :start_gui
)

:: 超时检测 - 30次 × 2秒 = 60秒
if %count% geq 30 (
    echo.
    echo ========================================
    echo [超时] 等待超时，后端服务未响应
    echo 请先启动后端 API 再运行前端
    echo ========================================
    timeout /t 3 /nobreak >nul
    exit /b 1
)

:: 显示等待进度
set /a mod=%count% %% 5
if %mod% equ 0 echo   等待中... (已等待 %count% 秒 / 60 秒)
goto :wait_loop

:start_gui
echo.
echo 正在启动前端界面...
echo ========================================
echo 前端窗口即将打开，本窗口将自动关闭...
timeout /t 2 /nobreak >nul

:: 使用 pythonw.exe 隐藏命令行，直接启动 GUI
start "" "%~dp0runtime\pythonw.exe" "%~dp0gpt_sovits_final_v2.py"

exit