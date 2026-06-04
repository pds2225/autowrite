# Auto Write: commit all app changes and open PR
# Run: powershell -ExecutionPolicy Bypass -File D:\auto_write\autowrite_repo\create_pr.ps1
Set-Location $PSScriptRoot

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$Args)
    & git @Args
    if ($LASTEXITCODE -ne 0) { throw "git $($Args -join ' ') failed with $LASTEXITCODE" }
}

Write-Host "[1/8] git status"
git status --short
$branch = git branch --show-current
Write-Host "Branch: $branch"

$files = @(
    "app/auto_write/main.py",
    "app/auto_write/config.py",
    "app/auto_write/models.py",
    "app/auto_write/storage.py",
    "app/auto_write/services/project_service.py",
    "app/auto_write/services/render_service.py",
    "app/auto_write/analysis/docx_template.py",
    "app/auto_write/templates/index.html",
    "app/auto_write/templates/template_detail.html",
    "app/auto_write/templates/project_detail.html",
    "app/auto_write/static/style.css",
    "app/tests/test_psst_mapping.py",
    "app/tests/test_loop4_sample_generate.py",
    "app/tests/test_service_resilience.py",
    "app/tests/test_document_ingest.py",
    "app/tests/test_project_service_safety.py"
)

Write-Host "[2/8] git add app/"
foreach ($f in $files) {
    if (Test-Path $f) { git add $f }
}
git diff --name-only -- app/ |
    Where-Object { $_ -notmatch '\.bak\.' -and $_ -notmatch '_backup\.' } |
    ForEach-Object { git add $_ }

Write-Host "[3/8] git commit (app)"
$commitMsg = @"
fix: PSST workflow, results export, and missing DOCX guards

- Map user brief/notes to PSST; psst_only and disable_images defaults
- Publish results bundle (hwp_paste.txt, copy_blocks, generation_summary)
- Resolve template source DOCX; Korean errors instead of HTTP 500
- Home/template UI: DOCX status chips; disable generate when DOCX missing
"@
$staged = git diff --cached --name-only
if ($staged) {
    Invoke-Git -Args @("commit", "-m", $commitMsg)
} else {
    Write-Host "[INFO] No staged app changes (may already be committed)."
}

Write-Host "[4/8] commit helper scripts (avoid gh dirty-tree warning)"
foreach ($helper in @("create_pr.ps1", "git_push_500fix.bat")) {
    if (Test-Path $helper) { git add $helper }
}
$helperStaged = git diff --cached --name-only
if ($helperStaged) {
    Invoke-Git -Args @("commit", "-m", "chore: add PR and git helper scripts")
}

Write-Host "[5/8] ensure branch"
$branch = git branch --show-current
if (-not $branch -or $branch -eq "(no branch)") {
    Invoke-Git -Args @("checkout", "-b", "fix/psst-docx-guards-20260602")
    $branch = git branch --show-current
}

Write-Host "[6/8] git push"
Invoke-Git -Args @("push", "-u", "origin", "HEAD")

Write-Host "[7/8] gh pr create"
$prTitle = "fix: PSST mapping, DOCX guards, and results export"
$prBody = @"
## Summary
- PSST input mapping and reduced autofill/render scope (psst_only, disable_images)
- ``results/`` export with HWP paste text, copy blocks, and Korean generation summary
- Missing template DOCX: resolve path, UI warning, disabled buttons, no Internal Server Error

## Test plan
- [ ] ``cd app`` + ``pytest tests/test_psst_mapping.py tests/test_loop4_sample_generate.py -q``
- [ ] ``launch.bat`` → re-upload template DOCX → new project → generate
- [ ] Verify ``results/{project_id}/hwp_paste.txt`` and dated DOCX

## Note
Follow-up to merged PR #13; adds DOCX missing guards and home/template status UI.
"@

$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    $existing = gh pr list --head $branch --state open --json url,number --jq ".[0]" 2>$null | ConvertFrom-Json
    if ($existing -and $existing.url) {
        Write-Host "[INFO] Open PR already exists: $($existing.url)"
        gh pr edit $existing.url --title $prTitle --body $prBody 2>&1 | Out-Host
        Write-Host "PR_URL=$($existing.url)"
    } else {
        $out = gh pr create --title $prTitle --body $prBody --base main 2>&1
        $out | Out-Host
        if ($LASTEXITCODE -ne 0) {
            $out = gh pr create --title $prTitle --body $prBody 2>&1
            $out | Out-Host
        }
        if ($LASTEXITCODE -eq 0) {
            $url = ($out | Select-String -Pattern "https://github.com/.+/pull/\d+" | Select-Object -First 1).Matches.Value
            if ($url) { Write-Host "PR_URL=$url" }
        } else {
            Write-Host "[WARN] gh pr create failed. Open manually:"
            Write-Host "https://github.com/pds2225/autowrite/pull/new/$branch"
            exit 1
        }
    }
} finally {
    $ErrorActionPreference = $prevEap
}

Write-Host "[8/8] done"
Write-Host "COMMIT=$(git rev-parse HEAD)"
Write-Host "BRANCH=$(git branch --show-current)"
