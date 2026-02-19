
@echo off

set variable_dir=%1
REM echo variable_dir : %variable_dir%

if "%variable_dir%"=="" goto do_regasm

rem the first argument is the directory that contains the dll's
set variable_dir=%1\

REM echo variable_dir : %variable_dir%


:do_regasm

echo =====================================================================
echo .....................................................................
echo Regasm QlmLicenseLib ...

c:\Windows\Microsoft.NET\Framework\v2.0.50727\RegAsm.exe /tlb %variable_dir%QlmLicenseLib.dll
c:\Windows\Microsoft.NET\Framework\v2.0.50727\RegAsm.exe /codebase %variable_dir%QlmLicenseLib.dll

c:\Windows\Microsoft.NET\Framework\v4.0.30319\RegAsm.exe /tlb %variable_dir%QlmLicenseLib.dll
c:\Windows\Microsoft.NET\Framework\v4.0.30319\RegAsm.exe /codebase %variable_dir%QlmLicenseLib.dll

c:\Windows\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe /tlb %variable_dir%QlmLicenseLib.dll
c:\Windows\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe /codebase %variable_dir%QlmLicenseLib.dll



echo =====================================================================

echo .....................................................................
echo Regasm StimulSoftLib ...

REM StimulSoft-2016.2 must have minimum .Net Framework 4.0 !!
REM c:\Windows\Microsoft.NET\Framework\v2.0.50727\RegAsm.exe /tlb %variable_dir%StimulSoft\StimulSoftLib.dll
REM c:\Windows\Microsoft.NET\Framework\v2.0.50727\RegAsm.exe /codebase %variable_dir%StimulSoft\StimulSoftLib.dll

c:\Windows\Microsoft.NET\Framework\v4.0.30319\RegAsm.exe /tlb %variable_dir%StimulSoft\StimulSoftLib.dll
c:\Windows\Microsoft.NET\Framework\v4.0.30319\RegAsm.exe /codebase %variable_dir%StimulSoft\StimulSoftLib.dll

c:\Windows\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe /tlb %variable_dir%StimulSoft\StimulSoftLib.dll
c:\Windows\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe /codebase %variable_dir%StimulSoft\StimulSoftLib.dll


REM pause ""