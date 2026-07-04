# Auto-commit and push when there are meaningful changes.
# Skips if working tree is clean. Never stages .env or secrets.

$ErrorActionPreference = "Stop"
$git = "C:\Program Files\Git\cmd\git.exe"
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot

$status = & $git status --porcelain
if (-not $status) {
    Write-Output "git-auto-push: clean — nothing to commit"
    exit 0
}

# Unstage secrets if accidentally tracked
& $git reset HEAD -- .env 2>$null
& $git reset HEAD -- "**/.env" 2>$null

& $git add -A
& $git reset HEAD -- .env 2>$null
& $git reset HEAD -- data-answers-agent/.env 2>$null

$staged = & $git diff --staged --name-only
if (-not $staged) {
    Write-Output "git-auto-push: no safe staged changes"
    exit 0
}

$summary = ($staged | Select-Object -First 5) -join ", "
if ($staged.Count -gt 5) { $summary += ", ..." }

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
$message = @"
Auto-sync: update project files ($timestamp).

Includes: $summary
"@

& $git -c user.name="harishhooli-coder" -c user.email="harishhooli-coder@users.noreply.github.com" `
    commit -m $message

$branch = (& $git rev-parse --abbrev-ref HEAD).Trim()
& $git push -u origin $branch
Write-Output "git-auto-push: pushed to origin/$branch"
