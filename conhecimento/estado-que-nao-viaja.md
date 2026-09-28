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

## O estado que a ferramenta apaga sozinha

O Claude Code apaga as transcrições (`~/.claude/projects/`) mais velhas que
`cleanupPeriodDays` (padrão 30 dias) a cada inicialização. Declare no
settings de usuário `"cleanupPeriodDays": 3650`, nunca 0 (o zero desliga a
persistência inteira:
[apagamento silencioso](https://github.com/anthropics/claude-code/issues/62476),
[defeito do zero](https://github.com/anthropics/claude-code/issues/23710));
prove com um arquivo de data antiga que sobrevive a uma sessão nova; e ponha
a pasta na rotina de cópia da máquina.

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
  "variavel": ["FERRAMENTA_X_TOKEN"]
}
```

`comando` tem de estar no PATH; `pasta` e `arquivo` no disco (`~` vale);
`variavel` definida, só o nome. O gancho `verificar-ambiente.py` confere na
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
