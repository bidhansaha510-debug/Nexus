# ═══════════════════════════════════════════════════════════════
# NEXUS AI Mobile — APK Build Script
# Automatically downloads Android SDK tools and builds the APK
# ═══════════════════════════════════════════════════════════════

param(
    [switch]$Release,
    [switch]$SkipSync
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AndroidDir = Join-Path $ScriptDir "android"
$SdkDir = Join-Path (Join-Path $env:LOCALAPPDATA "Android") "Sdk"

Write-Host ""
Write-Host "  NEXUS AI - Mobile APK Builder" -ForegroundColor Cyan
Write-Host "  =============================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Check/Install Android SDK ──
function Install-AndroidSdk {
    if (Test-Path (Join-Path $SdkDir "platform-tools")) {
        Write-Host "  [OK] Android SDK found at $SdkDir" -ForegroundColor Green
        return
    }

    Write-Host "  [DL] Android SDK not found. Downloading command-line tools..." -ForegroundColor Yellow

    $ToolsZip = Join-Path $env:TEMP "android-cmdline-tools.zip"
    $ToolsUrl = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"

    Write-Host "       Downloading from $ToolsUrl ..."
    Invoke-WebRequest -Uri $ToolsUrl -OutFile $ToolsZip -UseBasicParsing

    $CmdlineDir = Join-Path $SdkDir "cmdline-tools"
    New-Item -ItemType Directory -Path $CmdlineDir -Force | Out-Null
    Expand-Archive -Path $ToolsZip -DestinationPath $CmdlineDir -Force

    $ExtractedDir = Join-Path $CmdlineDir "cmdline-tools"
    $LatestDir = Join-Path $CmdlineDir "latest"
    if (Test-Path $ExtractedDir) {
        if (Test-Path $LatestDir) { Remove-Item $LatestDir -Recurse -Force }
        Rename-Item $ExtractedDir $LatestDir
    }

    Remove-Item $ToolsZip -Force -ErrorAction SilentlyContinue

    $sdkMgr = Join-Path $LatestDir "bin" "sdkmanager.bat"
    if (-not (Test-Path $sdkMgr)) {
        Write-Host "  [FAIL] sdkmanager not found at $sdkMgr" -ForegroundColor Red
        exit 1
    }

    Write-Host "  [DL] Installing required SDK packages..." -ForegroundColor Yellow

    # Accept all licenses by piping 'y' answers
    $licenseAnswers = @("y") * 30
    $licenseAnswers | cmd /c "$sdkMgr --licenses --sdk_root=$SdkDir" 2>$null

    # Install required packages
    cmd /c "$sdkMgr --sdk_root=$SdkDir `"platforms;android-34`" `"build-tools;34.0.0`" `"platform-tools`""

    Write-Host "  [OK] Android SDK installed successfully" -ForegroundColor Green
}

# ── Step 2: Set environment ──
function Set-Env {
    $env:ANDROID_HOME = $SdkDir
    $env:ANDROID_SDK_ROOT = $SdkDir
    Write-Host "  [OK] ANDROID_HOME = $SdkDir" -ForegroundColor DarkGray
}

# ── Step 3: Sync Capacitor ──
function Invoke-CapSync {
    if ($SkipSync) {
        Write-Host "  [--] Skipping Capacitor sync" -ForegroundColor DarkGray
        return
    }
    Write-Host "  [..] Syncing Capacitor web assets..." -ForegroundColor Yellow
    Push-Location $ScriptDir
    npx cap sync android
    Pop-Location
    Write-Host "  [OK] Capacitor sync complete" -ForegroundColor Green
}

# ── Step 3.5: Generate icons from icon.jpeg ──
function Invoke-IconGeneration {
    $iconScript = Join-Path $ScriptDir "generate_icons.js"
    if (Test-Path $iconScript) {
        Write-Host "  [..] Generating app icons from icon/icon.jpeg..." -ForegroundColor Yellow
        Push-Location $ScriptDir
        node $iconScript
        Pop-Location
        Write-Host "  [OK] Icons generated" -ForegroundColor Green
    } else {
        Write-Host "  [--] No generate_icons.js found, skipping" -ForegroundColor DarkGray
    }
}

# ── Step 4: Build APK ──
function Invoke-GradleBuild {
    $BuildType = if ($Release) { "assembleRelease" } else { "assembleDebug" }
    Write-Host "  [..] Building APK ($BuildType)..." -ForegroundColor Yellow

    Push-Location $AndroidDir

    $gradlewPath = Join-Path $AndroidDir "gradlew.bat"
    cmd /c "$gradlewPath $BuildType --no-daemon"

    $exitCode = $LASTEXITCODE
    Pop-Location

    if ($exitCode -ne 0) {
        Write-Host "  [FAIL] Build failed with exit code $exitCode" -ForegroundColor Red
        exit $exitCode
    }

    Write-Host "  [OK] Build complete!" -ForegroundColor Green
}

# ── Step 5: Report output ──
function Show-Result {
    $ApkDir = "$AndroidDir\app\build\outputs\apk"
    $DebugApk = "$ApkDir\debug\app-debug.apk"
    $ReleaseApk = "$ApkDir\release\app-release-unsigned.apk"

    $Apk = $null
    if ($Release -and (Test-Path $ReleaseApk)) {
        $Apk = $ReleaseApk
    } elseif (Test-Path $DebugApk) {
        $Apk = $DebugApk
    }

    Write-Host ""
    if ($Apk) {
        $Size = [math]::Round((Get-Item $Apk).Length / 1MB, 1)
        Write-Host "  ========================================" -ForegroundColor Green
        Write-Host "              APK READY!                  " -ForegroundColor Green
        Write-Host "  ========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "  APK: $Apk" -ForegroundColor White
        Write-Host "  Size: ${Size} MB" -ForegroundColor DarkGray
        Write-Host ""
        Write-Host "  To install on your phone:" -ForegroundColor Yellow
        Write-Host "    1. Transfer the APK to your Android device" -ForegroundColor DarkGray
        Write-Host "    2. Open it and tap Install" -ForegroundColor DarkGray
        Write-Host "    3. Allow Install from unknown sources if prompted" -ForegroundColor DarkGray
        Write-Host ""

        # Copy to mobile root for easy access
        $CopyDest = Join-Path $ScriptDir "NEXUS-AI.apk"
        Copy-Item $Apk $CopyDest -Force
        Write-Host "  Copied to: $CopyDest" -ForegroundColor Cyan
    } else {
        Write-Host "  [WARN] APK not found in expected location." -ForegroundColor Yellow
        Write-Host "  Check: $ApkDir" -ForegroundColor DarkGray
    }
    Write-Host ""
}

# ═══ MAIN ═══
try {
    Install-AndroidSdk
    Set-Env
    Invoke-CapSync
    Invoke-IconGeneration
    Invoke-GradleBuild
    Show-Result
} catch {
    Write-Host ""
    Write-Host "  [ERROR] $_" -ForegroundColor Red
    Write-Host "  Stack: $($_.ScriptStackTrace)" -ForegroundColor DarkGray
    exit 1
}
