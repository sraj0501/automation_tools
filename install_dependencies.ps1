# DevTrack Docker Installer for Windows
# Builds Docker images and deploys DevTrack as a containerized application

param(
    [string]$WorkspacePath = "$env:USERPROFILE\workspace"
)

$ErrorActionPreference = "Stop"

# Configuration
$INSTALL_DIR = "$env:USERPROFILE\.local\bin"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        DevTrack - Docker Installer (Windows)             ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

function Write-Success {
    param([string]$Message)
    Write-Host "   ✓ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "   ✗ $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "   ⚠️  $Message" -ForegroundColor Yellow
}

# Check Docker
Write-Host "🔍 Checking Docker installation..." -ForegroundColor Blue
try {
    docker info | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Docker not running" }
    Write-Success "Docker is installed and running"
} catch {
    Write-Error "Docker is not running."
    Write-Host ""
    Write-Host "   Please install and start Docker Desktop from:"
    Write-Host "   https://www.docker.com/products/docker-desktop" -ForegroundColor Cyan
    exit 1
}

# Check Docker Compose
Write-Host ""
Write-Host "🔍 Checking Docker Compose..." -ForegroundColor Blue
try {
    docker compose version | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose not found" }
    Write-Success "Docker Compose is available"
} catch {
    Write-Error "Docker Compose is not installed."
    Write-Host ""
    Write-Host "   Docker Compose is usually included with Docker Desktop."
    exit 1
}

# Check/create installation directory
Write-Host ""
Write-Host "🔍 Checking installation directory..." -ForegroundColor Blue
if (-not (Test-Path $INSTALL_DIR)) {
    Write-Host "   Creating $INSTALL_DIR" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null
}
Write-Success "Installation directory ready: $INSTALL_DIR"

# Check PATH
if ($env:PATH -notlike "*$INSTALL_DIR*") {
    Write-Warning "$INSTALL_DIR is not in your PATH"
    Write-Host ""
    Write-Host "   Add it to your PATH with:"
    Write-Host "   [System.Environment]::SetEnvironmentVariable('PATH', `$env:PATH + ';$INSTALL_DIR', 'User')" -ForegroundColor Yellow
    Write-Host ""
}

# Check/create workspace
Write-Host ""
Write-Host "🔍 Checking workspace directory..." -ForegroundColor Blue
if (-not (Test-Path $WorkspacePath)) {
    Write-Host "   Creating workspace at $WorkspacePath" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $WorkspacePath -Force | Out-Null
}
Write-Success "Workspace ready: $WorkspacePath"

# Build Docker images
Write-Host ""
Write-Host "━━━ Building DevTrack Docker Images ━━━" -ForegroundColor Magenta
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $scriptDir

Write-Host "📦 Building DevTrack image..." -ForegroundColor Blue
Write-Host "   This may take several minutes on first run..." -ForegroundColor Yellow

docker build -t devtrack:latest .
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to build DevTrack image"
    exit 1
}
Write-Success "DevTrack image built successfully"

# Pull Ollama
Write-Host ""
Write-Host "📦 Pulling Ollama image..." -ForegroundColor Blue
docker pull ollama/ollama:latest
if ($LASTEXITCODE -eq 0) {
    Write-Success "Ollama image pulled successfully"
} else {
    Write-Warning "Failed to pull Ollama image"
}

# Deploy wrapper
Write-Host ""
Write-Host "━━━ Deploying DevTrack Wrapper ━━━" -ForegroundColor Magenta
Write-Host ""

$batSource = Join-Path $scriptDir "devtrack-wrapper.bat"
$ps1Source = Join-Path $scriptDir "devtrack-wrapper.ps1"
$batDest = Join-Path $INSTALL_DIR "devtrack.bat"
$ps1Dest = Join-Path $INSTALL_DIR "devtrack-wrapper.ps1"

if (Test-Path $batSource) {
    Copy-Item $batSource $batDest -Force
    Copy-Item $ps1Source $ps1Dest -Force
    Write-Success "devtrack.bat installed to $INSTALL_DIR"
} else {
    Write-Error "Wrapper scripts not found"
    exit 1
}

# Start services
Write-Host ""
Write-Host "━━━ Starting DevTrack Services ━━━" -ForegroundColor Magenta
Write-Host ""

$env:WORKSPACE_PATH = $WorkspacePath
docker compose up -d
if ($LASTEXITCODE -eq 0) {
    Write-Success "DevTrack services started"
} else {
    Write-Error "Failed to start services"
    exit 1
}

Start-Sleep -Seconds 3

# Check services
$containers = docker ps --format "{{.Names}}"
if ($containers -contains "devtrack-ollama") {
    Write-Success "Ollama service is running"
}
if ($containers -contains "devtrack-app") {
    Write-Success "DevTrack service is running"
}

# Ollama models
Write-Host ""
Write-Host "━━━ Ollama Model Setup ━━━" -ForegroundColor Magenta
Write-Host ""

$response = Read-Host "Would you like to download an Ollama model now? (yes/no)"
if ($response -match '^[Yy]') {
    Write-Host ""
    Write-Host "Which model would you like to download?" -ForegroundColor Cyan
    Write-Host "   1) llama3.1 (recommended, ~4GB)"
    Write-Host "   2) llama2 (~4GB)"
    Write-Host "   3) mistral (~4GB)"
    Write-Host "   4) phi3 (smaller, ~2GB)"
    $choice = Read-Host "Enter choice (1-4)"
    
    $modelName = switch ($choice) {
        "1" { "llama3.1" }
        "2" { "llama2" }
        "3" { "mistral" }
        "4" { "phi3" }
        default { "" }
    }
    
    if ($modelName) {
        Write-Host ""
        Write-Host "📥 Downloading $modelName model..." -ForegroundColor Blue
        Write-Host "   This may take several minutes..." -ForegroundColor Yellow
        docker exec devtrack-ollama ollama pull $modelName
        if ($LASTEXITCODE -eq 0) {
            Write-Success "$modelName model downloaded"
        }
    }
}

Pop-Location

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║              INSTALLATION COMPLETE!                      ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "🎉 DevTrack installation finished successfully!" -ForegroundColor Green
Write-Host ""

Write-Host "Installation Summary:" -ForegroundColor Magenta
Write-Host "  ✓ DevTrack CLI → $INSTALL_DIR\devtrack.bat" -ForegroundColor Green
Write-Host "  ✓ Workspace → $WorkspacePath" -ForegroundColor Green
Write-Host "  ✓ Running in Docker containers" -ForegroundColor Green
Write-Host ""

Write-Host "Quick Start:" -ForegroundColor Magenta
Write-Host "  devtrack                 - Launch interactive TUI" -ForegroundColor Yellow
Write-Host "  devtrack --help          - Show all commands" -ForegroundColor Yellow
Write-Host "  devtrack learning-status - Check AI learning status" -ForegroundColor Yellow
Write-Host ""

if ($env:PATH -notlike "*$INSTALL_DIR*") {
    Write-Host "⚠️  IMPORTANT: Add $INSTALL_DIR to your PATH" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Run in PowerShell (as Administrator):" -ForegroundColor Cyan
    Write-Host "   [System.Environment]::SetEnvironmentVariable('PATH', `$env:PATH + ';$INSTALL_DIR', 'User')" -ForegroundColor Green
    Write-Host ""
}

Write-Host "Ready to use DevTrack!" -ForegroundColor Green
Write-Host ""
