$ErrorActionPreference = 'Stop'
$projectDirectory = $PSScriptRoot
$virtualPython = Join-Path $projectDirectory '.venv\Scripts\python.exe'
Push-Location -LiteralPath $projectDirectory
try {
    if (Test-Path -LiteralPath $virtualPython) {
        & $virtualPython app.py
    } else {
        python app.py
    }
} finally {
    Pop-Location
}
