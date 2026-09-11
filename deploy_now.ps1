$PROJECT_DIR = "C:\Users\Shash\AndroidStudioProjects\EduLabsRTM"
$FTP_AUTH = "Owner@medigyaan.xyz:MeriMaa007"

Write-Host "Deploying to medigyaan.xyz..." -ForegroundColor Cyan

$files = @(
    @{Local="$PROJECT_DIR\backend\thesis_workspace.php"; Remote="thesis_workspace.php"},
    @{Local="$PROJECT_DIR\backend\sw.js"; Remote="sw.js"}
)

foreach ($f in $files) {
    Write-Host "Uploading $($f.Remote)..." -NoNewline
    $sizeKB = [math]::Round((Get-Item $f.Local).Length / 1kb)
    $result = curl.exe -T $f.Local "ftp://ftp.medigyaan.xyz/$($f.Remote)" --user $FTP_AUTH --ftp-create-dirs 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " OK ($sizeKB KB)" -ForegroundColor Green
    } else {
        Write-Host " FAILED" -ForegroundColor Red
        Write-Host "  $result" -ForegroundColor DarkRed
    }
}

Write-Host "`nDone! Test: https://medigyaan.xyz/Neurons/thesis_workspace.php" -ForegroundColor Cyan
