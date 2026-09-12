Set-StrictMode -Version Latest

function Get-PlatformIOExecutable {
    [CmdletBinding()]
    param()

    $command = Get-Command pio -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $candidates = @(
        (Join-Path $HOME '.platformio\penv\Scripts\pio.exe'),
        (Join-Path $HOME '.platformio/penv/bin/pio')
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    throw 'PlatformIO Coreが見つかりません。VS CodeのPlatformIO IDEまたはPlatformIO Coreをインストールしてください。'
}
