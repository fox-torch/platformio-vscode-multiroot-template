[CmdletBinding()]
param(
    [ValidateSet('menu', 'repair', 'import', 'repair-all')]
    [string]$Action = 'menu'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$maintenance = Join-Path $PSScriptRoot 'maintenance.py'
$logDir = Join-Path $repoRoot '.pio\maintenance'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logPath = Join-Path $logDir 'last.log'

function Get-PlatformIOPython {
    $candidates = @(
        (Join-Path $HOME '.platformio\penv\Scripts\python.exe'),
        (Join-Path $HOME '.platformio\penv\bin\python')
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    foreach ($name in @('python', 'python3')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { return $command.Source }
    }
    throw 'Python was not found. Install PlatformIO IDE first.'
}

function Select-Folder {
    param([string]$Description, [string]$InitialPath, [bool]$AllowCreate = $false)
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = $Description
    $dialog.ShowNewFolderButton = $AllowCreate
    if ($InitialPath -and (Test-Path -LiteralPath $InitialPath)) {
        $dialog.SelectedPath = $InitialPath
    }
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { return $null }
    return $dialog.SelectedPath
}

function Show-Message {
    param([string]$Text, [string]$Title, [string]$Icon = 'Information')
    [System.Windows.Forms.MessageBox]::Show(
        $Text, $Title, [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::$Icon
    ) | Out-Null
}
function Invoke-Maintenance {
    param([string[]]$Arguments, [string]$SuccessMessage)
    $python = Get-PlatformIOPython
    $output = @(& $python $maintenance --repo-root $repoRoot @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    $output | Set-Content -LiteralPath $logPath -Encoding UTF8
    if ($exitCode -eq 0) {
        Show-Message "$SuccessMessage`n`nLog: $logPath" 'PlatformIO Maintenance'
        return
    }
    $tail = ($output | Select-Object -Last 18) -join "`n"
    Show-Message "Operation failed.`n`n$tail`n`nLog: $logPath" 'PlatformIO Maintenance' 'Warning'
}

function Invoke-RepairGui {
    $project = Select-Folder 'Select a PlatformIO project to repair.' $repoRoot
    if (-not $project) { return }
    Invoke-Maintenance @('repair', $project) 'Repair completed.'
}

function Invoke-ImportGui {
    $source = Select-Folder 'Select an external PlatformIO project to import.' $HOME
    if (-not $source) { return }
    $defaultDestination = Join-Path $repoRoot 'projects'
    $destination = Select-Folder 'Select the destination parent under projects/.' $defaultDestination $true
    if (-not $destination) { return }
    Invoke-Maintenance @('import', $source, $destination) 'Import and validation completed.'
}
function Invoke-RepairAllGui {
    $answer = [System.Windows.Forms.MessageBox]::Show(
        'Rebuild every PlatformIO project from clean generated state?',
        'PlatformIO Repair All',
        [System.Windows.Forms.MessageBoxButtons]::YesNo,
        [System.Windows.Forms.MessageBoxIcon]::Question
    )
    if ($answer -eq [System.Windows.Forms.DialogResult]::Yes) {
        Invoke-Maintenance @('repair-all') 'Repair all completed.'
    }
}

function Show-MaintenanceMenu {
    $form = New-Object System.Windows.Forms.Form
    $form.Text = 'PlatformIO Maintenance'
    $form.Size = New-Object System.Drawing.Size(420, 220)
    $form.StartPosition = 'CenterScreen'
    $form.MaximizeBox = $false
    $form.FormBorderStyle = 'FixedDialog'

    $label = New-Object System.Windows.Forms.Label
    $label.Text = 'Use only for project recovery or importing an external PlatformIO project.'
    $label.AutoSize = $true
    $label.Location = New-Object System.Drawing.Point(20, 20)
    $form.Controls.Add($label)
    $repair = New-Object System.Windows.Forms.Button
    $repair.Text = 'Repair project'
    $repair.Size = New-Object System.Drawing.Size(170, 42)
    $repair.Location = New-Object System.Drawing.Point(20, 70)
    $repair.Add_Click({ $form.Close(); Invoke-RepairGui })
    $form.Controls.Add($repair)

    $import = New-Object System.Windows.Forms.Button
    $import.Text = 'Import project'
    $import.Size = New-Object System.Drawing.Size(170, 42)
    $import.Location = New-Object System.Drawing.Point(210, 70)
    $import.Add_Click({ $form.Close(); Invoke-ImportGui })
    $form.Controls.Add($import)

    $repairAll = New-Object System.Windows.Forms.Button
    $repairAll.Text = 'Repair all projects'
    $repairAll.Size = New-Object System.Drawing.Size(170, 36)
    $repairAll.Location = New-Object System.Drawing.Point(115, 130)
    $repairAll.Add_Click({ $form.Close(); Invoke-RepairAllGui })
    $form.Controls.Add($repairAll)
    [void]$form.ShowDialog()
}

switch ($Action) {
    'repair' { Invoke-RepairGui }
    'import' { Invoke-ImportGui }
    'repair-all' { Invoke-RepairAllGui }
    default { Show-MaintenanceMenu }
}
