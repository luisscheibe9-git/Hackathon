param(
  [string]$Port = 'COM4',
  [string]$Network = 'attinternet',
  [int]$Seconds = 20,
  [int]$Trials = 3,
  [string]$OutputDirectory = 'data',
  [switch]$Verify
)

$ErrorActionPreference = 'Stop'

function Get-Median($Values) {
  if ($Values.Count -eq 0) { return }
  $sorted = @($Values | Sort-Object)
  $middle = [int][Math]::Floor($sorted.Count / 2)
  if ($sorted.Count % 2) { return $sorted[$middle] }
  return ($sorted[$middle - 1] + $sorted[$middle]) / 2
}

$serial = [IO.Ports.SerialPort]::new($Port, 460800)
$ping = [Net.NetworkInformation.Ping]::new()
$pingTask = $null
$log = $null
try {
  $serial.Open()
  $serial.ReadTimeout = 60
  $serial.DtrEnable = $false
  $serial.RtsEnable = $true
  Start-Sleep -Milliseconds 150
  $serial.RtsEnable = $false
  Start-Sleep -Milliseconds 1250
  $serial.DiscardInBuffer()
  $profile = netsh wlan show profile "name=$Network" key=clear |
    Select-String '^\s*Key Content\s*:\s*(.+)$' | Select-Object -First 1
  if ($profile) {
    $serial.WriteLine($Network)
    $serial.WriteLine($profile.Matches[0].Groups[1].Value)
    $profile = $null
  } else {
    $password = Read-Host 'Wi-Fi password' -AsSecureString
    $serial.WriteLine($Network)
    $serial.WriteLine([Net.NetworkCredential]::new('', $password).Password)
    $password.Dispose()
  }

  $join = [Diagnostics.Stopwatch]::StartNew()
  $board = $null
  while ($join.Elapsed.TotalSeconds -lt 30) {
    try { $line = $serial.ReadLine().Trim() } catch [TimeoutException] { continue }
    if ($line -match '^JOINED ip=([\d.]+) .*channel=(\d+) rssi=(-?\d+)$') {
      $board = $Matches[1]
      Write-Host "ESP32 joined $Network on channel $($Matches[2]) at $($Matches[3]) dBm."
      break
    }
    if ($line -match '^JOIN_FAILED') { throw 'The ESP32 could not join the network.' }
  }
  if (-not $board) { throw "No Wi-Fi join message from $Port." }

  $stages = if ($Verify) { @('verify') } else { @('empty', 'walking', 'standing') }
  $instructions = @{
    empty = 'Walk out of the room after pressing Enter.'
    walking = 'Walk back and forth across the path between the router and ESP32.'
    standing = 'Stand still near the middle of that path.'
    verify = 'Checking that raw frames arrive.'
  }
  if (-not $Verify) {
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
    $path = Join-Path (Resolve-Path $OutputDirectory) ('csi-motion-{0:yyyyMMdd-HHmmss}.csv' -f (Get-Date))
    $log = [IO.StreamWriter]::new($path)
    $log.WriteLine('trial,stage,elapsed_ms,board_timestamp_us,rssi_dbm,first_word_invalid,lltf_hex')
  }

  for ($trial = 1; $trial -le $Trials; $trial++) {
    foreach ($stage in $stages) {
      if (-not $Verify) {
        Write-Host "`nTrial $trial/$Trials - $stage. $($instructions[$stage])"
        $null = Read-Host "Press Enter when ready. Sampling starts in 6 seconds"
        Start-Sleep -Seconds 6
      }
      $serial.DiscardInBuffer()
      $timer = [Diagnostics.Stopwatch]::StartNew()
      $nextPing = 0
      $rows = 0
      $previous = $null
      $differences = [Collections.Generic.List[double]]::new()
      Write-Host "Recording $stage for $Seconds seconds..."
      while ($timer.Elapsed.TotalSeconds -lt $Seconds) {
        if ($timer.ElapsedMilliseconds -ge $nextPing -and (!$pingTask -or $pingTask.IsCompleted)) {
          $pingTask = $ping.SendPingAsync($board, 140)
          $nextPing = $timer.ElapsedMilliseconds + 35
        }
        try { $line = $serial.ReadLine().Trim() } catch [TimeoutException] { continue }
        if ($line -match '^CSI_INIT_FAILED') { throw $line }
        if ($line -notmatch '^CSI,(\d+),(-?\d+),([01]),([0-9a-f]{256})$') { continue }
        $timestamp, $rssi, $invalid, $hex = $Matches[1], $Matches[2], $Matches[3], $Matches[4]
        $rows++
        if ($log) {
          $log.WriteLine("$trial,$stage,$($timer.ElapsedMilliseconds),$timestamp,$rssi,$invalid,$hex")
        }
        $bytes = [Convert]::FromHexString($hex)
        $amplitudes = for ($carrier = 2; $carrier -lt 64; $carrier++) {
          $i = [int]$bytes[$carrier * 2]
          $q = [int]$bytes[$carrier * 2 + 1]
          if ($i -gt 127) { $i -= 256 }
          if ($q -gt 127) { $q -= 256 }
          [Math]::Sqrt($i * $i + $q * $q)
        }
        $sum = ($amplitudes | Measure-Object -Sum).Sum
        if ($sum -le 0) { continue }
        if ($previous) {
          $difference = 0.0
          for ($j = 0; $j -lt $amplitudes.Count; $j++) {
            $difference += [Math]::Abs($amplitudes[$j] / $sum - $previous[$j])
          }
          $differences.Add($difference)
        }
        $previous = @($amplitudes | ForEach-Object { $_ / $sum })
      }
      if ($log) { $log.Flush() }
      if ($rows -eq 0) { throw "No raw CSI frames during $stage." }
      $score = Get-Median $differences
      Write-Host ('{0}: {1} frames ({2:F1}/s). Median CSI change: {3:F4}' -f $stage, $rows, ($rows / $Seconds), $score)
      if (-not $Verify) { [Console]::Beep(660, 180) }
    }
  }
  if ($log) { Write-Host "`nRaw CSI saved to $path" }
} finally {
  if ($log) { $log.Dispose() }
  $ping.Dispose()
  $serial.Dispose()
}
