# scripts/grace_size_check.ps1
# Checks that GRACE files do not exceed line threshold

param(
    [int]$MaxLines = 500,
    [string]$Root = $PSScriptRoot + "\.."
)

$targets = @(
    "docs\Architecture.xml",
    "docs\Contracts.xml",
    "docs\contracts\*.xml",
    "docs\architecture\*.xml"
)

$warnings = 0

foreach ($pattern in $targets) {
    $fullPattern = Join-Path $Root $pattern
    $files = Get-Item $fullPattern -ErrorAction SilentlyContinue
    if (-not $files) { continue }

    foreach ($f in $files) {
        $lines = (Get-Content $f.FullName -Encoding UTF8).Count
        if ($lines -gt $MaxLines) {
            $rootNormalized = [System.IO.Path]::GetFullPath($Root).TrimEnd('\')
            $fileNormalized = [System.IO.Path]::GetFullPath($f.FullName)
            $relativePath = $fileNormalized
            if ($fileNormalized.StartsWith($rootNormalized, [System.StringComparison]::OrdinalIgnoreCase)) {
                $relativePath = $fileNormalized.Substring($rootNormalized.Length).TrimStart('\')
            }
            Write-Host "WARNING: $relativePath has $lines lines (threshold $MaxLines)" -ForegroundColor Yellow
            Write-Host "  -> Consider splitting into smaller files" -ForegroundColor Yellow
            $warnings++
        } else {
            Write-Host "OK: $($f.Name) - $lines lines" -ForegroundColor Green
        }
    }
}

if ($warnings -eq 0) {
    Write-Host "`nAll GRACE files are within threshold." -ForegroundColor Green
} else {
    Write-Host "`nTotal warnings: $warnings" -ForegroundColor Yellow
    exit 1
}

Pause;