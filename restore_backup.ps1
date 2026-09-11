Write-Host "=== Restoring clean backup from temp_ftp ===" -ForegroundColor Cyan
Copy-Item "C:\Users\Shash\AndroidStudioProjects\EduLabsRTM\backend\temp_ftp\thesis_workspace.php" "C:\Users\Shash\AndroidStudioProjects\EduLabsRTM\backend\thesis_workspace.php" -Force
Write-Host "Backup restored! Run .\deploy_now.ps1 to deploy" -ForegroundColor Green
