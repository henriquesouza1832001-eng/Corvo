# git-crypt no CORVO

O repositório é **público**. O git-crypt permite guardar segredos **cifrados** dentro dele: no GitHub aparecem como bloco binário ilegível, e só quem tem a chave vê o texto. Serve para levar configuração sensível (por exemplo, o `.env` do Oracle) junto do código, sem expor nada.

## O que é cifrado (`.gitattributes`)
| Padrão | Uso |
|---|---|
| `secrets/**` | segredos de implantação (ex.: `secrets/oracle.env`) |
| `docs/private/**` | anotações que não devem ser públicas |
| `*.secret`, `*.secret.*` | qualquer arquivo de segredo avulso |

O `.gitattributes` em si **não** é cifrado. O arquivo `secrets/selftest.txt` é um autoteste fictício: se alguém o enxergar em texto puro no GitHub, a criptografia não está funcionando.

## Estado atual
- git-crypt iniciado neste computador (`git-crypt init`); a **chave** foi exportada para `C:\Users\Dell\corvo-gitcrypt.key`, **fora do repositório**.
- Verificado: o autoteste entra no repositório como bloco `GITCRYPT` (sem o texto).

## A chave (o que não pode acontecer)
- **Faça backup** de `corvo-gitcrypt.key` em lugar seguro (gerenciador de senhas ou pen drive). **Sem a chave, o conteúdo cifrado é irrecuperável.**
- **Nunca** commite a chave, nem a envie por e-mail ou chat. Ela já está fora do repositório e `*.key` é recusado pelo `scripts/gitcrypt_check.sh`.
- Quem tiver a chave lê tudo que está cifrado, inclusive o histórico daqui para a frente.

## Comandos do dia a dia
```
# conferir o que está cifrado e se algo vazou em texto puro
git-crypt status -e
sh scripts/gitcrypt_check.sh

# adicionar um segredo (o filtro cifra sozinho no commit)
copy deploy\oracle\.env secrets\oracle.env
git add secrets/oracle.env
sh scripts/gitcrypt_check.sh   # deve dizer ok
git commit -m "chore: add encrypted oracle env"
```

## Em outra máquina (servidor, colaborador)
```
git clone https://github.com/henriquesouza1832001-eng/Corvo.git
cd Corvo
git-crypt unlock /caminho/para/corvo-gitcrypt.key
```
Sem o `unlock`, os arquivos de `secrets/` aparecem como binário. O Oracle precisa de `git-crypt` instalado (`apt install git-crypt`) e da chave copiada por canal seguro (por exemplo `scp`).

## Compartilhar por GPG em vez de uma chave solta (opcional)
```
git-crypt add-gpg-user ID_DA_CHAVE_GPG_DA_PESSOA
```
Cada pessoa passa a usar a própria chave GPG com `git-crypt unlock`, e dá para revogar acesso removendo o usuário e rotacionando.

## Limites que você precisa conhecer
1. **O histórico não é reescrito.** O que já foi commitado em texto puro (antes do git-crypt) continua legível no histórico público. Se algum segredo já vazou, **troque o segredo**, não esconda.
2. O git-crypt cifra **conteúdo**, não nomes de arquivo nem tamanhos.
3. Não cifre arquivos que o GitHub Actions precisa ler: o Actions não tem a chave. Para o CI use **GitHub Secrets** (`CORVO_API_URL`, `CORVO_INGEST_TOKEN`).
4. Mudar `.gitattributes` não cifra retroativamente arquivos já versionados em texto puro.
5. O token do Worker e o do Turso **continuam fora do repositório**, nos segredos do Cloudflare (`wrangler secret put`). O git-crypt é para o que precisa viajar com o código.
