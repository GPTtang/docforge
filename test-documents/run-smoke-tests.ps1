param(
    [string]$BaseUrl = 'http://localhost:8080',
    [string]$FixtureRoot = $PSScriptRoot,
    [int]$TimeoutSec = 300
)

$ErrorActionPreference = 'Continue'

$manifestPath = Join-Path $FixtureRoot 'manifest.csv'
if (-not (Test-Path $manifestPath)) {
    throw "Manifest not found: $manifestPath"
}

$manifest = Import-Csv $manifestPath

$reportDir = Join-Path $FixtureRoot 'reports'
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$reportPath = Join-Path $reportDir ("api-smoke-$stamp.csv")

$rows = @()

foreach ($item in $manifest) {
    $fullPath = Join-Path $FixtureRoot $item.file
    if (-not (Test-Path $fullPath)) {
        $rows += [PSCustomObject]@{
            file = $item.file
            endpoint = 'markdown'
            expected = $item.expected_markdown
            actual = 'missing'
            result = 'FAIL'
            http_status = ''
            duration_ms = 0
            output_length = 0
            message = 'fixture_missing'
        }
        $rows += [PSCustomObject]@{
            file = $item.file
            endpoint = 'json'
            expected = $item.expected_json
            actual = 'missing'
            result = 'FAIL'
            http_status = ''
            duration_ms = 0
            output_length = 0
            message = 'fixture_missing'
        }
        continue
    }

    foreach ($ep in @('markdown', 'json')) {
        $url = "$BaseUrl/api/convert/$ep"
        $expected = if ($ep -eq 'markdown') { $item.expected_markdown } else { $item.expected_json }

        $tmpBody = [System.IO.Path]::GetTempFileName()
        $started = Get-Date

        try {
            $httpCode = & curl.exe -sS --max-time $TimeoutSec -o $tmpBody -w "%{http_code}" -X POST -F "file=@$fullPath" $url
            $duration = [int]((Get-Date) - $started).TotalMilliseconds
            $body = Get-Content $tmpBody -Raw -ErrorAction SilentlyContinue

            $actual = 'fail'
            $outputLen = 0
            $message = ''

            if ($httpCode -eq '200') {
                try {
                    $obj = $body | ConvertFrom-Json
                    if ($obj.status -eq 'success') {
                        $actual = 'success'
                        if ($ep -eq 'markdown' -and $null -ne $obj.markdown) {
                            $outputLen = $obj.markdown.Length
                        }
                        if ($ep -eq 'json' -and $null -ne $obj.data) {
                            $outputLen = (ConvertTo-Json $obj.data -Depth 20).Length
                        }
                        $message = 'success'
                    } else {
                        $message = "status=$($obj.status)"
                    }
                } catch {
                    $message = 'invalid_json_response'
                }
            } else {
                $singleLine = ($body -replace "`r?`n", ' ')
                $message = if ([string]::IsNullOrWhiteSpace($singleLine)) { 'http_error' } else { $singleLine }
            }

            $result = if ($actual -eq $expected) { 'PASS' } else { 'FAIL' }

            $rows += [PSCustomObject]@{
                file = $item.file
                endpoint = $ep
                expected = $expected
                actual = $actual
                result = $result
                http_status = $httpCode
                duration_ms = $duration
                output_length = $outputLen
                message = $message
            }
        } catch {
            $duration = [int]((Get-Date) - $started).TotalMilliseconds
            $actual = 'fail'
            $result = if ($actual -eq $expected) { 'PASS' } else { 'FAIL' }

            $rows += [PSCustomObject]@{
                file = $item.file
                endpoint = $ep
                expected = $expected
                actual = $actual
                result = $result
                http_status = ''
                duration_ms = $duration
                output_length = 0
                message = $_.Exception.Message
            }
        } finally {
            Remove-Item $tmpBody -ErrorAction SilentlyContinue
        }
    }
}

$rows | Export-Csv -Path $reportPath -NoTypeInformation -Encoding UTF8

$passCount = ($rows | Where-Object { $_.result -eq 'PASS' }).Count
$totalCount = $rows.Count
$failCount = $totalCount - $passCount

Write-Output "Report: $reportPath"
Write-Output "Expectation Pass: $passCount / $totalCount"
Write-Output "Expectation Fail: $failCount"

if ($failCount -gt 0) {
    Write-Output ''
    Write-Output 'Unexpected Cases:'
    $rows | Where-Object { $_.result -eq 'FAIL' } |
        Select-Object file, endpoint, expected, actual, http_status, message |
        Format-Table -AutoSize | Out-String -Width 320 | Write-Output
}
