$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error "Python nao encontrado. Instale o Python 3.8+ e adicione ao PATH."
    exit 1
}

$venv = Join-Path $ProjectRoot ".venv"
if (-not (Test-Path $venv)) {
    Write-Host "[VENV] Criando ambiente virtual..."
    python -m venv $venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Falha ao criar ambiente virtual."
        exit 1
    }
}

& "$venv\Scripts\Activate.ps1"

if (Test-Path (Join-Path $ProjectRoot "requirements.txt")) {
    Write-Host "[DEPENDENCIAS] Instalando pacotes..."
    pip install -r "$ProjectRoot\requirements.txt" --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Falha ao instalar dependencias."
        exit 1
    }
}

Set-Location -LiteralPath $ProjectRoot
python run.py @args
