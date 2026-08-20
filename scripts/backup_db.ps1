# scripts/backup_db.ps1
# 1-Click Database Backup Script for APEX BI Studio
param (
    [string]$BackupDir = "..\backups"
)

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$TargetDir = Join-Path $PSScriptRoot $BackupDir
if (!(Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   APEX BI STUDIO — DATABASE BACKUP TOOL  " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. SQLite Database Backup
$SqliteDB = Join-Path $PSScriptRoot "..\BI\db.sqlite3"
if (Test-Path $SqliteDB) {
    $BackupFile = Join-Path $TargetDir "db_sqlite_$Timestamp.sqlite3"
    Copy-Item $SqliteDB -Destination $BackupFile
    Write-Host "[SUCCESS] Backed up SQLite database to: $BackupFile" -ForegroundColor Green
}

# 2. PostgreSQL Container Backup (if docker is active)
$PgContainer = docker ps --filter "name=powerbi_postgres" --format "{{.Names}}" 2>$null
if ($PgContainer) {
    $PgBackupFile = Join-Path $TargetDir "pg_dump_$Timestamp.sql"
    docker exec powerbi_postgres pg_dump -U powerbi_user powerbi_db > $PgBackupFile
    Write-Host "[SUCCESS] Backed up PostgreSQL container database to: $PgBackupFile" -ForegroundColor Green
}

Write-Host "Database backup completed successfully!" -ForegroundColor Green
