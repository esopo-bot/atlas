# O estado que não viaja

Trocar de pasta, de disco ou de máquina apaga parte do que a sessão precisa,
e a perda é silenciosa: nada quebra na hora. Esta página é o endereço que o
aviso da abertura aponta quando falta alguma coisa; se chegou por ele, vá à
seção "Quando o aviso aparecer".

| Onde o estado mora | Exemplos | Sobrevive à mudança? |
| --- | --- | --- |
| versionado no repositório | páginas, skills, ganchos, instrumentos | sim |
| na pasta, fora do git | configuração local, notas, credenciais | só se a pasta for copiada inteira |
| na ferramenta, endereçado pelo caminho absoluto | histórico, memória do agente, aprovações | não: vira órfão |
| no perfil do sistema | variáveis de ambiente, agendamentos, chaveiro | não: fica na máquina velha |

A regra de bolso: o que vale amanhã vira arquivo no repositório; o que a
sessão precisa e não está no git se declara por nome (nome não é segredo,
valor é); o resto se assume perdido a cada mudança e se repõe pela receita.

O nome do interpretador Python não viaja mais nas linhas de gancho: desde
29/09/2026 toda linha passa pelo lançador, que escolhe o Python na máquina
onde roda; a lembrança dele (nome e caminho) mora na pasta privada do usuário
e se refaz sozinha.

A lista do que esta camada deixa fora do repositório — a telemetria, o
classificador do modo automático, o settings local, a tarefa agendada, os
binários no PATH e os registros em `tmp/` — e a ordem de repor numa máquina
nova estão em [o que vive fora do repositório](configuracao-da-maquina.md).

## O estado que a ferramenta apaga sozinha

O Claude Code apaga as transcrições (`~/.claude/projects/`) mais velhas que
`cleanupPeriodDays` (padrão 30 dias) a cada inicialização. Declare no
settings de usuário `"cleanupPeriodDays": 3650`, nunca 0 (o zero desliga a
persistência inteira:
[apagamento silencioso](https://github.com/anthropics/claude-code/issues/62476),
[defeito do zero](https://github.com/anthropics/claude-code/issues/23710));
prove com um arquivo de data antiga que sobrevive a uma sessão nova; e ponha
a pasta na rotina de cópia da máquina.

## A sessão na nuvem

A sessão na nuvem do Claude Code nasce de um clone novo: chega o que está no
git, e o resto fica na máquina
([ambientes da nuvem](https://code.claude.com/docs/en/cloud-environments)).

- **Um repositório por sessão.** Sessão com vários repositórios abre acima
  dos clones e não lê o `.claude/settings.json` de nenhum: nenhuma cerca
  roda. Vizinho que tem a camada instalada abre sessão própria.
- **O arquivo local volta por variável.** O gancho
  `preparar-sessao-na-nuvem.py` roda só quando `CLAUDE_CODE_REMOTE` vale
  `true`: grava `nucleo/executor.json` a partir de `ATLAS_EXECUTOR_BASE64`,
  se ele falta e o git o ignora, e avisa o que muda lá. Gere o valor na
  máquina onde o arquivo existe e cole no campo de variáveis do ambiente:

  ```bash
  python -c "import base64;print(base64.b64encode(open('nucleo/executor.json','rb').read()).decode())"
  ```

- **Push só na branch da sessão.** O proxy do GitHub recusa as outras; a
  entrega é o pedido de incorporação dela, e a mescla na integração sai de
  uma sessão local.
- **Uma conta só.** O `gh` responde pela conta dona da sessão; instrumento
  que pede outra conta recusa. Por isso a abertura na nuvem não mede o
  histórico das issues encerradas nem os módulos de `avisos_da_abertura`, e
  diz isso em uma linha. A exceção é o relato de entrega: na nuvem, sem a
  conta de `issues.conta_gh`, ele grava pela conta da sessão e avisa. Se
  essa conta é a mesma que o comentário marca, o GitHub não notifica.
- **GraphQL não chega.** O proxy recusa `api.github.com/graphql` com HTTP
  403, e a REST passa. Caem `gh issue view|list|create|edit|comment`,
  `gh pr view|list|create` e o quadro de projetos, que só existe em GraphQL.
  A forma que funciona é `gh api repos/<dono>/<repo>/...`, com as receitas
  em `.agents/skills/trabalho-por-issue/references/receitas.md`. O relato
  de entrega e o bloco do corpo já vão pela REST; o cartão do quadro se
  move à mão.
- **O que só existe na máquina local se declara à parte.** O que mora em
  `so_na_maquina_local` de `nucleo/ambiente.json` não se cobra na nuvem.
- **Ambiente por risco, não por projeto.** Variável de ambiente é visível a
  quem usa o ambiente: credencial de nuvem, de banco e de produção não vai
  para lá.

## Duas contas de assinatura na mesma máquina

`CLAUDE_CONFIG_DIR` move credencial, configuração, servidores de contexto,
transcrições e skills para o diretório apontado, um por conta, definida só
no comando que abre aquela sessão. Entrar sem a variável sobrescreve o
perfil principal; exportá-la no perfil do shell contamina toda sessão. A
conta secundária nasce sem os servidores e skills de usuário: reponha pelo
nome.

## A declaração: `nucleo/ambiente.json`

Arquivo seu, que a atualização nunca reescreve:

```json
{
  "receita": "conhecimento/estado-que-nao-viaja.md",
  "comando": ["git", "gh", "python"],
  "pasta": ["~/.config/ferramenta-x"],
  "arquivo": ["scripts/preparar.sh"],
  "variavel": ["FERRAMENTA_X_TOKEN"],
  "so_na_maquina_local": {"comando": ["ferramenta-y"]}
}
```

`comando` tem de estar no PATH; `pasta` e `arquivo` no disco (`~` vale);
`variavel` definida, só o nome. `so_na_maquina_local` tem as mesmas chaves e
só se cobra fora da sessão na nuvem. O gancho `verificar-ambiente.py` confere na
abertura, avisa e deixa passar; ele alcança o `.mcp.json` também: variável
exigida ali sem valor vira aviso.

## Quando o aviso aparecer

Leia o que falta pelo nome; reponha pela receita declarada (se ela não
existe, escrevê-la é o primeiro trabalho); tire da declaração o que ninguém
usa mais. Antes de instalar de novo, procure no disco: o caso mais comum é
comando instalado por gerenciador de versão, no PATH do shell interativo, e
invisível ao shell não interativo do gancho, do executor e da sessão.

```bash
command -v <comando> || echo 'não está no PATH desta sessão'
find ~ -maxdepth 6 -name '<comando>' -type f 2>/dev/null | head
```

Achou na segunda e não na primeira: ajuste o PATH que a sessão herda, ou
declare o caminho absoluto onde o instrumento o chama. Reinstalar cria uma
segunda cópia igualmente invisível. Sobre onde cada coisa se escreve, veja
[onde escrever cada coisa](mapa-do-repositorio.md).
