# O estado que não viaja

Mudou o repositório de pasta, de disco ou de máquina e "tudo parou": o
agente esquece credencial, servidor MCP some, receita que funcionava morre.
Nada disso é mistério. O agente depende de estado em **quatro territórios**
— e só um deles viaja com o repositório.

## Os quatro territórios

| # | Território | Exemplos | Sobrevive à mudança? |
| --- | --- | --- | --- |
| 1 | Versionado no repositório | páginas, skills, ganchos, `.mcp.json` com `${VARIAVEL}` | **sim** |
| 2 | No repositório, fora do git | configuração local, notas pessoais, credenciais | só se a pasta for copiada inteira |
| 3 | Estado da ferramenta, chaveado pelo caminho absoluto | histórico de sessões, memória do agente, confiança, aprovações | **não** — vira órfão no caminho velho |
| 4 | Perfil do sistema operacional | variáveis de ambiente, perfis de CLI, keyring, agendamentos | **não** — fica na máquina velha |

Medido numa migração real de disco: as páginas e o `.mcp.json` chegaram
inteiros (território 1); as sessões antigas viraram órfãs numa pasta com o
nome do caminho velho (território 3); e as variáveis que os servidores MCP
esperavam sumiram junto com o perfil de CLI (território 4). O sintoma, nos
três casos, foi o mesmo: **silêncio**. Nada avisou na hora — cada peça
parou dias depois, com cara de defeito novo.

E o território 4 falha **sem mudar de máquina**: processo nascido de outro
pai — aplicativo aberto pelo ícone, serviço, agendador — não herda o que o
perfil do shell exporta. Mesmo disco, mesmo arquivo de variáveis, e a sessão
sem o que precisa. A lição inteira — o canal que a sessão gráfica lê, e por
que o publicador escreve nele — está em [MCP](mcp.md).

## A regra de bolso

- **O que vale amanhã mora no território 1.** Lição, receita e decisão se
  escrevem em página do repositório — nunca só na memória da ferramenta.
  O território 3 é cache: útil enquanto dura, descartável sem aviso.
- **O que a sessão precisa e não está no git se declara por nome** — nome
  de variável, de comando, de pasta — **e se confere por instrumento.**
  É o trabalho do gancho `conferir-ambiente.py`, abaixo.
- **O resto se assume perdido** a cada mudança de caminho ou de máquina.
  Confiança, aprovação e histórico se refazem; não vale carregá-los.

## A declaração: `ambiente.txt`

Um arquivo na raiz do workspace, **seu** — a atualização da camada nunca o
reescreve. Uma exigência por linha; `#` comenta:

```text
receita conhecimento/notas/maquina-nova.md
comando git
pasta ~/.config/ferramenta-x
arquivo scripts/preparar.sh
variavel FERRAMENTA_X_TOKEN
```

- `receita` — a página da casa que ensina a repor o que faltar. É o
  endereço que o aviso do gancho aponta.
- `comando` — precisa existir no PATH.
- `pasta` / `arquivo` — precisam existir no disco (`~` vale). O gancho olha
  a existência, nunca o conteúdo.
- `variavel` — precisa existir no ambiente. Só o nome é conferido; o valor
  nunca aparece.

As variáveis `${VARIAVEL}` do `.mcp.json` **não precisam ser declaradas**:
o gancho as extrai sozinho da declaração de MCP. As que têm padrão
(`${VARIAVEL:-valor}`) ficam de fora — o padrão cobre a ausência.

## O gancho que confere

O `conferir-ambiente.py` roda na abertura da sessão, **só avisa e cala
quando está tudo lá** — aviso que aparece sempre ensina a ignorar aviso.
Falta vira uma linha com o nome e o endereço da receita, na primeira sessão
da máquina nova — não no meio do incidente, que é a pior hora. Sem
`ambiente.txt` e sem `.mcp.json`, silêncio: casa que não declara nada não
tem o que conferir. Ele carrega o próprio teste:
`python .claude/hooks/conferir-ambiente.py --testar`.

## A página de máquina nova

A declaração diz **o que** falta; a receita diz **como** repor. Toda casa
merece uma página de máquina nova, com duas propriedades:

- **Cada linha com instrumento.** "Instale X" vem com o comando que prova —
  `which X` respondendo um caminho, o teste que passa, a listagem que
  aparece. Linha sem instrumento é impressão, e impressão passa em máquina
  quebrada.
- **A fronteira da credencial.** Instalar ferramenta é da sessão; configurar
  segredo é do dono. A página manda o dono rodar o `configure` da
  ferramenta — e nunca carrega valor nenhum.

É essa página que a primeira linha do `ambiente.txt` aponta. O caminho de
mudança inteiro — o antes, o depois e os sintomas de migração malfeita —
está no fluxo [mudar de máquina](../fluxos/mudar-de-maquina.md).

## O que não tem conserto — e a atitude certa

O território 3 é da ferramenta, não seu. Trate como cache: re-aprove sem
drama, deixe o órfão onde está (é histórico, não lixo) e não construa nada
que dependa de ele sobreviver. E a regra que impede o território 1 de ser
contaminado pelo 3 — configuração dentro do repositório nunca aponta
caminho absoluto — está na [página de MCP](mcp.md).
