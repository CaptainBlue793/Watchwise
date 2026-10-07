param([int]$Port = 8503)
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    & conda run --no-capture-output -n starGPU python -m streamlit run Watchwise.py --server.port $Port
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
