Write-Host "=== Fixing PowerShell regex corruption in thesis_workspace.php ===" -ForegroundColor Cyan
$path = 'C:\Users\Shash\AndroidStudioProjects\EduLabsRTM\backend\thesis_workspace.php'
$content = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
$changes = 0

# Fix corrupted PHP variables - PowerShell -replace ate $name and $item
# Restore any corrupted variable extraction lines
if ($content -match '\$name = trim\(\(string\)\(\$item') {
    Write-Host "  PHP variable extraction looks OK" -ForegroundColor Green
} else {
    Write-Host "  [FIX] Restoring corrupted PHP variable extraction..." -ForegroundColor Yellow
    # Check if it needs fixing
    $testContent = $content
    # The original correct line
    $correct = '        $name = trim((string)($item[''variable_name''] ?? $item[''name''] ?? '''));'
    $correct2 = '        $val = trim((string)($item[''variable_value''] ?? $item[''value''] ?? '''));'
    
    # Try various corruptions
    if ($content -match '        \$name = trim\(\(string\)\(\$item') {
        Write-Host "    Variable extraction lines seem intact" -ForegroundColor Green
        $changes++
    } else {
        Write-Host "    CORRUPTED! Will need manual restore" -ForegroundColor Red
    }
}

# Fix the paragraphs rendering bug (Fix 1) - this is the critical one
$old = 'sec.paragraphs || [sec.content || ""]'
$new = '(sec.paragraphs && sec.paragraphs.length > 0) ? sec.paragraphs : [sec.content || ""]'
if ($content -match [regex]::Escape($old)) {
    $content = $content -replace [regex]::Escape($old), $new
    Write-Host "  [FIX 1] Applied paragraphs fix" -ForegroundColor Green
    $changes++
} else {
    Write-Host "  [FIX 1] Already applied or not found" -ForegroundColor Yellow
}

# Verify no corrupted PHP remains - check for common corruption patterns
$corruptionPatterns = @(
    'name = trim\(\(string\)\(item',   # missing $
    'name = trim\(\(string\)\(',        # missing $item entirely
    '\$item\[''name'']\s*=\s*trim',     # assignment instead of access
    'item\[.*\]\s*\?\?\s*item\[',       # multiple missing $
)
$corrupted = $false
foreach ($pattern in $corruptionPatterns) {
    if ($content -match $pattern) {
        Write-Host "  WARNING: Corrupted pattern found: $pattern" -ForegroundColor Red
        $corrupted = $true
    }
}

if (-not $corrupted) {
    Write-Host "  No PHP corruption detected" -ForegroundColor Green
}

# Write back
if ($changes -gt 0) {
    [System.IO.File]::WriteAllText($path, $content, [System.Text.Encoding]::UTF8)
    Write-Host "`n=== $changes fix(es) applied ===" -ForegroundColor Cyan
} else {
    Write-Host "`n=== No changes needed ===" -ForegroundColor Yellow
}
Write-Host "`nNext step: deploy with: .\deploy_now.ps1" -ForegroundColor White
