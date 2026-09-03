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
| `conhecimento/` | página que gente lê | sim, só `regras-da-camada.md` — a lista das regras gerada de `nucleo/regras.json`. As outras páginas ficam neste repositório: quem instala recebe regras, skills, instrumentos e ganchos, e a documentação da camada mora aqui |
| `conhecimento/projetos/` | a wiki dos repositórios vizinhos — um perfil por repositório, gerado pela skill `perfil-de-repositorio` | não: é conteúdo do workspace, fora do git |
| `.agents/` | instrumentos (Python), as skills (fonte) e os prompts de abertura em `.agents/prompts/` | os instrumentos e as skills, sim; dos prompts, o de verificação pós-atualização, o de abertura de projeto e o que prova que o agente lê a camada — o de abertura NA camada e o da auditoria externa ficam, porque só servem a quem melhora o atlas |
| `.claude/` | o que o Claude Code lê: ganchos, subagentes, cópia das skills e a regra por caminho do padrão de código, gerada da skill | sim |
| `nucleo/` | os dados que instrumento lê (JSON) | sim |
| `modulos/` | peça opcional, que só chega para quem pedir pelo nome | não |
| `execucoes/` | roteiros do executor, **cópia gerada** de `modulos/encadeador/execucoes/` — edite lá, nunca aqui; o resultado de cada rodada fica fora do git | só com `--modulo encadeador`: os roteiros nomeados chegam pelo módulo, não pela camada base |
| `tmp/` | rascunho. Apagar não perde nada | não |

Na raiz ficam as instruções (`AGENTS.md`, `CLAUDE.md`, `README.md`) e os
instrumentos que agem sobre o repositório inteiro. Destes, só o `montar.py`
— que instala a camada — viaja. Os outros três ficam neste repositório e
**não chegam a quem instala**: `publicar.py` leva o que é público para fora,
`verificacoes.py` é a porta única das verificações e `verificar-agentes.py`
é a mais larga delas.

Nem toda verificação protege quem instala. A rotina `camada` — a mais larga
— roda o `verificar-agentes.py`, que **não viaja**: consertar algo nela
protege este repositório e mais ninguém. Quem instalou a camada é protegido
pelo `.agents/camada/camada.py`, que viaja junto. O alcance de cada rotina
está declarado no catálogo do `verificacoes.py`, campo `alcance`: **fica no
atlas** ou **viaja com a camada**. No atlas, `python3 verificacoes.py --lista`
mostra a coluna; onde a camada foi instalada esse arquivo não existe, e o que
se tem é `python3 .agents/camada/camada.py medir provar`.

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

O depósito embutido no `montar.py` é a terceira cópia, e pesa pouco no git.
Medido em 01/09/2026 (#245): a história inteira dele são 5 MB de um clone de
7 MB, 13 KB por revisão, porque o diff é por linha e o pacote faz delta.
`.git` local muito acima disso é objeto solto sem `git gc`, não o instalador:
`git count-objects -vH` separa, `size` é o solto e `size-pack` o empacotado.

A metade que falta: **skill pessoal não entra aqui.** Skill que só serve a
você vai para as skills de usuário, em `~/.claude/skills/` — fora do
repositório, fora do git. Skill que entra em `.agents/skills/` é skill que
todo mundo que instalar a camada recebe, e passa a cobrar contexto de toda
sessão de todo mundo.

## Gancho novo se matricula em cinco pontos

Arquivo que precisa chegar em quem instala se matricula no `montar.py`. O
`--verificar` checa a carga dos arquivos que conhece e cala sobre o que
ninguém matriculou: gancho commitado e ligado atravessa o "tudo em dia" sem
viajar.

Página nova em `conhecimento/` já entra sozinha — a tupla `FONTES` carrega a
pasta inteira por padrão. Gancho novo, não. São **cinco pontos**, todos no
`montar.py`:

1. A constante com o caminho do arquivo.
2. A constante com o comando que entra no `settings.json`.
3. O `GanchoDeclarado`, que amarra evento, matcher e comando.
4. A tupla `FONTES`, que diz o que se embute.
5. A sequência `garantir_ajustes`, que instala.

O gabarito é o commit que estreia um gancho: os cinco pontos aparecem juntos
no mesmo diff. E a prova não é reler o instalador: é montar árvore virgem,
rodar o `montar.py` nela, e ver o arquivo chegar.

**Gancho se edita em sessão do dono, não dentro de uma execução.** O
`vetar-escrita-em-politica` recusa escrita em `.claude/hooks/`, no
`settings.json`, nas listas que as cercas leem e em `nucleo/regras.json`
enquanto a marca `ENCADEADOR_ETAPA` estiver no ambiente. Em sessão
interativa a marca não existe e a cerca não morde: é essa a saída do laço
— o gancho que protege os ganchos protege a si mesmo, e quem o muda é
quem não está sendo vetado por ele.

## Instrumento novo se matricula em um ponto

Instrumento de `.agents/` é mais barato que gancho: ele não tem evento nem
matcher, então basta **a tupla `FONTES`** do `montar.py` — o mesmo quinto
ponto do gancho, sozinho. Quem seguir a receita das cinco linhas para um
instrumento procura quatro pontos que não existem.

Duas saídas dessa matrícula, e as duas são declaração:

- **Instrumento que só serve a este repositório não viaja.** Ele se declara em
  `INSTRUMENTOS_QUE_FICAM`, no `.agents/camada/camada.py`, com o motivo
  escrito ao lado. É o caso do `.agents/saude/saude.py`, que mede este
  repositório contra o instalador dele.
- **Instrumento que chega por módulo já viaja embutido** no bloco `MODULOS`.
  Repetir a linha no `FONTES` faria o mesmo arquivo entrar duas vezes.

A rotina `matricula` cobra o saldo dos dois lados: rastreado fora do `FONTES`
(não viaja, e quem instala não recebe) e declaração que sobra (a exceção
sobreviveu ao arquivo). Rode-a sempre que entrar ou sair instrumento — e
repare em QUAL comando, porque o `verificacoes.py` **não viaja**:

```bash
python3 verificacoes.py matricula              # aqui, no atlas
python .agents/camada/camada.py --matricula    # em quem instalou a camada
```

## Função repetida entre ganchos muda em todos

Cada gancho é um arquivo que roda sozinho, sem biblioteca comum — de
propósito. O preço é que a mesma função está copiada em vários ganchos —
conte com `grep -h '^def ' .claude/hooks/*.py | sort | uniq -c | sort -rn`,
porque número escrito aqui envelhece calado.

Consertar uma dessas em um gancho só reprova a rotina `camada`: ela compara
as **cópias** de mesmo nome entre ganchos e acusa quando duas divergem. Ou
muda em todos, ou declara a divergência em `FUNCOES_QUE_PODEM_DIVERGIR`, com
o motivo escrito ao lado.

## Página nova precisa de quem a leia

Uma página que nenhuma outra cita é órfã: ela cobra contexto de toda sessão
e não entrega a nenhuma. Por isso a verificação da camada reprova página sem
link de entrada. Ao criar uma, cite-a de algum texto que já é lido — e, se
não houver de onde citar, provavelmente ela não devia existir.

## Achado que não vira arquivo vai para a caixa

Nem tudo que a sessão descobre vira página. Defeito e ideia de melhoria viram
linha nas issues permanentes, escritas pelo `.agents/caixa/caixa.py` — e não
trabalho fora do assunto de agora. Cada linha leva a etiqueta do seu tipo, e
por isso as duas caixas podem apontar para a MESMA issue: um quadro só. Linha
que acabou sai por `caixa.py podar --id <identidade>`, que tira a linha do
quadro e deixa o registro do fechamento em comentário da caixa.

O relatório de fim de rodada não é linha: `caixa.py relatar --corpo <texto>`
abre um comentário NOVO na mesma caixa, um por rodada. Linha se reescreve por
desenho, e por isso o quadro só guardaria a última — o comentário guarda todas.

Para **ler** essas issues use `gh api ... -q .body`, nunca `gh issue view`. O
`view` renderiza o markdown e come as marcas HTML que delimitam o bloco do
instrumento. Quem reescreve o corpo a partir do que o `view` mostrou apaga as
marcas, e a próxima escrita do `caixa.py` se perde.

## O que a camada garante em cada ferramenta

Medido em 31/08 rodando outra ferramenta de agente sobre esta árvore. A camada
tem duas metades, e as duas atravessam — por caminhos diferentes.

| o que | como atravessa |
| --- | --- |
| as regras, as skills, as nove barreiras, as páginas | sozinhas: é texto, e a outra ferramenta testada já lê `.agents/skills/` sem configuração nenhuma |
| as cercas que recusam e as que orientam | pela **ponte**, ligada com `python montar.py --devin` para o agente de terminal e `--copilot` para o assistente do editor (`.github/hooks/atlas.json`) |

A ponte não é cerca nova. Ela lê a mesma lista de cercas que o Claude Code lê,
traduz o nome da ferramenta que chegou — os parâmetros já são os mesmos — e
devolve a recusa no dialeto de quem perguntou. Cerca que some daqui some de lá
junto, e ninguém precisa lembrar de dois lugares.

Ela carrega as duas respostas, não só a dura: cerca que **orienta** em vez de
recusar atravessa igual. Essa metade some calada quando ninguém a espera, e
some sem erro nenhum — foi o que aconteceu na primeira versão da ponte.

```bash
python3 .agents/travessia/travessia.py            # as cercas atravessam?
python3 .agents/travessia/travessia.py --custa "<pedido>"   # e quanto custa
```

A primeira linha **não abre sessão nenhuma**: ela conversa com a ponte no
dialeto da outra ferramenta e compara com o que a camada deveria responder. É
de graça e se repete quando quiser. A segunda abre duas sessões, com e sem a
camada, e diz a diferença — essa paga, e avisa que paga.

**O que ainda não atravessa.** A lista de caminhos negados da outra ferramenta
só vale no arquivo de configuração do usuário, não no do repositório: foi
medido, e é por isso que a ponte usa gancho, que vale no repositório. Quem
quiser a negativa por caminho declara à mão na configuração de usuário.

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
