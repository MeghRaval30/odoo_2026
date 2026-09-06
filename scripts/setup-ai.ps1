# Set up the local language model PeoplePay360 uses for data migration.
#
# Idempotent and safe to re-run. It verifies rather than assumes: after pulling
# the model it fires one real mapping prompt at it and reports PASS or FAIL
# with the latency, because "the pull succeeded" and "the model can do the job"
# are different claims.
#
# ASCII output only. The Windows console is cp1252.
#
#   powershell -ExecutionPolicy Bypass -File scripts\setup-ai.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\setup-ai.ps1 -Model qwen2.5:3b

param(
    [string]$Model = "",
    [string]$Endpoint = "http://127.0.0.1:11434"
)

$ErrorActionPreference = "Stop"

function Say([string]$text)  { Write-Host $text }
function Step([string]$text) { Write-Host ""; Write-Host "-> $text" }
function Ok([string]$text)   { Write-Host "   PASS  $text" }
function Bad([string]$text)  { Write-Host "   FAIL  $text" }
function Note([string]$text) { Write-Host "         $text" }

Say "PeoplePay360 - local model setup"
Say ("=" * 60)

# --------------------------------------------------------------------------
# 1. Is Ollama installed
# --------------------------------------------------------------------------

Step "Looking for Ollama"

$ollama = (Get-Command ollama -ErrorAction SilentlyContinue).Source
if (-not $ollama) {
    $fallback = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path $fallback) { $ollama = $fallback }
}

if (-not $ollama) {
    Bad "Ollama is not installed."
    Note "Download it from https://ollama.com/download, then run this again."
    Note "Everything in the product still works without it - column matching"
    Note "falls back to a synonym dictionary and value profiling."
    exit 0
}
Ok "found at $ollama"

# --------------------------------------------------------------------------
# 2. Is it serving
# --------------------------------------------------------------------------

Step "Checking the service"

function Test-Endpoint {
    try {
        $r = Invoke-WebRequest -Uri "$Endpoint/api/tags" -TimeoutSec 4 `
             -UseBasicParsing -ErrorAction Stop
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

if (Test-Endpoint) {
    Ok "already answering on $Endpoint"
} else {
    Note "not answering; starting it"
    Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
    $up = $false
    foreach ($i in 1..15) {
        Start-Sleep -Seconds 1
        if (Test-Endpoint) { $up = $true; break }
    }
    if ($up) { Ok "started, answering on $Endpoint" }
    else {
        Bad "could not reach $Endpoint after 15 seconds."
        Note "Try running 'ollama serve' in another window and re-run this."
        exit 0
    }
}

# --------------------------------------------------------------------------
# 3. Which model does this machine want
# --------------------------------------------------------------------------

Step "Choosing a model"

if (-not $Model) {
    $vram = $null
    try {
        $out = & nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) { $vram = [int](($out -split "`n")[0].Trim()) }
    } catch { $vram = $null }

    if ($null -eq $vram) {
        Note "no NVIDIA GPU detected; CPU inference is correct but slow"
        $Model = "qwen2.5:3b"
    } elseif ($vram -lt 6000) {
        Note "$vram MB of video memory - using the smaller model"
        $Model = "qwen2.5:3b"
    } else {
        Note "$vram MB of video memory"
        $Model = "qwen2.5:7b"
    }
}
Ok "using $Model"

# --------------------------------------------------------------------------
# 4. Pull it, if it is not already here
# --------------------------------------------------------------------------

Step "Pulling the model"

$tags = (Invoke-WebRequest -Uri "$Endpoint/api/tags" -TimeoutSec 6 -UseBasicParsing).Content |
        ConvertFrom-Json
$have = @($tags.models | ForEach-Object { $_.name })

if ($have -contains $Model) {
    Ok "$Model is already pulled"
} else {
    Note "downloading $Model - this is the slow part, a few GB"
    & $ollama pull $Model
    if ($LASTEXITCODE -ne 0) {
        Bad "the pull failed."
        Note "Check the network, then run: ollama pull $Model"
        exit 0
    }
    Ok "$Model pulled"
}

# --------------------------------------------------------------------------
# 5. Prove it can actually do the job
# --------------------------------------------------------------------------

Step "Testing it on a real prompt"
Note "first call includes loading the weights, so it is the slow one"

$prompt = @"
You map the columns of a messy HR spreadsheet onto a fixed schema.

TARGET FIELDS - choose exactly one per column, or null:
- full_name: the person's whole name in one column
- work_email: official email address
- wage: monthly gross pay in rupees
- date_of_joining: the day employment started

COLUMNS. A deterministic profiler has already inspected the values;
EVIDENCE states what it measured.

COLUMN 1  header='Sal (pm)'
  EVIDENCE: currency-like, values 35000 to 88000, 22 of 22 filled
  SAMPLES: Rs 45,000 | 72,000 | 38500/-

The EVIDENCE is authoritative about what TYPE a column holds. Your job is the
MEANING: which schema field this column is for.

Return JSON only:
{"mappings":[{"column":1,"field":"wage","confidence":0.9,"reason":"short"}]}
"@

$body = @{
    model      = $Model
    prompt     = $prompt
    stream     = $false
    format     = "json"
    keep_alive = "30m"
    options    = @{ temperature = 0; num_predict = 200 }
} | ConvertTo-Json -Depth 5

$started = Get-Date
try {
    $resp = Invoke-WebRequest -Uri "$Endpoint/api/generate" -Method Post `
            -Body $body -ContentType "application/json" -TimeoutSec 180 `
            -UseBasicParsing
    $elapsed = [int]((Get-Date) - $started).TotalMilliseconds
    $answer = ($resp.Content | ConvertFrom-Json).response
    $parsed = $answer | ConvertFrom-Json
    $field = $parsed.mappings[0].field

    if ($field -eq "wage") {
        Ok "answered correctly in $elapsed ms - mapped 'Sal (pm)' to wage"
    } else {
        Bad "answered in $elapsed ms but mapped 'Sal (pm)' to '$field'"
        Note "The model runs but reads columns poorly. Imports still work;"
        Note "the dictionary and profiler carry the result and say so."
    }
} catch {
    Bad "the model did not answer usably: $($_.Exception.Message)"
    Note "Try 'ollama run $Model' by hand to see what it says."
    exit 0
}

# --------------------------------------------------------------------------
# 6. Warm latency, which is what a demo actually feels
# --------------------------------------------------------------------------

Step "Measuring warm latency"
$started = Get-Date
try {
    Invoke-WebRequest -Uri "$Endpoint/api/generate" -Method Post -Body $body `
        -ContentType "application/json" -TimeoutSec 120 -UseBasicParsing | Out-Null
    $warm = [int]((Get-Date) - $started).TotalMilliseconds
    Ok "$warm ms with the weights already resident"
} catch {
    Note "not measured"
}

Say ""
Say ("=" * 60)
Say "Ready."
Say ""
Say "If the model is not the default, tell the backend:"
Say "  set PP360_LLM_MODEL=$Model"
Say ""
Say "Check it any time from project/backend:"
Say "  python manage.py ai_doctor"
Say ""
