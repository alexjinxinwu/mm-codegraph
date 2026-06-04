# Configure global OpenSpec for Superspec + generate Claude Code skills/commands.
# 兼容 Windows PowerShell 5.1

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $ScriptDir "..")).Path
Set-Location $Root

# 无 BOM 的 UTF-8 写文件辅助函数（PS 5.1 的 Set-Content -Encoding UTF8 会带 BOM）
function Write-Utf8NoBom([string]$Path, [string]$Content) {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $Path))
    [System.IO.File]::WriteAllText($full, $Content, $utf8NoBom)
}

Write-Host "==> Configuring global OpenSpec (Superspec workflows)"
openspec config set profile custom
openspec config set delivery both

# 不依赖 jq，直接用 PowerShell 内置 JSON 处理改写 workflows
$ConfigPath = (openspec config path).Trim()
$json = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$json.workflows = @("propose","explore","new","continue","apply","ff","sync","archive","bulk-archive","verify","onboard")
$jsonOut = $json | ConvertTo-Json -Depth 100
Write-Utf8NoBom $ConfigPath $jsonOut
Write-Host "    Workflows: $(openspec config get workflows)"

Write-Host "==> Initializing OpenSpec for Claude Code"
openspec init --tools claude --profile custom --force

Write-Host "==> Writing project openspec/config.yaml"
$ConfigYaml = @'
schema: superspec

context: |
  Harness: OpenSpec (Superspec schema) + Superpowers skills in Claude Code.
'@
if (-not (Test-Path "openspec")) { New-Item -ItemType Directory -Path "openspec" | Out-Null }
Write-Utf8NoBom "openspec/config.yaml" $ConfigYaml

Write-Host "==> Refreshing Claude integration"
openspec update

Write-Host "==> Validating schemas"
openspec schemas
# 对应 `|| true`：忽略校验失败
try { openspec validate --specs 2>$null } catch { }

Write-Host ""
Write-Host "Done. Install Superpowers in Claude Code:"
Write-Host "  /plugin marketplace add obra/superpowers-marketplace"
Write-Host "  /plugin install superpowers@superpowers-marketplace"