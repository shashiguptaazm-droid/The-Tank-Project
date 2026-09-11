$lines = [System.IO.File]::ReadAllLines('C:\Users\Shash\AndroidStudioProjects\EduLabsRTM\backend\thesis_workspace.php')
$line = $lines[3888]  # 0-indexed, so line 3889 is index 3888
$bytes = [System.Text.Encoding]::UTF8.GetBytes($line)
$hex = ($bytes | ForEach-Object { $_.ToString('X2') }) -join ' '
Write-Host "Line 3889 content:"
Write-Host "  Text: [$line]"
Write-Host "  Length: $($line.Length) chars"
Write-Host "  Hex: $hex"
Write-Host "  First char code: $([int][char]$line[0])"
Write-Host "  First 20 chars visible: '$($line.Substring(0, [Math]::Min(20, $line.Length)))'"
