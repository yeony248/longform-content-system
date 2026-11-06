param([string]$Dir, [string]$Out)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, [Type]$t) { $task = $asTaskGeneric.MakeGenericMethod($t).Invoke($null, @($op)); $task.Wait(-1) | Out-Null; $task.Result }
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]
$lang = New-Object Windows.Globalization.Language 'ko'
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
$rows = New-Object System.Collections.Generic.List[string]
foreach ($f in Get-ChildItem $Dir -Filter *.png) {
  $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($f.FullName)) ([Windows.Storage.StorageFile])
  $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
  $dec = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
  $bmp = Await ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
  $res = Await ($engine.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
  foreach ($line in $res.Lines) {
    $t = ($line.Words | ForEach-Object { $_.Text }) -join ''
    if ($t.Length -gt 0) {
      $xs = $line.Words | ForEach-Object { $_.BoundingRect }
      $x1 = ($xs | Measure-Object X -Minimum).Minimum; $y1 = ($xs | Measure-Object Y -Minimum).Minimum
      $x2 = ($xs | ForEach-Object { $_.X + $_.Width } | Measure-Object -Maximum).Maximum
      $y2 = ($xs | ForEach-Object { $_.Y + $_.Height } | Measure-Object -Maximum).Maximum
      $rows.Add("$($f.Name)`t$([int]$x1)`t$([int]$y1)`t$([int]$x2)`t$([int]$y2)`t$t")
    }
  }
  $stream.Dispose()
}
[System.IO.File]::WriteAllLines($Out, $rows, (New-Object System.Text.UTF8Encoding $false))
