# Ejecutar backend (Django) en localhost.
# Desde la raíz del proyecto: .\run_local.ps1
# Requisito: pip install -r backend\requirements.txt (o requirements-local.txt si falla mysqlclient en Windows)
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root\backend
$env:DJANGO_SETTINGS_MODULE = "django_app.settings"
python manage.py runserver 127.0.0.1:8000
