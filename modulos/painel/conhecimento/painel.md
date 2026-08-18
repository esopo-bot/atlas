# O painel da esteira

Uma caixa de prompt, um botão e o estado da corrente — no navegador, sem
decorar caminho de script. Servidor de biblioteca padrão: nada para instalar.

O painel é **vidro, não motor**. Quem fala com o modelo é o
[encadeador](rodar-uma-corrente.md); quem diz o estado é o
`andamento` dele. O painel não inventa nada.

## Subir

```bash
python montar.py --modulo painel
python .agents/painel/painel.py --testar
git worktree add /tmp/esteira HEAD
python .agents/painel/painel.py --cwd /tmp/esteira
```

Abre em `http://127.0.0.1:4000`. Bandeiras: `--porta`, `--dir` (onde os
recibos caem).

**O `--cwd` é obrigatório e tem de ser worktree ou clone descartável.** A
etapa de sessão roda com permissões puladas; o painel recusa subir se o alvo
tiver mudança não commitada, que é o sinal barato de "esta árvore importa".

## O F5 do VS Code

O `.vscode/launch.json` é **seu** — a camada nunca o reescreve. Acrescente
esta configuração à lista que já existe:

```json
{
  "name": "Painel da esteira",
  "type": "debugpy",
  "request": "launch",
  "program": "${workspaceFolder}/.agents/painel/painel.py",
  "args": ["--cwd", "/tmp/esteira"],
  "console": "integratedTerminal"
}
```

Com a configuração da documentação já presente, o F5 passa a oferecer as duas
— e um `compounds` sobe as duas de uma vez, se você quiser o guia aberto ao
lado do painel.

## O que o disparo faz

Prompt livre não vira `claude -p` solto: vira **corrente de uma etapa mais a
conferência**, pelo mesmo caminho da corrente inteira.

| Peça | Quem escreve |
| --- | --- |
| o manifesto de uma etapa | o painel, em `<dir>/<trabalho>.manifesto.json` |
| o recibo | o encadeador, por código |
| a re-execução das provas | a etapa de conferência |
| o estado na tela | o `andamento`, sem intermediário |

O ganho de passar pelo mesmo caminho: um pedido solto também ganha recibo,
conferência e teto de ciclos. Sessão que "provou" o que não se re-executa
reprova aqui igual reprovaria na corrente.

**Corrente de várias etapas escolhe-se na lista.** O seletor junta duas pastas
(`--manifestos`, por padrão `correntes,tmp`): a versionada, das correntes
oficiais que viajam com a camada, e a de rascunho, que é sua. Nome repetido
fica com a oficial — rascunho não sequestra o nome de uma corrente da casa.
Manifesto colado na caixa de texto é recusado com a razão: ali o JSON inteiro
viraria o texto de uma sessão só.

## Duas casas ao mesmo tempo

Um painel por repositório, **uma porta por casa**. Assim os dois sobem juntos,
cada um enxergando só o seu alvo, e você mexe nos dois em paralelo.

| Casa | Porta | Worktree |
| --- | --- | --- |
| esta | 4000 | `/tmp/esteira-<nome>` |
| a irmã | 4001 | outro worktree |

**Uma corrente por vez em cada alvo.** O painel recusa o segundo disparo
enquanto o primeiro roda, e responde por quê. O motor já garantia um escritor
por trabalho; o que faltava era impedir dois trabalhos diferentes na mesma
árvore — duas sessões que pulam permissões, editando o mesmo disco, é corrida,
e o recibo de cada uma descreveria um disco que a outra já mudou.

**Manifesto versionado e manifesto seu não são a mesma coisa.** Rotina que
serve a qualquer casa viaja em `correntes/`. Rotina de desenvolvedor — a que
cita o caminho da sua máquina, o nome do seu outro repositório, o seu caso —
mora em `tmp/`, fora do git, e ali não há barreira nenhuma a respeitar: ela
nunca sai daqui.

## Os limites, confessados

- Não commita, não empurra, não publica, não apaga trabalho.
- Escuta só em `127.0.0.1`: é ferramenta de mesa, não serviço. Não há
  autenticação porque não há porta para fora — não a exponha.
- O diretório de recibos também recebe trilha de gancho, que não é corrente:
  lida como se fosse, ela vira "ciclo N de teto 1, parada" — alarme falso sobre
  coisa que funcionou. O painel marca essas pastas como **avulso** pela ausência
  de manifesto ao lado, e não opina sobre o estado delas.
- A leitura no meio de uma onda fotografa estado parcial — o mesmo limite do
  `andamento`, e pelo mesmo motivo.
