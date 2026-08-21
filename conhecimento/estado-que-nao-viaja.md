# O estado que não viaja

Trocar de pasta, de disco ou de máquina apaga parte do que a sessão precisa
— e a perda é **silenciosa**: nada quebra na hora, você só descobre quando
um comando falha por um motivo que parece não ter relação.

Esta página é o endereço que o aviso da abertura da sessão aponta quando
falta alguma coisa. Se você chegou aqui por causa desse aviso, vá direto
para a última seção.

## Por que a perda é silenciosa

O agente depende de estado em quatro lugares diferentes, e só o primeiro
viaja junto com o repositório.

| Onde o estado mora | Exemplos | Sobrevive à mudança? |
| --- | --- | --- |
| Versionado no repositório | páginas, skills, ganchos, instrumentos | **sim** |
| Na pasta, mas fora do git | configuração local, notas, credenciais | só se a pasta for copiada inteira |
| Na ferramenta, endereçado pelo caminho absoluto | histórico, memória do agente, aprovações já dadas | **não** — vira órfão |
| No perfil do sistema operacional | variáveis de ambiente, agendamentos, chaveiro | **não** — fica na máquina velha |

O terceiro caso é o que mais engana. A ferramenta guarda o estado usando o
caminho da pasta como identidade: mover `~/trabalho/projeto` para
`~/código/projeto` faz a ferramenta tratar a pasta como um projeto novo,
sem histórico e sem as aprovações que você já tinha dado. Nada avisa.

O quarto falha até sem trocar de máquina: um processo que nasce de um ícone,
de um serviço ou de um agendador não herda as variáveis do seu terminal.

## A regra de bolso

- **O que vale amanhã vira arquivo no repositório.** Memória de ferramenta é
  cache: reaprovar é barato, mas não construa nada que dependa de ela durar.
- **O que a sessão precisa e não está no git se declara por nome.** Nome de
  arquivo ou de variável não é segredo; valor é. Declarar é o que permite
  verificar.
- **O resto se assume perdido** a cada mudança, e se repõe pela receita.

## A declaração: `nucleo/ambiente.json`

Este arquivo é **seu**: a atualização da camada nunca o reescreve. Ele lista
por nome o que a máquina precisa ter. Uma lista por tipo:

```json
{
  "receita": "conhecimento/estado-que-nao-viaja.md",
  "comando": ["git", "gh", "python3"],
  "pasta": ["~/.config/ferramenta-x"],
  "arquivo": ["scripts/preparar.sh"],
  "variavel": ["FERRAMENTA_X_TOKEN"]
}
```

- `receita` — a página que ensina a repor. É o endereço que o aviso mostra.
- `comando` — tem de existir no PATH.
- `pasta` e `arquivo` — têm de existir no disco; `~` vale.
- `variavel` — tem de estar definida. **Só o nome**: o gancho nunca lê nem
  imprime valor, e nunca sai procurando segredo.

O gancho `.claude/hooks/verificar-ambiente.py` verifica isso na abertura de
cada sessão. Ele **avisa e deixa passar** — nunca trava o trabalho. O que
ele verifica também alcança o `.mcp.json`: variável exigida ali sem valor no
ambiente vira aviso, porque um servidor MCP que sobe sem credencial falha
adiante, longe da causa.

## Quando o aviso aparecer

O aviso diz o que falta pelo nome e aponta a receita. Faça nesta ordem:

1. **Leia o que falta.** Comando ausente costuma ser instalação; variável
   ausente costuma ser perfil do sistema que ficou na máquina velha.
2. **Reponha pela receita** que o `ambiente.json` declara. Se a receita não
   existe mais, escrevê-la é o primeiro trabalho — sem ela o aviso vira
   ruído e ruído ensina gente a ignorar aviso.
3. **Confira que a lista ainda é verdade.** Item que ninguém usa mais sai da
   declaração; ferramenta nova que virou obrigatória entra.

O que este repositório espera de máquina nova mora nessa receita, e não na
memória de nenhuma sessão. Sobre onde cada coisa se escreve, veja
[onde escrever cada coisa](mapa-do-repositorio.md).
