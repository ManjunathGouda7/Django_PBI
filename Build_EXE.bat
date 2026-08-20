@echo off
title APEX BI Studio — Windows EXE Executable Generator
echo ================================================================================
echo             APEX BI STUDIO — WINDOWS EXE COMPILATION SCRIPT
echo ================================================================================
echo.

cd /d "%~dp0\BI"

echo [1/3] Setting environment variables...
set DJANGO_SETTINGS_MODULE=BI.settings

echo [2/3] Compiling standalone Windows Executable with PyInstaller...
..\mgenv\Scripts\pyinstaller.exe ^
  --noconfirm ^
  --onedir ^
  --name="ApexBIStudio" ^
  --add-data="analytics/templates;analytics/templates" ^
  --add-data="analytics/static;analytics/static" ^
  --hidden-import="analytics" ^
  --hidden-import="rest_framework" ^
  --hidden-import="rest_framework_simplejwt" ^
  --hidden-import="drf_yasg" ^
  --hidden-import="corsheaders" ^
  --hidden-import="django_filters" ^
  --hidden-import="pandas" ^
  --hidden-import="openpyxl" ^
  --hidden-import="waitress" ^
  desktop_launcher.py

echo.
echo ================================================================================
echo BUILD COMPLETE!
echo Executable Location: %~dp0BI\dist\ApexBIStudio\ApexBIStudio.exe
echo ================================================================================
pause
