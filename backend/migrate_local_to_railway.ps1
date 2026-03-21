<#
Script para migrar datos de la base local (SQLite) a la base remota en Railway (Postgres/MySQL)
Uso:
  cd c:\Users\eduar\Desktop\pantalla\backend
  .\migrate_local_to_railway.ps1 -RailwayDatabaseUrl "postgres://user:pass@host:port/dbname"
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$RailwayDatabaseUrl,
    [string]$DataFile = "..\dumpdata_railway.json"
)

$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $projectPath

Write-Host "[1/4] Generando volcado JSON desde la base local (SQLite)..." -ForegroundColor Cyan
python manage.py dumpdata --natural-foreign --natural-primary --indent 2 --exclude auth.permission --exclude contenttypes --output $DataFile
if ($LASTEXITCODE -ne 0) { Write-Error "Error al generar dumpdata"; Pop-Location; exit 1 }

Write-Host "[1.1/4] Convertir fixture a UTF-8 para loaddata..." -ForegroundColor Cyan
python -c "from pathlib import Path; p=Path(r'$DataFile'); text=p.read_text(encoding='cp1252'); p.write_text(text, encoding='utf-8')"
if ($LASTEXITCODE -ne 0) { Write-Error 'Error al convertir fixture a UTF-8'; Pop-Location; exit 1 }

Write-Host "[2/4] Configurando DATABASE_URL con Railway..." -ForegroundColor Cyan
$env:DATABASE_URL = $RailwayDatabaseUrl

Write-Host "[2.1/4] Verificando conteo actual en Railway (antes de cargar)..." -ForegroundColor Cyan
python manage.py shell -c "from django_app.core.models import Producto, Cliente, Categoria; print('Railway antes -> Productos:', Producto.objects.count(), 'Clientes:', Cliente.objects.count(), 'Categorias:', Categoria.objects.count())"

Write-Host "[3/4] Aplicando migraciones en la base Railway..." -ForegroundColor Cyan
python manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { Write-Error "Error al ejecutar migrate en Railway"; Pop-Location; exit 1 }

Write-Host "[4/4] Cargando datos en Railway desde $DataFile..." -ForegroundColor Cyan
python manage.py loaddata $DataFile
if ($LASTEXITCODE -ne 0) { Write-Error "Error al cargar datos con loaddata"; Pop-Location; exit 1 }

Write-Host "[4.1/4] Verificando conteo en Railway (después de cargar)..." -ForegroundColor Cyan
python manage.py shell -c "from django_app.core.models import Producto, Cliente, Categoria; print('Railway después -> Productos:', Producto.objects.count(), 'Clientes:', Cliente.objects.count(), 'Categorias:', Categoria.objects.count())"

Write-Host "¡Migración finalizada! Revisa Railway y prueba la app." -ForegroundColor Green
Pop-Location
