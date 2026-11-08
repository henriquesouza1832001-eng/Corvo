# Ligar o CORVO ao Turso (comando a comando)

Banco já criado: `libsql://corvo-henriquesouza1832001-eng.aws-sa-east-1.turso.io`
Limites do plano grátis: 5 GB, 500 milhões de leituras e 10 milhões de escritas por mês. O CORVO usa um teto de 300 mil escritas por dia (`DAILY_WRITE_LIMIT`).

## 1. Instalar a CLI do Turso (uma vez)
No Windows, pelo WSL ou Git Bash: `curl -sSfL https://get.tur.so/install.sh | bash` e feche e abra o terminal. Sem a CLI, use o painel web (passo 2b).

## 2. Gerar o token
a) Pela CLI:
```
turso auth login
turso db tokens create corvo
```
b) Pelo painel: turso.tech > banco `corvo` > Generate Token. Copie o valor (começa com `ey...`).

## 3. Gravar os segredos no Worker (o token não passa pelo chat)
```
cd C:\projetos\Pulso\apps\worker
npx wrangler secret put TURSO_URL
```
Cole: `libsql://corvo-henriquesouza1832001-eng.aws-sa-east-1.turso.io`
```
npx wrangler secret put TURSO_TOKEN
```
Cole o token. Confirme com `npx wrangler secret list` (devem aparecer INGEST_TOKEN, TURSO_URL e TURSO_TOKEN).

## 4. Criar as tabelas no Turso (migrations 0001 a 0008)
No PowerShell, na raiz do projeto:
```
cd C:\projetos\Pulso
$env:TURSO_URL = "libsql://corvo-henriquesouza1832001-eng.aws-sa-east-1.turso.io"
$env:TURSO_TOKEN = "COLE_O_TOKEN"
py engine/scripts/turso_migrate.py
```
O script aplica as migrations de `database/migrations` e pula as já aplicadas. Termina com erro se algo não bater. (Não passe nenhum arquivo de dump: não há dados para importar.)

Conferir: `turso db shell corvo "SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1"` deve listar `corvo_news`, `corvo_gate_stats`, `corvo_forecasts` e `write_budget`.

## 5. Publicar o Worker já usando o Turso
```
cd C:\projetos\Pulso\apps\worker
npx wrangler deploy
```
O `wrangler.jsonc` já tem `DB_BACKEND="turso"` e `DAILY_WRITE_LIMIT="300000"`.

## 6. Testar
```
curl https://corvo-api.henriquesouza.workers.dev/api/corvo/feed
```
Deve responder `{"generated_at":...,"news":[],...}` sem erro. Para confirmar que o Turso está em uso, rode o passo 7 e depois `turso db shell corvo "SELECT COUNT(*) FROM corvo_news"`.

## 7. Primeira coleta de verdade (na sua máquina, só para testar)
```
cd C:\projetos\Pulso\engine
py -m corvo_engine.collect --once --dry-run
```
Mostra o que o portão decidiu sem enviar nada. Para enviar de fato (precisa do token de ingestão que está em `deploy/oracle/.env`):
```
$env:CORVO_API_URL = "https://corvo-api.henriquesouza.workers.dev"
$env:CORVO_INGEST_TOKEN = "valor de CORVO_INGEST_TOKEN em deploy/oracle/.env"
py -m corvo_engine.collect --once
```
Abra o painel: o selo muda de DEMONSTRAÇÃO para AO VIVO.

## 8. Depois que o Turso estiver funcionando
Peça para remover o D1 e o KV de reserva do `wrangler.jsonc` (o Worker volta ao D1 se os segredos do Turso estiverem ausentes).

## Quando o CORVO rodar no Oracle
Em `deploy/oracle/.env` ficam só `CORVO_API_URL` e `CORVO_INGEST_TOKEN`. O Oracle fala com a API do Cloudflare; **o token do Turso fica só no Worker**, nunca no Oracle nem no Git.
