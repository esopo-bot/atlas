# O painel de controle do executor de roteiros

Uma caixa de prompt, um botão e o estado da execução — no navegador, sem
decorar caminho de script. Servidor de biblioteca padrão: nada para instalar.

O painel de controle é **vidro, não motor**. Quem fala com o modelo é o
encadeador; quem diz o estado é o
`andamento` dele. O painel de controle não inventa nada.

## Subir

```bash
python montar.py --modulo painel
python .agents/painel/painel.py --testar
git worktree add /tmp/executor HEAD
python .agents/painel/painel.py --cwd /tmp/executor
```

Abre em `http://127.0.0.1:4000`. Bandeiras: `--porta`, `--dir` (onde os
evidências caem).

**O `--cwd` é obrigatório e tem de ser worktree ou clone descartável.** A
etapa de sessão roda com permissões puladas; o painel de controle recusa
subir se o alvo tiver mudança não commitada, que é o sinal barato de "esta
árvore importa".

## O F5 do VS Code

O `.vscode/launch.json` é **seu** — a camada nunca o reescreve. Acrescente
esta configuração à lista que já existe:

```json
{
  "name": "Painel de controle do executor de roteiros",
  "type": "debugpy",
  "request": "launch",
  "program": "${workspaceFolder}/.agents/painel/painel.py",
  "args": ["--cwd", "/tmp/executor"],
  "console": "integratedTerminal"
}
```

Com a configuração da documentação já presente, o F5 passa a oferecer as duas
— e um `compounds` sobe as duas de uma vez, se você quiser o guia aberto ao
lado do painel de controle.

## O que o disparo faz

Prompt livre não vira `claude -p` solto: vira **execução de uma etapa mais a
verificação**, pelo mesmo caminho da execução inteira.

| Peça | Quem escreve |
| --- | --- |
| o roteiro de uma etapa | o painel de controle, em `<dir>/<trabalho>.roteiro.json` |
| a evidência | o encadeador, por código |
| a re-execução das provas | a etapa de verificação |
| o estado na tela | o `andamento`, sem intermediário |

O ganho de passar pelo mesmo caminho: um pedido solto também ganha evidência,
verificação e teto de ciclos. Sessão que "provou" o que não se re-executa
reprova aqui igual reprovaria na execução.

**Execução de várias etapas escolhe-se na lista.** O seletor junta duas pastas
(`--roteiros`, por padrão `execucoes,tmp`): a versionada, das execuções
oficiais que viajam com a camada, e a de rascunho, que é sua. Nome repetido
fica com a oficial — rascunho não sequestra o nome de uma execução do
repositório. Roteiro colado na caixa de texto é recusado com a razão: ali o
JSON inteiro viraria o texto de uma sessão só.

## Dois repositórios ao mesmo tempo

Um painel de controle por repositório, **uma porta para cada um**. Assim os
dois sobem juntos, cada um enxergando só o seu alvo, e você mexe nos dois em
paralelo.

| Repositório | Porta | Worktree |
| --- | --- | --- |
| este | 4000 | `/tmp/executor-<nome>` |
| o vizinho | 4001 | outro worktree |

**Uma execução por vez em cada alvo.** O painel de controle recusa o segundo
disparo enquanto o primeiro roda, e responde por quê. O motor já garantia um
escritor por trabalho; o que faltava era impedir dois trabalhos diferentes na
mesma árvore — duas sessões que pulam permissões, editando o mesmo disco, é
corrida, e a evidência de cada uma descreveria um disco que a outra já mudou.

**Roteiro versionado e roteiro seu não são a mesma coisa.** Rotina que serve a
qualquer repositório viaja em `execucoes/`. Rotina de desenvolvedor — a que
cita o caminho da sua máquina, o nome do seu outro repositório, o seu caso —
mora em `tmp/`, fora do git, e ali não há barreira nenhuma a respeitar: ela
nunca sai daqui.

## Os limites, confessados

- Não commita, não empurra, não publica, não apaga trabalho.
- Escuta só em `127.0.0.1`: é ferramenta de mesa, não serviço. Não há
  autenticação porque não há porta para fora — não a exponha.
- O diretório de evidências também recebe trilha de gancho, que não é execução:
  lida como se fosse, ela vira "ciclo N de teto 1, parada" — alarme falso sobre
  coisa que funcionou. O painel de controle marca essas pastas como
  **avulso** pela ausência de roteiro ao lado, e não opina sobre o estado
  delas.
- A leitura no meio de um estágio fotografa estado parcial — o mesmo limite do
  `andamento`, e pelo mesmo motivo.
