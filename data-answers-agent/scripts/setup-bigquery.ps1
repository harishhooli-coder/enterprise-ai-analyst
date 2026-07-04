# Bootstrap GCP project + BigQuery dataset for Data-Answers Agent (Path A dev pilot).
# Requires: gcloud/bq CLI, authenticated user with billing access.
#
# Usage:
#   .\scripts\setup-bigquery.ps1
#   .\scripts\setup-bigquery.ps1 -ProjectId my-unique-project-id

param(
    [string]$ProjectId = "",
    [string]$Dataset = "analytics",
    [string]$Location = "US",
    [string]$ProjectName = "Data Answers Agent Dev"
)

$ErrorActionPreference = "Stop"

function Get-Gcloud {
    $candidates = @(
        "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) { return $path }
    }
    throw "gcloud not found. Install Google Cloud SDK: winget install Google.CloudSDK"
}

function Get-Bq {
    $gcloud = Get-Gcloud
    return (Join-Path (Split-Path $gcloud) "bq.cmd")
}

$Gcloud = Get-Gcloud
$Bq = Get-Bq
$RepoRoot = Split-Path $PSScriptRoot -Parent

Write-Host "==> Checking gcloud authentication..."
$auth = & $Gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null
if (-not $auth) {
    Write-Host "No active gcloud account. Opening browser login..."
    & $Gcloud auth login
    & $Gcloud auth application-default login
    $auth = & $Gcloud auth list --filter=status:ACTIVE --format="value(account)"
}
Write-Host "Authenticated as: $auth"

if (-not $ProjectId) {
    $suffix = Get-Random -Minimum 100000 -Maximum 999999
    $ProjectId = "if-data-answers-dev-$suffix"
}

Write-Host "==> Using project id: $ProjectId"

$existing = & $Gcloud projects describe $ProjectId --format="value(projectId)" 2>$null
if (-not $existing) {
    Write-Host "==> Creating GCP project..."
    & $Gcloud projects create $ProjectId --name=$ProjectName | Out-Host

    Write-Host "==> Linking billing (required for BigQuery beyond free sandbox)..."
    $billing = & $Gcloud billing accounts list --format="value(name)" --filter="open=true" 2>$null | Select-Object -First 1
    if (-not $billing) {
        throw @"
No open billing account found on this Google account.
Enable billing at https://console.cloud.google.com/billing and re-run this script with -ProjectId $ProjectId
"@
    }
    & $Gcloud billing projects link $ProjectId --billing-account=$billing | Out-Host
} else {
    Write-Host "Project already exists; continuing."
}

& $Gcloud config set project $ProjectId | Out-Host

Write-Host "==> Enabling BigQuery API..."
& $Gcloud services enable bigquery.googleapis.com bigqueryconnection.googleapis.com --project=$ProjectId | Out-Host

Write-Host "==> Creating dataset $Dataset ($Location)..."
& $Bq --project_id=$ProjectId mk --dataset --location=$Location "${ProjectId}:${Dataset}" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Dataset may already exist; continuing."
}

Write-Host "==> Creating tables..."
$sqlTemplate = Get-Content (Join-Path $PSScriptRoot "bigquery-bootstrap.sql") -Raw
$sql = $sqlTemplate.Replace("{project}", $ProjectId).Replace("{dataset}", $Dataset)
$sql | & $Bq query --project_id=$ProjectId --use_legacy_sql=false | Out-Host

Write-Host "==> Generating row-level seed data from mock_data..."
Push-Location $RepoRoot
python (Join-Path $PSScriptRoot "generate_bq_seed.py")
Pop-Location

$seedDir = Join-Path $PSScriptRoot "bq_seed"
Write-Host "==> Loading seed data..."
& $Bq load --project_id=$ProjectId --source_format=NEWLINE_DELIMITED_JSON --replace=true "${ProjectId}:${Dataset}.sales" (Join-Path $seedDir "sales.ndjson") "month:STRING,region:STRING,amount:FLOAT,net_amount:FLOAT"
& $Bq load --project_id=$ProjectId --source_format=NEWLINE_DELIMITED_JSON --replace=true "${ProjectId}:${Dataset}.orders" (Join-Path $seedDir "orders.ndjson") "order_id:STRING,month:STRING,region:STRING,order_amount:FLOAT"
& $Bq load --project_id=$ProjectId --source_format=NEWLINE_DELIMITED_JSON --replace=true "${ProjectId}:${Dataset}.customers" (Join-Path $seedDir "customers.ndjson") "customer_id:STRING,month:STRING,region:STRING"

Write-Host "==> Smoke test query..."
& $Bq query --project_id=$ProjectId --use_legacy_sql=false "SELECT SUM(amount) AS total_revenue FROM \`${ProjectId}.${Dataset}.sales\` WHERE month = '2026-06' AND region IN ('US','EU')" | Out-Host

$envExample = Join-Path $RepoRoot ".env.example"
$envFile = Join-Path $RepoRoot ".env"
if (-not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile
}

Write-Host @"

==> Done. Update your .env with:

BQ_PROJECT_ID=$ProjectId
BQ_DATASET=$Dataset
BQ_USE_MOCK=0
IDENTITY_MODE=stub

Application Default Credentials are set if you ran 'gcloud auth application-default login'.
Restart the API and POST /ask with a grounded question to verify live BigQuery.

"@
