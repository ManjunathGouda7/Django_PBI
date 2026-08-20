# scripts/manage.ps1
# Developer CLI and Workflow Automation for APEX BI Studio
param (
    [Parameter(Position=0, Mandatory=$true)]
    [string]$Command,
    [Parameter(Position=1)]
    [string]$Arg
)

$PythonExe = Join-Path $PSScriptRoot "..\mgenv\Scripts\python.exe"
$BiDir = Join-Path $PSScriptRoot "..\BI"

switch ($Command.ToLower()) {
    "run" {
        Write-Host "[STARTING] Django Development Server on http://127.0.0.1:8000..." -ForegroundColor Cyan
        & $PythonExe (Join-Path $BiDir "manage.py") runserver 127.0.0.1:8000
    }
    "test" {
        Write-Host "[RUNNING] Automated Unit & Integration Test Suite..." -ForegroundColor Cyan
        & $PythonExe (Join-Path $BiDir "manage.py") test analytics --verbosity=2
    }
    "check" {
        Write-Host "[CHECKING] Django System Sanity & Health..." -ForegroundColor Cyan
        & $PythonExe (Join-Path $BiDir "manage.py") check
    }
    "migrate" {
        Write-Host "[MIGRATING] Applying Database Migrations..." -ForegroundColor Cyan
        & $PythonExe (Join-Path $BiDir "manage.py") migrate
    }
    "makemigrations" {
        Write-Host "[MIGRATIONS] Generating Django Migrations..." -ForegroundColor Cyan
        & $PythonExe (Join-Path $BiDir "manage.py") makemigrations analytics
    }
    "build_exe" {
        Write-Host "[BUILDING] Standalone Windows Binary (ApexBIStudio.exe)..." -ForegroundColor Cyan
        Set-Location (Join-Path $PSScriptRoot "..")
        .\Build_EXE.bat
    }
    "health" {
        Write-Host "[PROBING] Checking /health/ endpoint..." -ForegroundColor Cyan
        try {
            $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health/" -Method Get
            $response | ConvertTo-Json -Depth 4
        } catch {
            Write-Host "[OFFLINE] Server is not reachable at http://127.0.0.1:8000" -ForegroundColor Red
        }
    }
    default {
        Write-Host "Usage: .\manage.ps1 [run|test|check|migrate|makemigrations|build_exe|health]" -ForegroundColor Yellow
    }
}
