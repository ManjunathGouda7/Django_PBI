# scripts/restore_db.ps1
# 1-Click Database Restore Script for APEX BI Studio
param (
    [Parameter(Mandatory=$true)]
    [string]$BackupFile
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   APEX BI STUDIO — DATABASE RESTORE TOOL " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

if (!(Test-Path $BackupFile)) {
    Write-Host "[ERROR] Specified backup file not found: $BackupFile" -ForegroundColor Red
    exit 1
}

if ($BackupFile.EndsWith(".sqlite3")) {
    $TargetDB = Join-Path $PSScriptRoot "..\BI\db.sqlite3"
    Copy-Item $BackupFile -Destination $TargetDB -Force
    Write-Host "[SUCCESS] Successfully restored SQLite database from: $BackupFile" -ForegroundColor Green
}
elseif ($BackupFile.EndsWith(".sql")) {
    $PgContainer = docker ps --filter "name=powerbi_postgres" --format "{{.Names}}" 2>$null
    if ($PgContainer) {
        Get-Content $BackupFile | docker exec -i powerbi_postgres psql -U powerbi_user -d powerbi_db
        Write-Host "[SUCCESS] Successfully restored PostgreSQL database from: $BackupFile" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] PostgreSQL container 'powerbi_postgres' is not running." -ForegroundColor Red
    }
}
