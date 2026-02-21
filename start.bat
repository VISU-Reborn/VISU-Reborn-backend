@echo off
echo 🚀 Starting VISU...
echo.

:: Start frontend server in a new window
start "VISU Frontend" cmd /k "cd /d %~dp0 && uv run python frontend/server.py"

:: Wait a moment for the frontend to boot
timeout /t 3 /nobreak > nul

:: Start agent in a new window
start "VISU Agent" cmd /k "cd /d %~dp0 && uv run python main.py console"

echo ✅ Both windows launched!
echo    - Frontend: http://localhost:8000
echo    - Agent: running in console mode
