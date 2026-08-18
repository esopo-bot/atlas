# O estado que não viaja

O agente depende de estado em quatro territórios; só o 1 viaja com o git —
e a perda na mudança de pasta, disco ou máquina é silenciosa.

## Os quatro territórios

| # | Território | Exemplos | Sobrevive à mudança? |
| --- | --- | --- | --- |
| 1 | Versionado no repositório | páginas, skills, ganchos, `.mcp.json` com `${VARIAVEL}` | **sim** |
| 2 | No repositório, fora do git | configuração local, notas, credenciais | só se a pasta for copiada inteira |
| 3 | Estado da ferramenta, chaveado pelo caminho absoluto | histórico, memória do agente, confiança, aprovações | **não** — vira órfão |
| 4 | Perfil do sistema operacional | variáveis, perfis de CLI, keyring, agendamentos | **não** — fica na máquina velha |

O território 4 falha até sem mudar de máquina: processo nascido de outro
pai (ícone, serviço, agendador) não herda o perfil do shell — o canal que a
sessão gráfica lê está em [MCP](mcp.md).

## A regra de bolso

- O que vale amanhã mora no território 1 — página, nunca só memória de
  ferramenta. O território 3 é cache: re-aprove sem drama, não construa
  nada que dependa de ele sobreviver.
- O que a sessão precisa e não está no git se declara por nome e se confere
  por instrumento — é o `conferir-ambiente.py`.
- O resto se assume perdido a cada mudança.

## A declaração: `nucleo/ambiente.json`

**Seu** — a atualização nunca o reescreve. Uma lista por tipo; valor solto
vale por lista de um:

```json
{
  "receita": "conhecimento/notas/maquina-nova.md",
  "comando": ["git", "python3"],
  "pasta": ["~/.config/ferramenta-x"],
  "arquivo": ["scripts/preparar.sh"],
  "variavel": ["FERRAMENTA_X_TOKEN"]
}
```

- `receita` — a página da casa que ensina a repor; é o endereço que o aviso
  do gancho aponta.
- `comando` no PATH; `pasta`/`arquivo` existem no disco (`~` vale);
  `variavel` existe no ambiente. Nomes e existência, nunca valores.
- As `${VARIAVEL}` do `.mcp.json` não precisam ser declaradas — o gancho as
  extrai sozinho; as com padrão (`${VAR:-valor}`) ficam de fora.

O gancho roda na abertura, só avisa e cala quando está tudo lá:
`python .claude/hooks/conferir-ambiente.py --testar`.

## A página de máquina nova

- Cada linha com instrumento: "instale X" vem com o comando que prova.
- A fronteira da credencial: instalar é da sessão; configurar segredo é do
  dono.
- O caminho de mudança inteiro:
  [mudar de máquina](mudar-de-maquina.md).
