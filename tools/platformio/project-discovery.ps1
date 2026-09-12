Set-StrictMode -Version Latest

function Get-RepositoryRelativePath {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$RepositoryRoot,
        [Parameter(Mandatory)][string]$Path
    )

    $rootUri = [Uri]::new(($RepositoryRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar))
    $pathUri = [Uri]::new(($Path.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar))
    return [Uri]::UnescapeDataString($rootUri.MakeRelativeUri($pathUri).ToString()).TrimEnd('/').Replace('\', '/')
}

function Get-PlatformIOProjects {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$RepositoryRoot)

    $root = Join-Path $RepositoryRoot 'projects'
    $items = @()
    if (Test-Path -LiteralPath $root) {
        $items = @(Get-ChildItem -LiteralPath $root -Filter 'platformio.ini' -File -Recurse |
            Where-Object { $_.FullName -notmatch '[\\/](archive|templates|node_modules|\.pio)[\\/]' })
    }

    return @($items | ForEach-Object {
        [PSCustomObject]@{
            Id = Get-RepositoryRelativePath -RepositoryRoot $RepositoryRoot -Path $_.Directory.FullName
            Directory = $_.Directory.FullName
            ConfigFile = $_.FullName
        }
    } | Sort-Object Id -Unique)
}
