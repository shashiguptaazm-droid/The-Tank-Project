@echo off
echo ============================================
echo  Deploying backend files to medigyaan.xyz
echo ============================================
echo.

set PROJECT_DIR=C:\Users\Shash\AndroidStudioProjects\EduLabsRTM
set FTP_HOST=ftp.medigyaan.xyz
set FTP_USER=Owner@medigyaan.xyz
set FTP_PASS=MeriMaa007

echo [1/2] Uploading thesis_chapter_generator.php...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
$ftp = [System.Net.FtpWebRequest]::Create('ftp://%FTP_HOST%/thesis_chapter_generator.php'); ^
$ftp.Method = [System.Net.WebRequestMethods+Ftp]::UploadFile; ^
$ftp.Credentials = New-Object System.Net.NetworkCredential('%FTP_USER%', '%FTP_PASS%'); ^
$ftp.UsePassive = $true; ^
$ftp.UseBinary = $true; ^
$content = [System.IO.File]::ReadAllBytes('%PROJECT_DIR%\backend\thesis_chapter_generator.php'); ^
$ftp.ContentLength = $content.Length; ^
try { ^
  $stream = $ftp.GetRequestStream(); ^
  $stream.Write($content, 0, $content.Length); ^
  $stream.Close(); ^
  $response = $ftp.GetResponse(); ^
  Write-Host '  -> SUCCESS: Uploaded thesis_chapter_generator.php (' ([math]::Round($content.Length / 1kb)) 'KB)' -ForegroundColor Green; ^
} catch { ^
  Write-Host '  -> FAILED: ' $_.Exception.Message -ForegroundColor Red; ^
  exit 1; ^
}

if %ERRORLEVEL% NEQ 0 (
  echo.
  echo FAILED! Check the error above.
  pause
  exit /b 1
)

echo [2/2] Uploading thesis_workspace.php...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
$ftp = [System.Net.FtpWebRequest]::Create('ftp://%FTP_HOST%/thesis_workspace.php'); ^
$ftp.Method = [System.Net.WebRequestMethods+Ftp]::UploadFile; ^
$ftp.Credentials = New-Object System.Net.NetworkCredential('%FTP_USER%', '%FTP_PASS%'); ^
$ftp.UsePassive = $true; ^
$ftp.UseBinary = $true; ^
$content = [System.IO.File]::ReadAllBytes('%PROJECT_DIR%\backend\thesis_workspace.php'); ^
$ftp.ContentLength = $content.Length; ^
try { ^
  $stream = $ftp.GetRequestStream(); ^
  $stream.Write($content, 0, $content.Length); ^
  $stream.Close(); ^
  $response = $ftp.GetResponse(); ^
  Write-Host '  -> SUCCESS: Uploaded thesis_workspace.php (' ([math]::Round($content.Length / 1kb)) 'KB)' -ForegroundColor Green; ^
} catch { ^
  Write-Host '  -> FAILED: ' $_.Exception.Message -ForegroundColor Red; ^
  exit 1; ^
}

if %ERRORLEVEL% NEQ 0 (
  echo.
  echo FAILED! Check the error above.
  pause
  exit /b 1
)

echo.
echo ============================================
echo  DEPLOYMENT COMPLETE!
echo ============================================
echo.
echo Files uploaded to: https://medigyaan.xyz/Neurons/
echo  - thesis_workspace.php
echo  - thesis_chapter_generator.php
echo.
echo Test: https://medigyaan.xyz/Neurons/thesis_workspace.php
echo.
pause
