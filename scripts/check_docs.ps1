param(
  [string]$PythonExe = 'python'
)

$ErrorActionPreference = 'Stop'

Write-Host '[check-docs] Validating markdown links...'
$files = @((Get-Item README.md)) + (Get-ChildItem docs -Recurse -File -Filter *.md)
$missing = @()
$formatIssues = @()
$structureIssues = @()
$legacyIssues = @()

foreach ($f in $files) {
  $content = Get-Content $f.FullName -Raw
  $repoRoot = (Get-Location).Path
  $relativePath = $f.FullName.Replace($repoRoot + [System.IO.Path]::DirectorySeparatorChar, '')
  $rel = $relativePath.Replace('\', '/')
  $fileName = [System.IO.Path]::GetFileName($f.FullName)

  # Validate regular markdown links.
  $matches = [regex]::Matches($content, '\[[^\]]+\]\(([^)]+)\)')
  foreach ($m in $matches) {
    $target = $m.Groups[1].Value.Trim()
    if ($target -match '^(http|https|mailto):' -or $target -match '^#') { continue }
    $target = $target.Split('#')[0]
    if ([string]::IsNullOrWhiteSpace($target)) { continue }
    $resolved = Join-Path $f.DirectoryName $target
    if (-not (Test-Path $resolved)) {
      $missing += "$($f.FullName) -> $target"
    }
  }

  # Enforce clickable diagram-source references for Mermaid pages.
  $diagramLines = [regex]::Matches($content, '(?m)^\s*Diagram source:\s*(.+)$')
  foreach ($line in $diagramLines) {
    $rawTarget = $line.Groups[1].Value.Trim()
    $mdLink = [regex]::Match($rawTarget, '^\[[^\]]+\]\(([^)]+)\)\.?$')
    if (-not $mdLink.Success) {
      $formatIssues += "$($f.FullName) -> Diagram source is not a markdown link"
      continue
    }

    $target = $mdLink.Groups[1].Value.Trim().Split('#')[0]
    if (-not [string]::IsNullOrWhiteSpace($target)) {
      $resolved = Join-Path $f.DirectoryName $target
      if (-not (Test-Path $resolved)) {
        $missing += "$($f.FullName) -> $target"
      }
    }
  }

  # Guard against legacy path references after docs refactor.
  if ($content -match 'guides/runbooks/' -or $content -match 'docs/observability\.md') {
    $legacyIssues += "$rel -> contains legacy docs path reference"
  }

  # Structural lint for docs pages (skip root README and ADR pages).
  if ($rel -eq 'README.md') { continue }
  if (-not $rel.StartsWith('docs/')) { continue }
  if ($rel -match '^docs/architecture/decisions/adr-\d+') { continue }
  if ($fileName -eq 'README.md') { continue }

  if (-not [regex]::IsMatch($content, '(?m)^Audience:\s+.+$')) {
    $structureIssues += "$rel -> missing 'Audience:' line"
  }
  if (-not [regex]::IsMatch($content, '(?m)^Goal:\s+.+$')) {
    $structureIssues += "$rel -> missing 'Goal:' line"
  }

  # Guide minimum structure.
  if ($rel -like 'docs/guides/*') {
    foreach ($heading in @('Expected Outcome', 'Prerequisites', 'Rollback', 'Links')) {
      if (-not [regex]::IsMatch($content, "(?m)^##\s+$heading\s*$")) {
        $structureIssues += "$rel -> missing '## $heading'"
      }
    }

    $actionSections = @(
      'Steps',
      'Setup Flow',
      'Tuning Steps',
      'Change-Type Checklist',
      'Validation',
      'Runtime Flow',
      'Symptoms and Checks',
      'Policy',
      'Local Development'
    )
    $hasActionSection = $false
    foreach ($s in $actionSections) {
      if ([regex]::IsMatch($content, "(?m)^##\s+$s\s*$")) {
        $hasActionSection = $true
        break
      }
    }
    if (-not $hasActionSection) {
      $structureIssues += "$rel -> missing action section (e.g. '## Steps')"
    }
  }

  # Runbook minimum structure.
  if ($rel -like 'docs/runbooks/*') {
    foreach ($heading in @('Symptoms', 'Checks', 'Mitigation', 'Rollback', 'Escalation', 'Code Investigation Pointers', 'Links')) {
      if (-not [regex]::IsMatch($content, "(?m)^##\s+$heading\s*$")) {
        $structureIssues += "$rel -> missing '## $heading'"
      }
    }
  }

  # Architecture minimum structure.
  if ($rel -like 'docs/architecture/*' -and $rel -notlike 'docs/architecture/decisions/*') {
    foreach ($heading in @('Purpose', 'Links')) {
      if (-not [regex]::IsMatch($content, "(?m)^##\s+$heading\s*$")) {
        $structureIssues += "$rel -> missing '## $heading'"
      }
    }
  }

  # Reference minimum structure.
  if ($rel -like 'docs/reference/*') {
    if (-not [regex]::IsMatch($content, '(?m)^##\s+Links\s*$')) {
      $structureIssues += "$rel -> missing '## Links'"
    }
  }
}

if ($formatIssues.Count -gt 0) {
  Write-Host '[check-docs] Diagram source format issues found:'
  $formatIssues | ForEach-Object { Write-Host "  $_" }
  exit 1
}

if ($legacyIssues.Count -gt 0) {
  Write-Host '[check-docs] Legacy docs path issues found:'
  $legacyIssues | ForEach-Object { Write-Host "  $_" }
  exit 1
}

if ($missing.Count -gt 0) {
  Write-Host '[check-docs] Missing links found:'
  $missing | ForEach-Object { Write-Host "  $_" }
  exit 1
}
Write-Host '[check-docs] Links OK.'

if ($structureIssues.Count -gt 0) {
  Write-Host '[check-docs] Structure lint issues found:'
  $structureIssues | ForEach-Object { Write-Host "  $_" }
  exit 1
}
Write-Host '[check-docs] Structure OK.'

Write-Host '[check-docs] Validating configs/demo.yaml load...'
$script = @"
import sys
sys.path.insert(0, 'src')
from tycherion.shared.config import load_config
cfg = load_config('configs/demo.yaml')
assert cfg.application.portfolio.threshold_weight is not None
print('config_ok')
"@
$script | & $PythonExe -
Write-Host '[check-docs] Config OK.'
