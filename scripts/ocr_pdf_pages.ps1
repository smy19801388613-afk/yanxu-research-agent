param([Parameter(Mandatory=$true)][string]$ManifestPath,[Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.Streams.IRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.SoftwareBitmap,Windows.Graphics.Imaging,ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrResult,Windows.Foundation,ContentType=WindowsRuntime] | Out-Null
[Windows.Globalization.Language,Windows.Globalization,ContentType=WindowsRuntime] | Out-Null
$asyncMethod=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
function Wait-Result($Operation,[Type]$ResultType) {
    $pending=$asyncMethod.MakeGenericMethod($ResultType).Invoke($null,@($Operation))
    $pending.Wait()
    return $pending.Result
}
$recognizer=[Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('zh-Hans-CN'))
if (-not $recognizer) { throw 'Chinese Windows OCR language pack is unavailable' }
$manifest=Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$results=@()
foreach ($entry in $manifest) {
    $sourceFile=Wait-Result ([Windows.Storage.StorageFile]::GetFileFromPathAsync([string]$entry.path)) ([Windows.Storage.StorageFile])
    $stream=Wait-Result ($sourceFile.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $bitmap=$null
    try {
        $decoder=Wait-Result ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap=Wait-Result ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $recognized=Wait-Result ($recognizer.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        $words=@()
        foreach ($line in $recognized.Lines) {
            foreach ($word in $line.Words) {
                $box=$word.BoundingRect
                $words+=@{text=$word.Text;x=$box.X;y=$box.Y;w=$box.Width;h=$box.Height}
            }
        }
        $results+=@{page=$entry.page;words=$words}
    } finally {
        if ($bitmap) { $bitmap.Dispose() }
        $stream.Dispose()
    }
}
ConvertTo-Json -InputObject @($results) -Depth 6 -Compress | Set-Content -LiteralPath $OutputPath -Encoding UTF8
