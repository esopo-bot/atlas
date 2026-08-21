# Onde escrever cada coisa

Antes de criar arquivo, ache a pasta certa aqui. O erro que esta página
evita é o mais caro do repositório: escrever no lugar errado, o texto não
chegar em quem precisava, e ninguém perceber.

A regra que resolve quase tudo: **quem vai ler decide onde mora.** Se quem
lê é gente, é página. Se quem lê é instrumento, é dado. Se só serve à sua
máquina, fica fora do git.

## As pastas, uma linha cada

| Pasta | O que mora ali | Viaja para quem instala? |
| --- | --- | --- |
| `conhecimento/` | página que gente lê | sim |
| `.agents/` | instrumentos (Python) e as skills, que são a fonte | sim |
| `.claude/` | o que o Claude Code lê: ganchos, subagentes, cópia das skills | sim |
| `nucleo/` | os dados que instrumento lê (JSON) | sim |
| `modulos/` | peça opcional, que só chega para quem pedir pelo nome | não |
| `execucoes/` | roteiros do executor; o resultado de cada rodada fica fora do git | os roteiros nomeados, sim |
| `tmp/` | rascunho. Apagar não perde nada | não |

Na raiz ficam as instruções (`AGENTS.md`, `CLAUDE.md`, `README.md`) e os
instrumentos que agem sobre o repositório inteiro: `montar.py` instala a
camada, `publicar.py` leva o que é público para fora, `verificacoes.py` é a
porta única das verificações e `verificar-agentes.py` é a mais larga delas.

## Página ou dado?

Esta é a decisão que mais erra, e a regra 14 é quem manda.

- **Dado** é o que instrumento consome: um fato por chave, sem prosa em
  volta. Mora em `nucleo/*.json`. Exemplo: as regras da camada nascem em
  `nucleo/regras.json`.
- **Página** é o que uma pessoa lê para entender. Mora em `conhecimento/`.

Quando o mesmo fato interessa aos dois, ele nasce como dado e a página é
**gerada** a partir dele — nunca escrita à mão em dois lugares. É o que
acontece com `conhecimento/regras-da-camada.md`: editar essa página é
trabalho perdido, porque a próxima sincronização a reescreve.

Depois de mexer em página, skill, módulo ou `nucleo/`, rode:

```bash
python montar.py --sincronizar
```

## Fonte e cópia: edite sempre a fonte

Três pares neste repositório parecem duplicados e não são. Em cada um há uma
fonte e uma cópia gerada; editar a cópia é trabalho que a próxima
sincronização apaga.

| Fonte (edite aqui) | Cópia (gerada) |
| --- | --- |
| `.agents/skills/` | `.claude/skills/` |
| `modulos/<nome>/` | os arquivos correspondentes na raiz |
| `nucleo/regras.json` | `conhecimento/regras-da-camada.md` e o `AGENTS.md` |

A cópia das skills **entra no git de propósito**: sessão que roda na nuvem
só enxerga o que está commitado.

## Página nova precisa de quem a leia

Uma página que nenhuma outra cita é órfã: ela cobra contexto de toda sessão
e não entrega a nenhuma. Por isso a verificação da camada reprova página sem
link de entrada. Ao criar uma, cite-a de algum texto que já é lido — e, se
não houver de onde citar, provavelmente ela não devia existir.

## O que nunca entra no git

Fora do git ficam a configuração da sua máquina, o resultado das execuções e
o rascunho. Duas linhas que valem por todas:

- **Segredo não entra em git nenhum.** Em texto rastreado vai
  `${VARIAVEL}`, nunca o valor. Vale para repositório privado também.
- **O que nomeia você, sua empresa ou seus outros projetos não viaja.** É o
  que separa a camada — genérica — do seu caso.

O que a sessão precisa e não está no git se declara por nome em
`nucleo/ambiente.json` e se verifica por instrumento. O porquê e a receita
de repor estão em [o estado que não viaja](estado-que-nao-viaja.md).
