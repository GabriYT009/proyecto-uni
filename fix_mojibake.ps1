$files = Get-ChildItem "frontend/templates/core/*.html"
$patterns = @("Ã", "Â", "ðŸ", "â€", "ï¸")
$correctedCount = 0
$correctedFiles = @()

foreach ($file in $files) {
    $content = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
    
    $initialCount = 0
    foreach ($p in $patterns) {
        $initialCount += ([regex]::Matches($content, [regex]::Escape($p))).Count
    }

    if ($initialCount -gt 0) {
        try {
            $bytes = [System.Text.Encoding]::GetEncoding(1252).GetBytes($content)
            $fixed = [System.Text.Encoding]::UTF8.GetString($bytes)
            
            $finalCount = 0
            foreach ($p in $patterns) {
                $finalCount += ([regex]::Matches($fixed, [regex]::Escape($p))).Count
            }
            
            if ($finalCount -lt $initialCount) {
                [System.IO.File]::WriteAllText($file.FullName, $fixed, (New-Object System.Text.UTF8Encoding($false)))
                $correctedCount++
                $correctedFiles += $file.FullName
            }
        } catch {
            Write-Warning "Error procesando $($file.Name): $($_.Exception.Message)"
        }
    }
}

Write-Host "Archivos corregidos: $correctedCount"
foreach ($f in $correctedFiles) { Write-Host $f }

Write-Host "`nVerificación final:"
$totalRemaining = 0
foreach ($file in Get-ChildItem "frontend/templates/core/*.html") {
    $content = Get-Content $file.FullName -Raw -Encoding UTF8
    foreach ($p in $patterns) {
        $totalRemaining += ([regex]::Matches($content, [regex]::Escape($p))).Count
    }
}
Write-Host "Patrones dañados restantes: $totalRemaining"
