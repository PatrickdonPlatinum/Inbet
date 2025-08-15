@echo off
echo [INFO] Killing common processes locking Temp...
taskkill /F /IM explorer.exe >nul 2>&1
taskkill /F /IM icue.exe >nul 2>&1
taskkill /F /IM chrome.exe >nul 2>&1
taskkill /F /IM msedge.exe >nul 2>&1
taskkill /F /IM firefox.exe >nul 2>&1

echo [INFO] Deleting Temp folder (forcing)...
rmdir /s /q "C:\Users\petar\AppData\Local\Temp"

echo [INFO] Recreating Temp folder...
mkdir "C:\Users\petar\AppData\Local\Temp"

echo [INFO] Restarting Explorer...
start explorer.exe

echo [DONE] Temp folder fully cleared.
pause
