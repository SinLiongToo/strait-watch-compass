@echo off
chcp 65001 > nul
title 國防部共軍動態 - 一鍵更新資料

echo ===================================================
echo   正在從國防部網站抓取最新軍事動態資料...
echo ===================================================
echo.

cd /d "%~dp0"
python mnd_scraper.py 5

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ===================================================
    echo [成功] 最新資料已更新至 records.js / records.json！
    echo 正在自動為您開啟台海動態羅盤網頁...
    echo ===================================================
    start strait-watch-compass.html
) else (
    echo.
    echo [錯誤] 抓取資料時發生錯誤，請檢查網路連線或 Python 環境。
    pause
)
