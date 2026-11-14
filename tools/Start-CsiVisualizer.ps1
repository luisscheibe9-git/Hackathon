param(
  [string[]]$Ports = @('COM4', 'COM5'),
  [string]$Network = 'attinternet',
  [string]$Python = 'python',
  [switch]$Observatory,
  [switch]$Standalone,
  [string]$GatewayPort,
  [switch]$MotionModel
)

$ErrorActionPreference = 'Stop'
if ($GatewayPort) {
  $modelFlag = @(if ($MotionModel) { '--motion-model' })
  '' | & $Python (Join-Path $PSScriptRoot 'csi-visualizer.py') 'Stillpoint-CSI' $GatewayPort --observatory --gateway @modelFlag
  exit $LASTEXITCODE
}
if ($Standalone) {
  'stillpoint-demo' | & $Python (Join-Path $PSScriptRoot 'csi-visualizer.py') 'Stillpoint-CSI' @Ports --observatory --external-traffic
  exit $LASTEXITCODE
}
$profile = netsh wlan show profile "name=$Network" key=clear |
  Select-String '^\s*Key Content\s*:\s*(.+)$' | Select-Object -First 1
if ($profile) {
  $password = $profile.Matches[0].Groups[1].Value
} else {
  $secure = Read-Host 'Wi-Fi password' -AsSecureString
  $password = [Net.NetworkCredential]::new('', $secure).Password
  $secure.Dispose()
}
$flags = @(if ($Observatory) { '--observatory' })
$password | & $Python (Join-Path $PSScriptRoot 'csi-visualizer.py') $Network @Ports @flags
exit $LASTEXITCODE
