<#
  Coleta de corpus do CORVO em laço (teste a seco: NÃO envia nada à API).
  Rode numa janela do PowerShell que fique aberta durante a noite; ela independe de qualquer agente.

  Uso:   powershell -ExecutionPolicy Bypass -File scripts\corvo_corpus_loop.ps1 -Hours 6 -IntervalSeconds 600
  Saída: engine\data\corvo_corpus\corpus.jsonl (uma linha por item lido, com a decisão do portão)
         engine\data\corvo_corpus\precos.csv (preços de referência para o Munin conferir previsões; idempotente)
         engine\data\corvo_corpus\ciclos.log (resumo de cada ciclo)
  Parar: Ctrl+C. Mínimo educado com as fontes: 300 s entre ciclos (o coletor também impõe isso).
#>
param(
  [double]$Hours = 6,
  [int]$IntervalSeconds = 600
)

$ErrorActionPreference = "Continue"
if ($IntervalSeconds -lt 300) { $IntervalSeconds = 300 }
$engine = Join-Path (Split-Path -Parent $PSScriptRoot) "engine"
Set-Location $engine
$dir = Join-Path $engine "data\corvo_corpus"
New-Item -ItemType Directory -Force $dir | Out-Null
$corpus = Join-Path $dir "corpus.jsonl"
$log = Join-Path $dir "ciclos.log"
$fim = (Get-Date).AddHours($Hours)
$n = 0
Write-Host "CORVO corpus: ate $fim, um ciclo a cada $IntervalSeconds s. Ctrl+C para parar."
while ((Get-Date) -lt $fim) {
  $n++
  $t0 = Get-Date
  $env:PYTHONIOENCODING = "utf-8"
  $line = py -m corvo_engine.collect --once --dry-run --quiet --dump $corpus 2>&1 | Select-Object -Last 1
  "$((Get-Date).ToString('s')) ciclo $n $line" | Out-File -Append -Encoding utf8 $log
  $preco = py -m corvo_engine.collect.prices --out (Join-Path $dir "precos.csv") 2>&1 | Select-Object -Last 1
  "$((Get-Date).ToString('s')) precos $preco" | Out-File -Append -Encoding utf8 $log
  $total = 0
  if (Test-Path $corpus) { $total = (Get-Content $corpus | Measure-Object -Line).Lines }
  Write-Host ("ciclo {0} ok | linhas no corpus: {1}" -f $n, $total)
  $espera = $IntervalSeconds - ((Get-Date) - $t0).TotalSeconds
  if ($espera -gt 0) { Start-Sleep -Seconds ([int]$espera) }
}
Write-Host "Fim do laco: $n ciclos."
