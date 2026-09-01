# Roteiros que viajam com a camada

Os roteiros desta pasta são **da camada e entram no git**: o `.gitignore` ao
lado ignora tudo e libera por nome. O que a liberação não nomeia é pessoal
e fica fora — vale aqui no módulo e na `execucoes/` de quem instala.

Roteiro que mora aqui é **da camada**: não sabe nada de ninguém, tira todo
endereço da configuração, e serve a qualquer repositório que instale o
módulo. Troque a configuração e o mesmo roteiro serve outro lugar — é esse o
teste de que ele é mecanismo, e não o processo de alguém.

| Roteiro | O que faz | A página |
| --- | --- | --- |
| `catalogador.json` | reorganiza a camada de conhecimento e as anotações | `catalogador.md` |
| `entrega.json` | exemplo de trabalho que termina em pedido de revisão | `entrega.md` |
| `revisar-a-camada.json` | revisão periódica da camada, pela execução | `revisar-a-camada.md` |
| `mexida-em-vizinho.json` | trabalha uma issue dentro de outro repositório do workspace | `mexida-em-vizinho.md` |

O `.gitignore` ao lado ignora tudo e **libera por nome**, um roteiro por
linha — nunca `!*.json`, que reabriria a pasta e deixaria roteiro local
vazar sem ninguém ver.

## A receita do disparo, em linhas copiáveis

Cada rodada nova re-pagava os mesmos pedágios por seguir prosa em vez de
linha. Aqui estão as linhas, na ordem. Troque `<n>` pelo número da issue e
`<assunto>` pelo assunto em kebab.

**1. O roteiro local.** Copie o roteiro nomeado; não edite o original.
A chave `bloco` é opcional e recorta o ESCOPO: com ela, a verificação cobra
só os `- [ ]` da seção `## Bloco N` do corpo; sem ela, cobra a issue inteira.
Bloco que o corpo não tem mata a execução com erro de uso — silêncio seria
pior.
A chave `tempo-limite-da-prova` também é opcional e vale para a rodada
inteira: é o teto, em segundos, de cada prova re-executada na verificação.
Sem ela o teto é o de sempre, 60 s. Declare-a quando a rodada tem prova
reconhecidamente demorada — suíte grande, auditor sobre uma execução
inteira. Prova avulsa que é lenta sozinha declara o teto dela no próprio
item do provado, com `"tempo-limite"`, e não precisa da chave do roteiro.

```bash
python3 -c "
import json
r = json.load(open('execucoes/entrega.json'))
json.dump({'auditoria': True, 'issue': <n>, **r},
          open('execucoes/roteiro-issue-<n>.json', 'w'),
          ensure_ascii=False, indent=2)"
```

**2. A árvore descartável.** Clone local, nunca worktree: o clone nasce com
`origin` apontando para o repositório daqui, e é isso que salva a entrega
quando o remoto de verdade não está disponível.

```bash
git clone --no-hardlinks . /tmp/issue-<n>
mkdir -p /tmp/issue-<n>/nucleo
cp nucleo/executor.json /tmp/issue-<n>/nucleo/
cp .mcp.json /tmp/issue-<n>/ 2>/dev/null || true
cp .git/info/exclude /tmp/issue-<n>/.git/info/exclude
```

A configuração vai para `nucleo/` DA ÁRVORE — é lá que o executor a lê.
Copiada para a raiz dela, o disparo recusa e a rodada perde o turno.

O `.git/info/exclude` **não viaja no clone** — o git o deixa para trás, e
por isso o arquivo que só ele esconde reaparece solto na árvore da
execução. Solto, ele é varrido para dentro do commit pelo `git add -A` e
conta como sujeira para a cerca da regra 16. A linha do `cp` fecha os dois
de uma vez: o que a origem escondia continua escondido na árvore
descartável.

**3. O ensaio, antes de gastar sessão.** Mesmo comando, troca a palavra.

```bash
ISSUE=<n> ASSUNTO=<assunto> \
python3 .agents/encadeador/encadeador.py ensaio \
  --roteiro execucoes/roteiro-issue-<n>.json \
  --trabalho issue-<n> \
  --dir execucoes/evidencias \
  --cwd /tmp/issue-<n>
```

**4. O disparo, desacoplado do terminal.**

```bash
ISSUE=<n> ASSUNTO=<assunto> \
nohup python3 .agents/encadeador/encadeador.py executar \
  --roteiro execucoes/roteiro-issue-<n>.json \
  --trabalho issue-<n> \
  --dir execucoes/evidencias \
  --cwd /tmp/issue-<n> \
  > execucoes/evidencias/issue-<n>.log 2>&1 &
```

**5. A retomada, também desacoplada.** Mesma linha, com `--retomar` no fim.

**6. A auditoria à mão, antes de aprovar.** O auditor é OUTRO módulo —
instale-o com `--modulo auditor` se ainda não tiver. Sem ele, pule para o
`touch`: a aprovação é sua, com ou sem auditor.

```bash
python3 .agents/auditor/auditor.py execucoes/evidencias/issue-<n> \
  --cwd /tmp/issue-<n>
touch /tmp/issue-<n>/aprovacoes/entrega.ok
```

### Os quatro pedágios já pagos

- **O disparo sai da árvore intocada, e só o `--cwd` é editado.** Execução
  que mexe nos instrumentos e roda de dentro da árvore que muda derruba o
  próprio motor no meio.
- **`ISSUE` e `ASSUNTO` vão no ambiente do disparo.** Sem eles a branch de
  trabalho nasce com o nome errado, e a etapa seguinte para.
- **`--dir` resolve contra a árvore de onde o motor roda**, não contra o
  `--cwd`, e por isso vai explícito: sem ele quem for reler as evidências
  procura numa pasta vazia.
- **`aguardando-resposta` quer dizer processo MORTO.** Tocar o arquivo de
  aprovação sozinho não continua nada — quem continua é `--retomar`.

## Onde mora o SEU roteiro

Na `execucoes/` da raiz do seu repositório. Lá o conteúdo não entra no git,
de propósito: roteiro de trabalho cita o caminho da sua máquina, o nome dos
seus outros repositórios, o seu caso. Nada disso viaja.

Quando um roteiro seu deixar de citar o seu caso e passar a servir qualquer
repositório, ele é candidato a mudar para cá — e aí precisa da linha no
`.gitignore` e da página ao lado.
