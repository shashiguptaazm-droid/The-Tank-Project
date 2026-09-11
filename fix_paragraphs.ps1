$content = [System.IO.File]::ReadAllText('C:\Users\Shash\AndroidStudioProjects\EduLabsRTM\backend\thesis_workspace.php')
$old = 'const paragraphs = sec.paragraphs || [sec.content || ""];'
$new = 'const paragraphs = (sec.paragraphs && sec.paragraphs.length > 0) ? sec.paragraphs : [sec.content || ""];'
if ($content.Contains($old)) {
    $content = $content.Replace($old, $new)
    [System.IO.File]::WriteAllText('C:\Users\Shash\AndroidStudioProjects\EduLabsRTM\backend\thesis_workspace.php', $content)
    Write-Host "FIXED: Updated paragraphs fallback logic" -ForegroundColor Green
} else {
    Write-Host "NOT FOUND: Could not find exact string" -ForegroundColor Red
    $lines = $content -split "`n"
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match 'sec\.paragraphs') {
            Write-Host "Line $($i+1):" -ForegroundColor Yellow
            Write-Host "  [$([System.BitConverter]::ToString([System.Text.Encoding]::UTF8.GetBytes($lines[$i])))]"
        }
    }
}
