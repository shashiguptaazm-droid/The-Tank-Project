param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string[]]$Links,

    [string]$RpcUrl = "http://213.199.61.156:6800/jsonrpc",

    [string]$DownloadDir = "/downloads",

    [string]$RpcSecret = "",

    [string]$LinksFile = ""
)

function Invoke-Aria2Rpc {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Method,

        [Parameter(Mandatory = $true)]
        [object[]]$Params
    )

    $body = @{
        jsonrpc = "2.0"
        id      = "ariang-service"
        method  = $Method
        params  = $Params
    } | ConvertTo-Json -Depth 10

    Invoke-RestMethod -Method Post -Uri $RpcUrl -ContentType "application/json" -Body $body
}

function Normalize-Link {
    param([string]$Link)
    $value = ($Link | ForEach-Object { $_.Trim() })
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $null
    }
    return $value
}

$allLinks = New-Object System.Collections.Generic.List[string]

foreach ($link in $Links) {
    $normalized = Normalize-Link $link
    if ($null -ne $normalized) {
        $allLinks.Add($normalized)
    }
}

if ($LinksFile -and (Test-Path -LiteralPath $LinksFile)) {
    Get-Content -LiteralPath $LinksFile | ForEach-Object {
        $normalized = Normalize-Link $_
        if ($null -ne $normalized) {
            $allLinks.Add($normalized)
        }
    }
}

if ($allLinks.Count -eq 0) {
    throw "No usable links were provided."
}

foreach ($link in $allLinks) {
    $params = @()
    if ($RpcSecret) {
        $params += "token:$RpcSecret"
    }
    $params += @(
        @($link),
        @{ dir = $DownloadDir }
    )

    try {
        $result = Invoke-Aria2Rpc -Method "aria2.addUri" -Params $params
        if ($result.result) {
            Write-Host "added $link -> $($result.result)"
        } else {
            Write-Host "added $link"
        }
    } catch {
        Write-Host "failed $link -> $($_.Exception.Message)"
    }
}
