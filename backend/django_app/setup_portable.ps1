<#
PowerShell helper to prepare this Django project on another Windows machine.

Usage (run from the `django_app` folder):
  .\setup_portable.ps1 -CreateVenv -InstallReqs -ImportSQL

Options:
  -CreateVenv    : create a python venv in `.venv`
  -InstallReqs   : install packages from `requirements.txt` into the venv
  -ImportSQL     : import `cliente/solucionarteBD.sql` into `db.sqlite3` using the included Python script
  -RunServer     : run `python manage.py runserver` after setup
#>

param(
    [switch]$CreateVenv,
    [switch]$InstallReqs,
    [switch]$ImportSQL,
    [switch]$RunServer
)

$ErrorActionPreference = 'Stop'

Write-Host "Running setup_portable.ps1 in $(Get-Location)" -ForegroundColor Cyan

if ($CreateVenv) {
    if (-Not (Test-Path -Path .venv)) {
        python -m venv .venv
        Write-Host "Created venv at .venv"
    } else {
        Write-Host "Venv already exists at .venv"
    }
}

if ($InstallReqs) {
    if (-Not (Test-Path -Path .venv)) { throw "Venv not found. Run with -CreateVenv first." }
    $pip = Join-Path -Path (Join-Path -Path (Get-Location) -ChildPath '.venv/Scripts') -ChildPath 'pip.exe'
    if (-Not (Test-Path $pip)) { throw "pip not found in venv" }
    & $pip install --upgrade pip
    if (Test-Path requirements.txt) {
        & $pip install -r requirements.txt
    } else {
        Write-Host "requirements.txt not found; installing Django only" -ForegroundColor Yellow
        & $pip install Django==5.2.8
    }
}

if ($ImportSQL) {
    $python = if (Test-Path '.venv/Scripts/python.exe') { '.venv/Scripts/python.exe' } else { 'python' }
    $importScript = Join-Path -Path (Get-Location) -ChildPath 'scripts/import_sql.py'
    if (-Not (Test-Path $importScript)) { throw "import_sql.py not found at $importScript" }
    & $python $importScript
}

if ($RunServer) {
    $python = if (Test-Path '.venv/Scripts/python.exe') { '.venv/Scripts/python.exe' } else { 'python' }
    & $python manage.py runserver
}

Write-Host "setup_portable.ps1 complete." -ForegroundColor Green
