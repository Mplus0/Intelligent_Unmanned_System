@echo off
cd /d "%~dp0"
"D:\Anaconda\python.exe" -m conda run --no-capture-output -n Unmanned_systems python mnist_experiment.py
if errorlevel 1 exit /b 1
"D:\Anaconda\python.exe" -m conda run --no-capture-output -n Unmanned_systems python verify_results.py
if errorlevel 1 exit /b 1
"D:\Anaconda\python.exe" -m conda run --no-capture-output -n Unmanned_systems python predict.py --index 0
pause
