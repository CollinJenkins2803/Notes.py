@echo off
cd C:\PATH\TO\Notes.py

:: Start the backend process
start cmd /k "python app.py"

:: Open the frontend in the default browser
start "" http://127.0.0.1:5000

pause