@echo off
chcp 65001 >nul
title 雲頂天宮 · 正在启动...

echo.
echo  ======================================================
echo    雲頂天宮 · Telegram 智能矩阵与商机中枢
echo  ======================================================
echo.

:: 检查 Python 环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 正在使用系统 Python 启动...
)

echo [*] 正在启动后台服务与控制台窗口，请稍候...
start "" python windows_desktop_app.py

exit
