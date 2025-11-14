# DevTrack Docker Wrapper for Windows
# Makes DevTrack container callable like a native CLI application

# Configuration
$DOCKER_IMAGE = "devtrack:latest"
$CONTAINER_NAME = "devtrack-app"
$WORKSPACE_PATH = if ($env:WORKSPACE_PATH) { $env:WORKSPACE_PATH } else { "$env:USERPROFILE\workspace" }

# Check if Docker is running
try {
    docker info | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker not running"
    }
} catch {
    Write-Error "Error: Docker is not running. Please start Docker Desktop."
    exit 1
}

# Check if docker-compose services are running
$runningContainers = docker ps --format "{{.Names}}"
if ($runningContainers -notcontains $CONTAINER_NAME) {
    # Check if image exists
    try {
        docker image inspect $DOCKER_IMAGE | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Image not found"
        }
    } catch {
        Write-Error "Error: DevTrack image not found. Please run the installer first."
        exit 1
    }
    
    # Start services if they're not running
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $repoDir = Split-Path -Parent $scriptDir
    $composeFile = Join-Path $repoDir "docker-compose.yml"
    
    if (Test-Path $composeFile) {
        Push-Location $repoDir
        docker compose up -d | Out-Null
        Pop-Location
    } else {
        Write-Error "Error: docker-compose.yml not found. DevTrack may not be properly installed."
        exit 1
    }
}

# Get current directory relative to workspace
$currentDir = Get-Location | Select-Object -ExpandProperty Path
$workspacePathNormalized = $WORKSPACE_PATH.Replace('\', '/')

if ($currentDir.StartsWith($WORKSPACE_PATH)) {
    # Inside workspace, maintain relative path
    $relPath = $currentDir.Substring($WORKSPACE_PATH.Length).Replace('\', '/')
    $workDir = "/workspace$relPath"
} else {
    # Not inside workspace, use workspace root
    $workDir = "/workspace"
}

# Run devtrack command in container
$env:TERM = if ($env:TERM) { $env:TERM } else { "xterm-256color" }
docker exec -it `
    -w $workDir `
    -e "TERM=$env:TERM" `
    $CONTAINER_NAME `
    devtrack-cli $args

exit $LASTEXITCODE
