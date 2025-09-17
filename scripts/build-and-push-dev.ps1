<#
Build and optionally push a dev Docker image for this repo.

Usage (PowerShell):
  $env:DOCKER_REGISTRY = 'docker.io' ; $env:DOCKER_USERNAME='user' ; $env:DOCKER_PASSWORD='token' ; ./scripts/build-and-push-dev.ps1

Environment variables:
  DOCKER_REGISTRY - optional registry (default: docker.io)
  IMAGE_NAME - optional full image name (default: hrbzhq/autowork2025:dev)
  DOCKER_USERNAME / DOCKER_PASSWORD - optional credentials to login before push
  DO_PUSH - set to '1' to push the image after building (default: 0)
#>

param()

$ErrorActionPreference = 'Stop'

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker CLI not found in PATH. Please install Docker Desktop or Docker Engine and try again."
    exit 2
}

$registry = if ($env:DOCKER_REGISTRY) { $env:DOCKER_REGISTRY } else { 'docker.io' }
$imageName = if ($env:IMAGE_NAME) { $env:IMAGE_NAME } else { 'hrbzhq/autowork2025:dev' }
$doPush = if ($env:DO_PUSH -and $env:DO_PUSH -eq '1') { $true } else { $false }

Write-Host "Building Docker image: $imageName (registry: $registry)"

# Build image
docker build -t $imageName .

if ($doPush) {
    if ($env:DOCKER_USERNAME -and $env:DOCKER_PASSWORD) {
        Write-Host "Logging in to $registry"
        docker login $registry -u $env:DOCKER_USERNAME -p $env:DOCKER_PASSWORD
    }

    Write-Host "Pushing image: $imageName"
    docker push $imageName
    Write-Host "Push finished."
} else {
    Write-Host "Build finished. To push, set DO_PUSH=1 and provide DOCKER_USERNAME/DOCKER_PASSWORD if needed."
}
