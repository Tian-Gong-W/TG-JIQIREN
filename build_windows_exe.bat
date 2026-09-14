@echo off
chcp 65001 >nul
title 雲頂天宮 打包工具

echo.
echo  ======================================================
echo    雲頂天宮 · Telegram 智能矩阵与商机中枢 · 打包脚本
echo  ======================================================
echo.

:: ==============================
:: 1. 检查 Python
:: ==============================
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python！
    echo 请先下载安装 Python 3.11+ 并勾选 "Add to PATH"
    echo 下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [✓] 检测到 %%i

:: ==============================
:: 2. 安装打包依赖
:: ==============================
echo.
echo [1/3] 安装打包所需工具 (pywebview, pyinstaller)...
pip install pywebview pyinstaller --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo [错误] 安装依赖失败，请检查网络或手动运行：
    echo pip install pywebview pyinstaller
    pause
    exit /b 1
)
echo [✓] 打包工具已就绪

:: ==============================
:: 3. 安装项目后端依赖
:: ==============================
echo.
echo [2/3] 安装 TG 后端依赖...
pip install -r tg_suite\requirements.txt --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo [警告] 部分依赖安装失败，可能影响功能
)
echo [✓] 后端依赖已就绪

:: ==============================
:: 4. PyInstaller 打包
:: ==============================
echo.
echo [3/3] 正在编译 雲頂天宮.exe (约 1~2 分钟，请耐心等待)...

:: 清理旧的打包产物
if exist dist\雲頂天宮 rmdir /s /q dist\雲頂天宮
if exist build rmdir /s /q build

pyinstaller ^
  --noconfirm ^
  --onedir ^
  --windowed ^
  --name "雲頂天宮" ^
  --add-data "tg_suite;tg_suite" ^
  --add-data "使用手册.html;." ^
  --hidden-import "webview" ^
  --hidden-import "clr" ^
  --collect-all "webview" ^
  windows_desktop_app.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 打包失败！请截图上方报错信息发给技术支持。
    pause
    exit /b 1
)

:: ==============================
:: 5. 整理产物目录
:: ==============================
echo.
echo [*] 整理发布目录...
xcopy /e /i /q tg_suite dist\雲頂天宮\tg_suite >nul
xcopy /q 使用手册.html dist\雲頂天宮\ >nul

echo.
echo  ======================================================
echo    ✅ 打包成功！
echo  ======================================================
echo.
echo  📂 程序位置: dist\雲頂天宮\雲頂天宮.exe
echo.
echo  ▶  使用方法:
echo     1. 将 dist\雲頂天宮\ 整个文件夹复制/压缩后发给用户
echo     2. 双击 雲頂天宮.exe 即可直接打开控制台！
echo.
echo  📖 使用手册: dist\雲頂天宮\使用手册.html
echo.
pause

