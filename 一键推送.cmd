@echo off
chcp 65001 >nul
cd /d "%~dp0"
title TD2 掉落站 - 推送到 GitHub
echo ==========================================
echo  推送 全境封锁2 掉落站 到 GitHub
echo ==========================================
echo.
echo 仓库: https://github.com/pwm385/td2
echo 当前目录: %CD%
echo.
echo 开始推送... 弹出浏览器就点 Authorize 授权
echo.
git push -u origin main
set RC=%ERRORLEVEL%
echo.
if not "%RC%"=="0" (
  echo ---------- 失败，错误码 %RC% ----------
  echo 请把上面这几行截图发给 AI
) else (
  echo ---------- 成功！回去跟 AI 说一声 ----------
)
echo.
pause
