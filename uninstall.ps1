# DevTrack Uninstaller for Windows
# Removes all DevTrack components, Docker containers, images, and data

param(
    [string]$WorkspacePath = "$env:USERPROFILE\workspace"
)

$ErrorActionPreference = "Stop"

# Configuration
$INSTALL_DIR = "$env:USERPROFILE\.local\bin"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Red
Write-Host "║        DevTrack - Uninstaller (Windows)                  ║" -ForegroundColor Red
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Red
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

function Write-Info {
    param([string]$Message)
    Write-Host "   $Message" -ForegroundColor Blue
}

# Confirmation
Write-Host "WARNING: This will remove:" -ForegroundColor Yellow
Write-Host "  • DevTrack Docker containers and images"
Write-Host "  • All DevTrack data and configuration"
Write-Host "  • DevTrack CLI wrapper from $INSTALL_DIR"
Write-Host "  • Docker volumes (database, config, Ollama models)"
Write-Host ""
Write-Host "This action CANNOT be undone!" -ForegroundColor Red
Write-Host ""
$response = Read-Host "Are you sure you want to uninstall DevTrack? (yes/no)"

if ($response -notmatch '^[Yy][Ee][Ss]$') {
    Write-Host ""
    Write-Host "Uninstallation cancelled."
    exit 0
}

Clear-Host
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Red
Write-Host "║        DevTrack - Uninstaller (Windows)                  ║" -ForegroundColor Red
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Red
Write-Host ""

# Stop and remove containers
Write-Host ""
Write-Host "━━━ Stopping DevTrack Containers ━━━" -ForegroundColor Magenta
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$composeFile = Join-Path $scriptDir "docker-compose.yml"

if (Test-Path $composeFile) {
    Write-Host "🛑 Stopping containers..." -ForegroundColor Blue
    Push-Location $scriptDir
    try {
        docker compose down 2>$null
        Write-Success "Containers stopped and removed"
    } catch {
        Write-Warning "No running containers found or already removed"
    }
    Pop-Location
} else {
    Write-Warning "docker-compose.yml not found, trying manual cleanup"
    
    # Try to stop containers manually
    $containers = @("devtrack-app", "devtrack-ollama")
    foreach ($container in $containers) {
        $exists = docker ps -a --format "{{.Names}}" | Select-String -Pattern "^$container$"
        if ($exists) {
            Write-Host "Stopping $container..." -ForegroundColor Blue
            docker stop $container 2>$null | Out-Null
            docker rm $container 2>$null | Out-Null
            Write-Success "$container removed"
        }
    }
}

# Remove Docker images
Write-Host ""
Write-Host "━━━ Removing DevTrack Images ━━━" -ForegroundColor Magenta
Write-Host ""

Write-Host "🗑️  Removing DevTrack image..." -ForegroundColor Blue
try {
    docker image inspect devtrack:latest 2>$null | Out-Null
    docker rmi devtrack:latest 2>$null | Out-Null
    Write-Success "DevTrack image removed"
} catch {
    Write-Info "DevTrack image not found (already removed)"
}

Write-Host ""
$removeOllama = Read-Host "Remove Ollama image as well? (yes/no)"

if ($removeOllama -match '^[Yy]') {
    Write-Host "🗑️  Removing Ollama image..." -ForegroundColor Blue
    try {
        docker image inspect ollama/ollama:latest 2>$null | Out-Null
        docker rmi ollama/ollama:latest 2>$null | Out-Null
        Write-Success "Ollama image removed"
    } catch {
        Write-Info "Ollama image not found (already removed)"
    }
}

# Remove Docker volumes
Write-Host ""
Write-Host "━━━ Removing DevTrack Data ━━━" -ForegroundColor Magenta
Write-Host ""

Write-Host "WARNING: This will delete all DevTrack data, including:" -ForegroundColor Red
Write-Host "  • Database and task history"
Write-Host "  • Configuration files"
Write-Host "  • Ollama models (can be large)"
Write-Host ""
$removeData = Read-Host "Delete all data volumes? (yes/no)"

if ($removeData -match '^[Yy]') {
    $volumes = @("devtrack-data", "devtrack-config", "ollama-data")
    foreach ($volume in $volumes) {
        try {
            docker volume inspect $volume 2>$null | Out-Null
            Write-Host "Removing volume $volume..." -ForegroundColor Blue
            docker volume rm $volume 2>$null | Out-Null
            Write-Success "$volume removed"
        } catch {
            # Volume doesn't exist, skip
        }
    }
} else {
    Write-Info "Skipping data volume removal (data preserved)"
}

# Remove wrapper scripts
Write-Host ""
Write-Host "━━━ Removing CLI Wrapper ━━━" -ForegroundColor Magenta
Write-Host ""

$batWrapper = Join-Path $INSTALL_DIR "devtrack.bat"
$ps1Wrapper = Join-Path $INSTALL_DIR "devtrack-wrapper.ps1"

$removed = $false
if (Test-Path $batWrapper) {
    Write-Host "🗑️  Removing devtrack.bat..." -ForegroundColor Blue
    Remove-Item $batWrapper -Force
    $removed = $true
}

if (Test-Path $ps1Wrapper) {
    Write-Host "🗑️  Removing devtrack-wrapper.ps1..." -ForegroundColor Blue
    Remove-Item $ps1Wrapper -Force
    $removed = $true
}

if ($removed) {
    Write-Success "CLI wrapper removed from $INSTALL_DIR"
} else {
    Write-Info "CLI wrapper not found (already removed)"
}

# Remove network
Write-Host ""
Write-Host "━━━ Cleaning Up Network ━━━" -ForegroundColor Magenta
Write-Host ""

try {
    docker network inspect devtrack-network 2>$null | Out-Null
    Write-Host "Removing network..." -ForegroundColor Blue
    docker network rm devtrack-network 2>$null | Out-Null
    Write-Success "Network removed"
} catch {
    Write-Info "Network not found (already removed)"
}

# Optional: Remove workspace
Write-Host ""
Write-Host "━━━ Workspace Directory ━━━" -ForegroundColor Magenta
Write-Host ""

if (Test-Path $WorkspacePath) {
    Write-Host "Workspace directory: $WorkspacePath" -ForegroundColor Yellow
    Write-Host ""
    $removeWorkspace = Read-Host "Remove workspace directory? (yes/no)"
    
    if ($removeWorkspace -match '^[Yy]') {
        Write-Host "🗑️  Removing workspace..." -ForegroundColor Blue
        Remove-Item -Recurse -Force $WorkspacePath
        Write-Success "Workspace removed"
    } else {
        Write-Info "Workspace preserved at $WorkspacePath"
    }
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║            UNINSTALLATION COMPLETE!                      ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "DevTrack has been removed from your system." -ForegroundColor Green
Write-Host ""
Write-Host "Cleanup summary:" -ForegroundColor Blue
Write-Host "  • Docker containers stopped and removed"
Write-Host "  • Docker images removed"
Write-Host "  • CLI wrapper removed"
Write-Host "  • Network cleaned up"
Write-Host ""
Write-Host "Note: Docker itself is still installed and running." -ForegroundColor Yellow
Write-Host ""
Write-Host "To reinstall DevTrack, run:"
Write-Host "  .\install_dependencies.ps1" -ForegroundColor Cyan
Write-Host ""
