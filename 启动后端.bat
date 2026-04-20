@echo off
chcp 65001 >nul
title GPT-SoVITS 后端 API 服务

cd /d "%~dp0"

:: ==========================================
:: 清理函数：退出时释放端口
:: ==========================================
goto :main

:cleanup
echo.
echo 正在释放端口 9880...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":9880.*LISTENING"') do (
    taskkill /F /PID %%a 2>nul
)
echo 端口已释放
exit /b

:main
:: 检查端口是否被占用
netstat -ano | findstr ":9880" | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
    echo [警告] 端口 9880 已被占用
    choice /c yn /n /m "是否结束占用进程？(Y/N): "
    if errorlevel 2 exit /b 1
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":9880.*LISTENING"') do taskkill /F /PID %%a 2>nul
    timeout /t 2 /nobreak >nul
)

echo ========================================
echo      GPT-SoVITS 后端 API 服务
echo ========================================
echo.
echo 正在启动后端服务...
echo 地址: http://127.0.0.1:9880
echo.
echo ========================================
echo 提示：
echo   - 按 Ctrl+C 正常退出
echo   - 直接关闭窗口也会自动释放端口
echo ========================================
echo.

:: 启动 Python，并用 call 确保返回后执行清理
call .\runtime\python.exe api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml

:: 无论怎么退出，都会执行清理
call :cleanup