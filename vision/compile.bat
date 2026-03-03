@echo off
%windir%\Microsoft.NET\Framework\v2.0.50727\csc.exe /target:winexe /out:JoblistLeegmaken.exe JoblistLeegmaken.cs
if %errorlevel%==0 (
    echo Compiled: JoblistLeegmaken.exe
) else (
    echo Fout bij compileren.
)
pause
