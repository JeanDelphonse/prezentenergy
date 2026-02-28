Add-Type -Assembly 'System.IO.Compression.FileSystem'

$root = $PSScriptRoot
$zipPath = Join-Path $root 'prezentenergy-deploy.zip'

$excludeDirs = @('.venv', 'venv', 'env', '__pycache__', 'instance', '.git', 'images')
$excludeFiles = @('.env', 'prezentenergy-deploy.zip', 'make_zip.ps1', 'DEPLOY.md')
$excludeExts = @('.pyc', '.pyo', '.pyd', '.db', '.sqlite3')

if (Test-Path $zipPath) { Remove-Item $zipPath }

$archive = [System.IO.Compression.ZipFile]::Open($zipPath, 'Create')

$allFiles = Get-ChildItem -Path $root -Recurse -File

foreach ($f in $allFiles) {
    $rel = $f.FullName.Substring($root.Length + 1)

    # Skip excluded directories (any path segment matches)
    $skip = $false
    foreach ($d in $excludeDirs) {
        if ($rel -match "(^|\\)$([regex]::Escape($d))(\\|$)") { $skip = $true; break }
    }
    if ($skip) { continue }

    # Skip excluded filenames
    if ($excludeFiles -contains $f.Name) { continue }

    # Skip excluded extensions
    if ($excludeExts -contains $f.Extension) { continue }

    # Skip static/video subtree
    if ($rel -match "(^|\\)static\\video(\\|$)") { continue }

    $entry = $rel.Replace('\', '/')
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $f.FullName, $entry) | Out-Null
}

$archive.Dispose()

$size = [math]::Round((Get-Item $zipPath).Length / 1KB)
Write-Host "Created: prezentenergy-deploy.zip ($size KB)"
