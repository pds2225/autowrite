# Quick finish: commit create_pr.ps1 only, then open PR (after push already done)
Set-Location $PSScriptRoot
$ErrorActionPreference = "Continue"

if (Test-Path create_pr.ps1) {
    git add create_pr.ps1 finish_pr.ps1
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        git commit -m "chore: add PR helper scripts"
        git push origin HEAD
    }
}

$branch = git branch --show-current
$prTitle = "fix: DOCX guards and template status UI (follow-up to #13)"
$prBody = @"
## Summary
- Missing template DOCX: Korean UI warning, disabled generate, no HTTP 500
- ``template_docx_ready`` / home DOCX status chips
- Resolve and pin ``template_source.docx`` on new projects

## Test plan
- [ ] pytest ``tests/test_psst_mapping.py`` ``tests/test_loop4_sample_generate.py``
- [ ] Re-upload DOCX → new project → generate → ``results/`` output
"@

gh pr create --title $prTitle --body $prBody --base main
if ($LASTEXITCODE -ne 0) {
    Write-Host "Manual: https://github.com/pds2225/autowrite/pull/new/$branch"
}
