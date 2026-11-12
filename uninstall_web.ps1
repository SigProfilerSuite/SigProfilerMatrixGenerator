# Remove what the SigProfilerMatrixGenerator Workbench installed on this Windows computer:
#   - its private Python environment, .venv-dashboard, next to this script
#   - its run records, in %LOCALAPPDATA%\SigProfilerMatrixGenerator
#   - only if you say so as well: the reference genomes installed in this folder, in
#     SigProfilerMatrixGenerator\references\chromosomes\tsb (runs from Python or the
#     command line in this folder use them too)
# Your matrices (wherever runs wrote them) and the rest of this folder are kept; delete them
# yourself if you no longer need them. Run it by double-clicking uninstall_web.bat, or:
# powershell -File uninstall_web.ps1 [--yes] [--genomes]

$ErrorActionPreference = 'Continue'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $Here '.venv-dashboard'
$Tsb = Join-Path $Here 'SigProfilerMatrixGenerator\references\chromosomes\tsb'
$LocalAppData = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $HOME 'AppData\Local' }
$State = Join-Path $LocalAppData 'SigProfilerMatrixGenerator'
$Yes = ($args -contains '--yes') -or ($args -contains '-y')
$GenomesToo = $args -contains '--genomes'

function Test-InUse {
    # The Workbench, or one of its runs, still running?
    $pidfile = Join-Path $State 'dashboard.pid'
    if (Test-Path $pidfile) {
        $first = ((Get-Content $pidfile -Raw) -split ':')[0]
        $id = 0
        if ([int]::TryParse($first, [ref]$id) -and (Get-Process -Id $id -ErrorAction SilentlyContinue)) { return $true }
    }
    $procs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue
    foreach ($p in $procs) {
        if ($p.CommandLine -and $p.CommandLine.Contains('SigProfilerMatrixGenerator.web') -and
            (($p.ExecutablePath -and $p.ExecutablePath.StartsWith($Venv, 'OrdinalIgnoreCase')) -or
             $p.CommandLine.Contains($Venv))) { return $true }
    }
    return $false
}

function Get-Size($paths) {
    $bytes = ($paths | ForEach-Object { Get-ChildItem -LiteralPath $_ -Recurse -File -Force -ErrorAction SilentlyContinue } |
        Measure-Object -Property Length -Sum).Sum
    if ($bytes) { '{0:N1} GB' -f ($bytes / 1GB) } else { '?' }
}

Write-Host ""
Write-Host "  SigProfilerMatrixGenerator Workbench uninstaller"
Write-Host "  ------------------------------------------------"

if (Test-InUse) {
    Write-Host "  The Workbench is still running. Click Quit in it (or run launch_web.bat --stop),"
    Write-Host "  then run this again."
    exit 1
}

$HasVenv = Test-Path (Join-Path $Venv 'pyvenv.cfg')
$Jobs = Join-Path $State 'jobs'
$HasState = (Test-Path $Jobs) -or (Test-Path (Join-Path $State 'dashboard.pid')) -or (Test-Path (Join-Path $State 'dashboard.lock'))
$Runs = if (Test-Path $Jobs) { @(Get-ChildItem -LiteralPath $Jobs -Directory -ErrorAction SilentlyContinue).Count } else { 0 }

# Installed genomes: one folder each under tsb\, which the package ships empty (but for
# __init__.py). Unfinished downloads (spmg-reference-*) are not genomes.
$Genomes = @()
if (Test-Path $Tsb) {
    $Genomes = @(Get-ChildItem -LiteralPath $Tsb -Directory -ErrorAction SilentlyContinue |
        Where-Object { -not $_.Name.StartsWith('__') -and -not $_.Name.StartsWith('spmg-reference-') } |
        ForEach-Object { $_.Name })
}
$HasGenomes = $Genomes.Count -gt 0

if (-not $HasVenv -and -not $HasState -and -not $HasGenomes) {
    Write-Host "  Nothing to remove: the Workbench's Python environment and run records are not here."
    exit 0
}

$Remove = $false
if ($HasVenv -or $HasState) {
    Write-Host "  This removes:"
    if ($HasVenv) { Write-Host "    - the Python environment $Venv ($(Get-Size @($Venv)))" }
    if ($HasState) { Write-Host "    - the records of $Runs run(s) in $State (settings and logs, not matrices)" }
    Write-Host ""
    Write-Host "  It keeps your matrices (each run's output folder) and this folder ($Here)."
    Write-Host ""

    if ($Yes) {
        $Remove = $true
    } else {
        $ans = Read-Host "  Remove them? Type y and press Enter"
        if ($ans -notmatch '^(y|yes)$') {
            Write-Host "  Nothing was removed."
            exit 0
        }
        $Remove = $true
        Write-Host ""
    }
} else {
    Write-Host "  The Workbench's Python environment and run records are not here."
    Write-Host ""
}

$RemoveGenomes = $false
if ($HasGenomes) {
    $paths = $Genomes | ForEach-Object { Join-Path $Tsb $_ }
    Write-Host "  Reference genomes installed in this folder: $($Genomes -join ' ') ($(Get-Size $paths))"
    Write-Host "    in $Tsb"
    Write-Host "  Runs from Python or the command line in this folder use them too, and each one"
    Write-Host "  takes a while to download again."
    if ($GenomesToo) {
        $RemoveGenomes = $true
    } elseif ($Yes) {
        Write-Host "  They are kept (--genomes removes them too)."
    } else {
        $ans = Read-Host "  Remove these genomes too? Type y and press Enter, or just Enter to keep them"
        if ($ans -match '^(y|yes)$') { $RemoveGenomes = $true } else { Write-Host "  The genomes are kept." }
    }
    Write-Host ""
}

$status = 0
if ($Remove -and $HasVenv) {
    Remove-Item -LiteralPath $Venv -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path $Venv) {
        Write-Host "  Could not remove $Venv; delete that folder yourself (close anything using it first)."
        $status = 1
    } else {
        Write-Host "  Removed $Venv."
    }
}
if ($Remove -and $HasState) {
    # Only the Workbench's own files; the folder goes only if that empties it.
    Remove-Item -LiteralPath $Jobs -Recurse -Force -ErrorAction SilentlyContinue
    foreach ($f in @('dashboard.pid', 'dashboard.lock')) {
        Remove-Item -LiteralPath (Join-Path $State $f) -Force -ErrorAction SilentlyContinue
    }
    if ((Test-Path $State) -and -not (Get-ChildItem -LiteralPath $State -Force)) { Remove-Item -LiteralPath $State -Force }
    if (Test-Path $Jobs) {
        Write-Host "  Could not remove the run records in $State; delete them yourself."
        $status = 1
    } else {
        Write-Host "  Removed the run records."
    }
}
if ($RemoveGenomes) {
    foreach ($name in $Genomes) {
        $dir = Join-Path $Tsb $name
        Remove-Item -LiteralPath $dir -Recurse -Force -ErrorAction SilentlyContinue
        if (Test-Path $dir) {
            Write-Host "  Could not remove $dir; delete that folder yourself."
            $status = 1
        } else {
            Write-Host "  Removed the reference genome $name."
        }
    }
}

if (-not $Remove -and -not $RemoveGenomes) {
    Write-Host "  Nothing was removed."
    exit 0
}

Write-Host ""
Write-Host "  Done. To start again later, double-click launch_web.bat: it sets everything up anew."
Write-Host "  To remove the rest, delete this folder and, if you no longer need them, your matrices."
exit $status
