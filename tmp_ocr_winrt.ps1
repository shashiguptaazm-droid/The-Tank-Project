$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime

# Load WinRT types
[Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.Streams.RandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime] | Out-Null

# Async helper
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if ($null -eq $engine) {
    Write-Error "No OCR language pack available"
    exit 1
}
Write-Host "OCR engine: $($engine.RecognizerLanguage.DisplayName)"

$imgDir = 'C:\Users\Shash\AndroidStudioProjects\MediGyaan\tmp_pptx_imgs'
$outFile = 'C:\Users\Shash\AndroidStudioProjects\MediGyaan\tmp_pptx_ocr.txt'
$sb = New-Object System.Text.StringBuilder

$files = Get-ChildItem -Path $imgDir -File | Sort-Object { [int]([regex]::Match($_.BaseName, '\d+').Value) }
foreach ($f in $files) {
    $sf = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($f.FullName)) ([Windows.Storage.StorageFile])
    $stream = Await ($sf.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    $null = $sb.AppendLine("")
    $null = $sb.AppendLine("=" * 70)
    $null = $sb.AppendLine("### $($f.BaseName)")
    $null = $sb.AppendLine("=" * 70)
    foreach ($line in $result.Lines) {
        $null = $sb.AppendLine($line.Text)
    }
    Write-Host "OCR done: $($f.Name)  ($($result.Lines.Count) lines)"
}

[System.IO.File]::WriteAllText($outFile, $sb.ToString(), [System.Text.Encoding]::UTF8)
Write-Host "Wrote $outFile"