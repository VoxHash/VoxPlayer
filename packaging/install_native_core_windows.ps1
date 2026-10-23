# Clear per-OS installer helper: native C media core for Windows.
# Downloads are not automated (license / mirror choice). Guides PATH / VLC_HOME.

Write-Host "VoxPlayer — native C media core (Windows)"
Write-Host ""

$candidates = @(
    "${env:ProgramFiles}\VideoLAN\VLC",
    "${env:ProgramFiles(x86)}\VideoLAN\VLC",
    $env:VLC_HOME
) | Where-Object { $_ -and (Test-Path $_) }

$found = $null
foreach ($dir in $candidates) {
    if (Test-Path (Join-Path $dir "libvlc.dll")) {
        $found = $dir
        break
    }
}

if (-not $found) {
    Write-Host "libvlc.dll not found."
    Write-Host "1. Install the desktop media suite (VideoLAN VLC) for Windows."
    Write-Host "2. Re-run this script, or set VLC_HOME to the install folder."
    Write-Host "3. pip install python-vlc"
    exit 1
}

Write-Host "Found native core at: $found"
$env:VLC_HOME = $found
[Environment]::SetEnvironmentVariable("VLC_HOME", $found, "User")

$path = [Environment]::GetEnvironmentVariable("Path", "User")
if ($path -notlike "*$found*") {
    [Environment]::SetEnvironmentVariable("Path", "$found;$path", "User")
    Write-Host "Added to user PATH: $found"
}

Write-Host "Also ensure: pip install python-vlc"
Write-Host "Native C media core setup finished."
