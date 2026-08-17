"""Gancho PreToolUse: PROFESSOR de credencial — orienta a leitura pelo shell,
veta só o que não se desfaz.

A trava antiga negava ler o conteúdo e deixava a sessão perdida na porta do
login. Decisão do dono (16/08/2026): **ler é reversível; publicar não é** —
a trava muda de eixo e o gancho passa a ensinar. O princípio, escrito na
issue da esteira: *trava no que não se desfaz; instrumento educativo em todo
o resto.*

Três respostas, decididas por segmento — e a ordem das perguntas é a mesma
da trava antiga (o alvo manda, nunca o verbo; 33 casos medidos continuam
valendo):

1. **CALA** — o alvo não é credencial, ou o comando só lê NOME (`ls`,
   `test`, `find`, `stat`...). Aviso que aparece sempre ensina a ignorar
   aviso — metade dos testes prova o silêncio.
2. **ORIENTA** — o comando LÊ O CONTEÚDO de credencial (`cat`, `grep`,
   `cp`...). Passa, e o modelo recebe por `additionalContext` a lição: onde
   o arquivo mora, `${VARIAVEL}` no lugar do valor, o que fazer se já entrou
   no git. Medido nesta camada (claude 2.1.233, 16/08/2026): o
   `additionalContext` de PreToolUse chega ao modelo e não mexe no fluxo de
   permissão — `permissionDecision: "allow"` auto-aprovaria a chamada, e por
   isso NÃO se usa aqui.
3. **VETA** — o alvo é credencial e o verbo GRAVA HISTÓRIA ou PUBLICA
   (`git`, `gh`): `git commit -m "$(cat .env)"`, `gh issue comment
   --body-file .env`. Aí recusa: segredo que sobe fica exposto, e o conserto
   vira trocar o segredo — reescrever história tira da listagem, não do
   alcance.

Este gancho é o PRIMEIRO CLIENTE do recibo da esteira (`.agents/recibo/`):
cada ORIENTA materializa um recibo `segue` e cada VETA um `para`, escritos
por código em `tmp/recibos/orientacao-credencial/` — a prova do `provado` é
re-executável (`--avaliar`). O recibo nunca decide nada: se ele falhar, a
decisão sai igual — o recibo falha alto no canto dele, o gancho falha
aberto no dele.

Rode os testes com:    python .claude/hooks/orientar-credencial.py --testar
Avalie um comando:     python .claude/hooks/orientar-credencial.py --avaliar '<cmd>'
"""

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

# As três famílias, casadas contra o nome do arquivo — nunca contra o comando
# inteiro. Casar contra o comando inteiro pegaria toda página que cita o
# assunto, e gancho largo demais é desligado na primeira semana.
#
# `.env` é exato, `.envrc` é exato e `.env.<algo>` cobre `.env.local` e
# `.env.exemplo` — arquivo de exemplo entra junto, por decisão do dono: as
# quatro regras do `deny` já o pegam, e duas proteções da mesma casa
# discordando é pior que uma orientando demais. Fica de fora, de propósito, o
# nome que só COMEÇA parecido: `.envision.md` é página, não credencial.
NOME_DE_CREDENCIAL = re.compile(r"^(\.env|\.envrc|\.env\..+|appsettings(\..+)?\.json)$")

# Pasta inteira: qualquer pedaço do caminho chamado exatamente assim.
PASTA_DE_CREDENCIAL = ".credenciais"

# As marcas que fazem valer a pena olhar. Sem nenhuma delas o gancho sai na
# primeira linha — ele roda antes de TODO comando de shell da sessão.
MARCAS = (".env", "appsettings", PASTA_DE_CREDENCIAL)

# Verbos que revelam só NOME e existência, nunca o conteúdo. Allowlist curto
# de propósito: o conjunto de verbos que LEEM conteúdo é infinito (`cat`,
# `head`, `sort`, `awk`, `strings`, `base64`, `openssl`...), e por isso não
# se pode listá-los; já o conjunto que só olha metadado é pequeno e fechado.
# `file` fica de FORA: ele lê alguns bytes para adivinhar o tipo, e a régua
# aqui é nome/existência, não "quase nada do conteúdo".
VERBOS_SO_DE_NOME = {"ls", "test", "[", "stat", "find",
                     "readlink", "realpath", "dirname", "basename"}

# Os verbos do que NÃO SE DESFAZ: gravam história ou publicam. `git` grava
# história local que vira pública no push; `gh` fala direto com o GitHub.
# Lista curta e fechada de propósito, o espelho do allowlist de nome: o que
# lê é infinito e orienta; o que entrega para fora é pequeno e veta.
VERBOS_QUE_NAO_SE_DESFAZEM = {"git", "gh"}

# `find` é de nome — MAS `-exec`/`-ok` rodam outro comando (que pode ser
# `cat`), e `-fprint*`/`-fls` escrevem no arquivo apontado. Com qualquer um
# desses, o `find` deixa de ser só-de-nome.
FIND_LE_OU_ESCREVE = re.compile(r"-(?:exec|execdir|ok|okdir|fprint|fprintf|fls)\b")

# Prefixos que só antecedem o verbo de verdade — some com eles para achá-lo.
# Tirá-los nunca transforma perigoso em seguro: `sudo cat .env` continua
# `cat`; só revela o `ls` que estava atrás de um `sudo`.
PREFIXOS = {"sudo", "command", "env", "nice", "nohup", "time", "stdbuf",
            "builtin", "exec", "\\"}

# Separadores de comando: entre dois comandos, cada lado é julgado sozinho.
# `&&` e `||` vêm antes de `&` e `|` sozinhos para o alternador casar o par
# primeiro. Sem o `&` sozinho, `ls & cat .env` esconderia o `cat` atrás do
# `ls` de nome — e vazaria.
SEPARADORES = re.compile(r"&&|\|\||;|\n|\||&")

# Documento entregue com o delimitador entre aspas (`<<'FIM'`) é dado literal.
# Sem esta exceção o gancho morde quem escreve o recibo dele — foi assim que
# o veto de branch mordeu o próprio autor. Só o CORPO sai da varredura; o
# resto da linha de abertura fica, senão `cat <<'FIM' > .env` se esconderia
# atrás do documento.
DOCUMENTO_LITERAL = re.compile(
    r"<<-?\s*(['\"])(\w+)\1([^\n]*)\n.*?(?:^\2\s*$|\Z)", re.S | re.M)

# O que vem depois de uma bandeira de mensagem é mensagem, não alvo: `git
# commit -m "explica o .env"` cala. A ressalva é a que o veto de branch
# aprendeu na marra — dentro de aspas duplas o `$(...)` ainda executa, então
# `-m "$(cat .env)"` NÃO é mensagem, é leitura indo para a história.
EXECUTA_DENTRO = re.compile(r"\$\(|`")

# Colada na bandeira por um igual, a mensagem é o resto da palavra — não há
# como confundi-la com um alvo. Por isso aqui vale também sem aspas.
MENSAGEM_COLADA = re.compile(
    r"""(?:--message|--body|-m)=(?:"([^"]*)"|'([^']*)'|(\S*))""")

# Separada por espaço, ela SÓ vale entre aspas, e a razão é um falso negativo
# que apareceu no teste: em `ls -m .env` o `-m` é bandeira comum e o `.env` é
# alvo de verdade. Mensagem com espaço precisa de aspas de qualquer jeito;
# exigi-las devolve a diferença entre os dois casos.
MENSAGEM_SEPARADA = re.compile(
    r"""(?<!\S)(?:--message|--body|-am|-m)\s+("[^"]*"|'[^']*')""")

# Pedaços que podem ser caminho de arquivo. Aspas, parênteses e vírgula ficam
# de fora do conjunto de propósito: é isso que faz `open('.env')` render o
# candidato `.env` limpo, em vez de um pedaço colado que não casa com nada.
CANDIDATO = re.compile(r"[\w./\\~-]+")

# Onde nascem os recibos deste gancho: dentro de tmp/, o endereço do
# descartável — a camada já ignora /tmp/* no git, e recibo de orientação é
# evidência de uso, não entrega.
DIR_RECIBOS = "tmp/recibos"
TRABALHO_RECIBO = "orientacao-credencial"
ETAPA_RECIBO = "orientar-credencial"

ORIENTACAO = (
    "O comando LÊ O CONTEÚDO de '{alvo}', que é arquivo de credencial. Passa "
    "— ler é reversível — e fica a lição: (1) o valor que entra na sessão "
    "entra no histórico dela — trabalhe com o NOME (${{VARIAVEL}}), e nunca "
    "cole o valor em arquivo, issue, commit ou resposta; (2) credencial mora "
    "fora de todo git — na gaveta .credenciais/ do workspace ou no cofre da "
    "casa — e configuração versionada carrega ${{VARIAVEL}}, nunca o valor; "
    "(3) se este arquivo já entrou em algum git, o valor está exposto: o "
    "conserto é TROCAR o segredo — reescrever história tira da listagem, não "
    "do alcance; (4) backup de credencial é cópia fora do repositório, nunca "
    "commit. Precisa só do nome ou da existência? `ls`, `test`, `find` e "
    "`stat` respondem sem abrir o valor."
)

VETO = (
    "Isto levaria o conteúdo de '{alvo}', que é arquivo de credencial, para "
    "onde NÃO SE DESFAZ (git grava história; gh publica). Segredo que sobe "
    "fica exposto, e o conserto vira trocar o segredo. Refaça sem o valor: "
    "referencie pelo NOME (${{VARIAVEL}}); para citar o arquivo num texto, a "
    "bandeira de mensagem (-m \"explica o .env\") e o documento com "
    "delimitador entre aspas (<<'FIM') passam. Ler localmente também passa — "
    "este gancho só barra o que sai."
)


def sem_aspas(token: str) -> str:
    """Tira TODA aspa do token, não só o par que o envolve.

    O `shlex` roda em modo não-posix de propósito: em modo posix ele comeria a
    contrabarra de um caminho do Windows. O preço é que as aspas ficam coladas
    no token, e `'.env'` deixaria de ser igual a `.env`.

    Tirar só o par de fora não basta, e isto foi medido: o shell cola os
    pedaços de `.en''v` e abre o mesmo arquivo. Tirando todas, o nome volta a
    ser o que o shell vai usar de verdade.
    """
    return token.replace('"', "").replace("'", "")


def tirar_atribuicoes_literais(segmento: str) -> str:
    """Atribuição de ambiente no prefixo é CONFIGURAÇÃO, não conteúdo.

    `GH_CONFIG_DIR=.credenciais/.gh-bot gh pr create` autentica pelo
    chaveiro e publica só o corpo — o caminho na atribuição diz ao programa
    ONDE está a credencial; o valor dela não sai da máquina. Medido em
    17/08/2026: o veto aqui barrou o fluxo de PR da própria casa (falso
    positivo no PR de promoção do workspace raiz).

    Só sai da varredura a atribuição LITERAL: com `$(` ou crase no valor
    (`TOKEN=$(cat .env) gh ...`), há leitura de verdade acontecendo e o
    segmento fica inteiro para ser julgado. E tirar o prefixo nunca
    inocenta o resto: alvo de credencial no argv do verbo continua lá.
    """
    s = segmento.lstrip()
    while True:
        atribuicao = re.match(r"[A-Za-z_]\w*=\S*(?:\s+|$)", s)
        if not atribuicao or EXECUTA_DENTRO.search(atribuicao.group(0)):
            return s
        s = s[atribuicao.end():]


def e_credencial(pedaco: str) -> str:
    """Devolve o nome do alvo se este pedaço aponta para uma credencial."""
    for candidato in CANDIDATO.findall(pedaco):
        partes = [p for p in re.split(r"[/\\]", candidato) if p]
        if not partes:
            continue
        if any(p.lower() == PASTA_DE_CREDENCIAL for p in partes):
            return candidato
        if NOME_DE_CREDENCIAL.match(partes[-1].lower()):
            return candidato
    return ""


def primeiro_verbo(segmento: str) -> str:
    """O verbo de verdade do segmento, sem os prefixos e as atribuições."""
    s = segmento.strip()
    while s:
        atribuicao = re.match(r"[A-Za-z_]\w*=\S*\s+", s)
        if atribuicao:
            s = s[atribuicao.end():]
            continue
        palavra = re.match(r"(\S+)\s*", s)
        if not palavra:
            return ""
        base = re.split(r"[/\\]", palavra.group(1))[-1].strip("\"'").lower()
        if base in PREFIXOS:
            s = s[palavra.end():]
            continue
        return base
    return ""


def so_le_o_nome(segmento: str) -> bool:
    """O segmento apenas lista/testa nome, sem chegar ao conteúdo?

    A substituição de comando derruba a garantia: `X=$(cat .env) ls` tem
    verbo `ls`, mas o `$(...)` leu o arquivo antes. Com `$(` ou crase no
    segmento, nada é só-de-nome.
    """
    if EXECUTA_DENTRO.search(segmento):
        return False
    verbo = primeiro_verbo(segmento)
    if verbo not in VERBOS_SO_DE_NOME:
        return False
    if verbo == "find" and FIND_LE_OU_ESCREVE.search(segmento):
        return False
    return True


def tirar_mensagem(trecho) -> str:
    """Apaga o valor de uma bandeira de mensagem — só quando é mesmo texto.

    A ressalva é a que o veto de branch aprendeu na marra: dentro de aspas
    duplas o `$(...)` ainda executa. `-m "$(cat .env)"` não é mensagem, é
    leitura indo para a história — e essa fica, para ser varrida.
    """
    valor = next((g for g in trecho.groups() if g is not None), "")
    return " " if not EXECUTA_DENTRO.search(valor) else trecho.group(0)


def vale_olhar(comando: str) -> bool:
    """A saída rápida: sem nenhuma das marcas, não há o que examinar.

    Ela mora AQUI, e não no `main()`, por uma razão medida: com a saída
    rápida só no `main()`, o autoteste passava por um caminho que o gancho
    nunca toma — e deu OK num caso que o gancho de verdade deixava passar.

    As aspas saem antes da comparação pelo mesmo motivo de sempre: o shell
    cola `.en''v` e o resultado é `.env`.
    """
    limpo = sem_aspas(comando).lower()
    return any(marca in limpo for marca in MARCAS)


def decisao(comando: str) -> tuple:
    """('', ''), ('orienta', alvo) ou ('veta', alvo) para o comando inteiro.

    A ordem é o desenho herdado da trava: tira o que é DADO — corpo de
    documento literal e mensagem —, quebra em segmentos por separador de
    comando, e julga cada um sozinho. Um segmento conta quando aponta
    credencial E não é só-de-nome; aí o verbo decide o grau — `git`/`gh`
    veta na hora (o veto vence a orientação: basta um segmento que publica
    para o comando inteiro não poder rodar), o resto orienta.
    """
    if not comando or not vale_olhar(comando):
        return "", ""
    texto = DOCUMENTO_LITERAL.sub(r"\3", comando)
    texto = MENSAGEM_COLADA.sub(tirar_mensagem, texto)
    texto = MENSAGEM_SEPARADA.sub(tirar_mensagem, texto)
    resposta, alvo_achado = "", ""
    for segmento in SEPARADORES.split(texto):
        segmento = tirar_atribuicoes_literais(segmento)
        alvo = e_credencial(sem_aspas(segmento))
        if not alvo or so_le_o_nome(segmento):
            continue
        if primeiro_verbo(segmento) in VERBOS_QUE_NAO_SE_DESFAZEM:
            return "veta", alvo
        resposta, alvo_achado = "orienta", alvo
    return resposta, alvo_achado


def raiz_do_repositorio() -> Path:
    """A raiz: onde o gancho foi declarado, ou dois níveis acima dele.

    O comando do settings.json carrega ${CLAUDE_PROJECT_DIR}; quando a
    variável não vem (teste, execução à mão), o próprio arquivo sabe onde
    mora: .claude/hooks/ fica dois níveis abaixo da raiz.
    """
    base = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(base) if base else Path(__file__).resolve().parents[2]


def emitir_recibo(resposta: str, alvo: str, comando: str) -> None:
    """O primeiro cliente do contrato: orienta é `segue`, veta é `para`.

    Materializado por código (.agents/recibo/recibo.py), nunca por texto — a
    emenda do degrau 1. A prova do `provado` é re-executável: `--avaliar`
    repete o julgamento deste gancho sobre o mesmo comando, sem executá-lo.

    O recibo NUNCA decide: qualquer falha aqui — script ausente (casa sem a
    esteira), colisão de escritor (dois Bash em paralelo orientando junto),
    NTFS sem os.link — é engolida, e a decisão do gancho sai igual. O recibo
    falha alto no canto dele (recibo.py cuida disso); o gancho falha aberto.
    O JSON viaja em ASCII puro de propósito: o filho decodifica o stdin pela
    localidade, e a do Windows não é utf-8.
    """
    try:
        raiz = raiz_do_repositorio()
        script = raiz / ".agents" / "recibo" / "recibo.py"
        if not script.is_file():
            return
        corpo = {
            "etapa": "x", "trabalho": "x", "quando": "2000-01-01T00:00:00Z",
            "ciclo": {"i": 1, "teto": 1},
            "veredito": "segue" if resposta == "orienta" else "para",
            "provado": [{
                "afirmacao": (f"o comando aponta credencial ({alvo}) e "
                              + ("lê o conteúdo"
                                 if resposta == "orienta"
                                 else "entrega para onde não se desfaz")),
                "comando": ("python .claude/hooks/orientar-credencial.py "
                            f"--avaliar {shlex.quote(comando)}"),
                "saida": f"{resposta}: {alvo}",
            }],
            "suposto": [],
            "faltas": [],
        }
        if resposta == "veta":
            corpo["proximo"] = (
                "Refaça o comando sem o valor da credencial: referencie pelo "
                "NOME (${VARIAVEL}) ou use a bandeira de mensagem — o "
                "conteúdo não sobe para git nem gh.")
        subprocess.run(
            [sys.executable, str(script), "materializar",
             "--dir", str(raiz / DIR_RECIBOS),
             "--trabalho", TRABALHO_RECIBO,
             "--etapa", ETAPA_RECIBO,
             "--ordem", "1", "--teto", "1"],
            input=json.dumps(corpo).encode("ascii"),
            capture_output=True, timeout=10)
    except Exception:
        pass


def resposta_json(resposta: str, alvo: str) -> dict:
    """O JSON de saída do gancho — a forma medida na sonda de 16/08/2026.

    ORIENTA usa `additionalContext` SEM permissionDecision: o texto chega ao
    modelo e o fluxo de permissão fica intacto (um "allow" auto-aprovaria a
    chamada). VETA usa o `deny` de sempre.
    """
    if resposta == "veta":
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": VETO.format(alvo=alvo),
        }}
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": ORIENTACAO.format(alvo=alvo),
    }}


def main() -> int:
    try:
        entrada = json.load(sys.stdin)
        comando = entrada.get("tool_input", {}).get("command", "")
    except (json.JSONDecodeError, AttributeError, TypeError):
        return 0  # falha aberto: entrada quebrada não prende a sessão

    resposta, alvo = decisao(comando)
    if not resposta:
        return 0  # cala: sair 0 sem imprimir nada

    emitir_recibo(resposta, alvo, comando)
    print(json.dumps(resposta_json(resposta, alvo)))
    return 0


def avaliar(argv) -> int:
    """`--avaliar '<cmd>'`: imprime o julgamento — é a prova re-executável."""
    depois = argv[argv.index("--avaliar") + 1:]
    if not depois:
        print("uso: orientar-credencial.py --avaliar '<comando>'",
              file=sys.stderr)
        return 2
    resposta, alvo = decisao(depois[0])
    print(f"{resposta}: {alvo}" if resposta else "cala")
    return 0


# --- Testes -----------------------------------------------------------------
# Três listas de decisão e uma de comportamento. A que importa é a CALA:
# gancho largo demais é desligado na primeira semana — e aviso que aparece
# sempre ensina a ignorar aviso. Cada caso que orienta ou veta tem um par
# que cala, pelo mesmo mecanismo, com alvo que não é credencial — ou com
# verbo que só lê o nome.

ORIENTA = [
    ("abrir direto", "cat .env"),
    ("abrir com aspas", "cat '.env'"),
    ("abrir por dentro do python", 'python -c "print(open(\'.env\').read())"'),
    ("buscar dentro da pasta de credencial", "grep -r SENHA .credenciais/"),
    ("ler conteúdo de arquivo na pasta", "cat .credenciais/mcp.env"),
    ("caminho relativo para cima", "less ../.credenciais/gh-bot"),
    ("configuração do .NET", "type appsettings.Production.json"),
    ("no PowerShell", "Get-Content .env.local"),
    ("escondido depois de &&", "git status && cat .env"),
    ("ls de nome não inocenta o cat ao lado", "ls .credenciais && cat .env"),
    ("escondido atrás de & de fundo", "ls & cat .env"),
    ("dentro de outro shell", "bash -c 'cat .env'"),
    # find é de nome — mas -exec roda outro comando, que aqui lê o conteúdo.
    ("find que executa leitura", "find .credenciais -exec cat {} \\;"),
    ("find que executa leitura no diretório", "find .credenciais -execdir less {} +"),
    # Substituição de comando lê o arquivo antes do verbo de nome rodar.
    ("verbo de nome com leitura embutida", "X=$(cat .env) ls"),
    ("copiar dentro da máquina é ler, não publicar", "cp .env /tmp/copia"),
    ("exemplo entra junto, por decisão do dono", "cat .env.exemplo"),
    # O shell cola os pedaços: `.en''v` abre o mesmo arquivo que `.env`.
    # Medido — o veto de branch ainda tem este furo, e foi por isso que
    # aqui as aspas saem TODAS, não só o par de fora.
    ("aspas coladas no meio do nome", "cat .en''v"),
    ("aspas que cortam o nome em dois", 'cat ".en"v'),
    # Atribuição com $() lê de verdade — o prefixo NÃO sai da varredura e a
    # leitura orienta. Não veta: o corpo publicado é outro, e passar token
    # por variável de ambiente é padrão legítimo de autenticação.
    ("atribuição que lê antes de rodar gh",
     'TOKEN=$(cat .env) gh pr create --title x --body y'),
]

VETA = [
    # A armadilha que o veto de branch já tinha ensinado: dentro de aspas
    # duplas o `$(...)` executa — e aqui o resultado vai para a HISTÓRIA.
    ("mensagem que na verdade executa e commita", 'git commit -m "$(cat .env)"'),
    ("mensagem colada que executa e commita",
     'git commit --message="$(cat .env)"'),
    # `--body-file` come um ARQUIVO, não uma mensagem. Um caractere de
    # diferença para `--body`, e o efeito é publicar o conteúdo.
    ("bandeira que parece mensagem mas publica o arquivo",
     "gh issue comment 13 --body-file .env"),
    ("anexar credencial num pr", "gh pr create --title x --body-file .env"),
    ("adicionar credencial ao índice", "git add .env"),
    # Configuração no prefixo não inocenta credencial no argv do verbo.
    ("chaveiro no prefixo e credencial no argv",
     "GH_CONFIG_DIR=.credenciais/.gh-bot gh issue comment 1 "
     "--body-file .credenciais/mcp.env"),
]

CALA = [
    ("abrir arquivo comum", "cat README.md"),
    ("abrir arquivo comum com aspas", "cat 'README.md'"),
    ("buscar palavra no conhecimento", "rg TOKEN conhecimento/"),
    ("buscar palavra parecida", 'grep -rn "environment" fluxos/'),
    ("pasta que só começa parecido", "ls .credenciais-explicado/"),
    ("página que fala do assunto", "cat conhecimento/appsettings-explicado.md"),
    ("nome que só começa parecido", "cat .envision.md"),
    # Falar de credencial num texto não é abrir credencial — nem publicar.
    ("mensagem de commit que cita o arquivo",
     'git commit -m "explica o .env no LEIAME"'),
    ("mensagem colada na bandeira com igual",
     'git commit --message="ajusta o .env de exemplo"'),
    ("corpo de comentário pelo gh", 'gh issue comment 13 --body "o gancho orienta .env"'),
    ("corpo de pr que cita credencial", 'gh pr create --title x --body "documenta o .env"'),
    ("commit de página que cita o assunto",
     "git add conhecimento/appsettings-explicado.md"),
    # Foi este caso que mordeu o recibo do veto de branch. O recibo DESTE
    # gancho é entregue exatamente assim.
    ("documento literal é dado, não comando",
     "gh issue comment 13 --body-file - <<'FIM'\ncat .env\nFIM"),
    ("o ritual da casa", "python montar.py --sincronizar"),
    ("o próprio autoteste", "python .claude/hooks/orientar-credencial.py --testar"),
    # Ler NOME não é ler conteúdo — o que destrava organizar sem abrir valor.
    ("listar a pasta de credencial", "ls .credenciais/"),
    ("listar detalhado a subpasta", "ls -la .credenciais/putty"),
    ("testar existência da pasta", "test -d .credenciais"),
    ("testar existência de arquivo", "[ -f .credenciais/mcp.env ]"),
    ("achar chave pelo nome", "find .credenciais -name '*.key'"),
    ("metadado sem conteúdo", "stat .credenciais/mcp.env"),
    # `ls .env` revela só que o arquivo existe e como se chama — nome, não
    # valor. `-m` aqui é bandeira do ls.
    ("listar o próprio arquivo de credencial", "ls -m .env"),
    # O par do furo das aspas: aspa colada no meio de um nome que não é
    # credencial continua calando.
    ("aspas coladas em nome comum", "cat REA''DME.md"),
    ("aspas que cortam nome comum em dois", 'cat "REA"DME.md'),
    ("bandeira comum com alvo comum", "ls -m conhecimento/"),
    # Atribuição de ambiente é configuração: o chaveiro autentica o gh; o
    # que sobe é só o corpo. Foi o veto deste caso que barrou o PR de
    # promoção da própria casa em 17/08/2026.
    ("chaveiro como configuração do gh",
     "GH_CONFIG_DIR=.credenciais/.gh-bot gh pr create --title x "
     "--body-file corpo.md"),
    ("chaveiro absoluto como configuração",
     "GH_CONFIG_DIR=/home/x/code/casa/.credenciais/.gh-bot gh api user"),
    ("variável apontando credencial antes de verbo comum",
     "CONFIG=.credenciais/mcp.env python roda.py"),
]


def _testar_comportamento(falhas: list) -> None:
    """O que as listas não cobrem: a forma da saída e o recibo de verdade."""
    import shutil
    import tempfile

    def caso(rotulo, condicao):
        if not condicao:
            falhas.append(f"  comportamento — {rotulo}")

    # A forma da saída: orienta ensina sem decidir permissão; veta nega.
    orienta = resposta_json("orienta", ".env")["hookSpecificOutput"]
    caso("orienta leva additionalContext", "additionalContext" in orienta)
    caso("orienta NÃO decide permissão (allow auto-aprovaria)",
         "permissionDecision" not in orienta)
    veta = resposta_json("veta", ".env")["hookSpecificOutput"]
    caso("veta nega", veta.get("permissionDecision") == "deny")
    caso("veta explica", bool(veta.get("permissionDecisionReason")))

    # O recibo de verdade, numa raiz descartável com a esteira copiada.
    raiz_real = Path(__file__).resolve().parents[2]
    origem = raiz_real / ".agents" / "recibo"
    guardado = os.environ.get("CLAUDE_PROJECT_DIR")
    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        if origem.is_dir():
            shutil.copytree(origem, raiz / ".agents" / "recibo")
            os.environ["CLAUDE_PROJECT_DIR"] = pasta
            try:
                emitir_recibo("orienta", ".env", "cat .env")
                emitir_recibo("veta", ".env",
                              "gh issue comment 13 --body-file .env")
            finally:
                if guardado is None:
                    os.environ.pop("CLAUDE_PROJECT_DIR", None)
                else:
                    os.environ["CLAUDE_PROJECT_DIR"] = guardado
            pasta_recibos = raiz / DIR_RECIBOS / TRABALHO_RECIBO
            primeiro = pasta_recibos / f"01-{ETAPA_RECIBO}-c1.json"
            segundo = pasta_recibos / f"01-{ETAPA_RECIBO}-c2.json"
            caso("orienta materializa recibo c1", primeiro.is_file())
            caso("veta materializa recibo c2 (ciclo pela contagem)",
                 segundo.is_file())
            if primeiro.is_file() and segundo.is_file():
                r1 = json.loads(primeiro.read_text(encoding="utf-8"))
                r2 = json.loads(segundo.read_text(encoding="utf-8"))
                caso("orienta é segue", r1.get("veredito") == "segue")
                caso("veta é para, com proximo",
                     r2.get("veredito") == "para" and r2.get("proximo"))
                # A prova é re-executável: --avaliar repete o julgamento.
                prova = subprocess.run(
                    ["bash", "-c", r1["provado"][0]["comando"]],
                    capture_output=True, text=True, cwd=raiz_real)
                caso("a prova do provado re-executa igual",
                     prova.stdout.strip() == r1["provado"][0]["saida"])
                valida = subprocess.run(
                    [sys.executable, str(origem / "recibo.py"),
                     "validar", str(primeiro)], capture_output=True)
                caso("o recibo do gancho passa no validador",
                     valida.returncode == 0)
        else:
            falhas.append("  comportamento — .agents/recibo não existe na "
                          "camada; o primeiro cliente ficou sem contrato")

    # Falha aberta: casa SEM a esteira decide igual e não escreve nada.
    with tempfile.TemporaryDirectory() as pasta:
        os.environ["CLAUDE_PROJECT_DIR"] = pasta
        try:
            emitir_recibo("orienta", ".env", "cat .env")
        finally:
            if guardado is None:
                os.environ.pop("CLAUDE_PROJECT_DIR", None)
            else:
                os.environ["CLAUDE_PROJECT_DIR"] = guardado
        caso("sem .agents/recibo, nada nasce e nada quebra",
             not (Path(pasta) / DIR_RECIBOS).exists())


def testar() -> int:
    falhas = []
    for rotulo, comando in ORIENTA:
        resposta, _ = decisao(comando)
        if resposta != "orienta":
            falhas.append(f"  DEVIA ORIENTAR e {resposta or 'calou'} — "
                          f"{rotulo}: {comando}")
    for rotulo, comando in VETA:
        resposta, _ = decisao(comando)
        if resposta != "veta":
            falhas.append(f"  DEVIA VETAR e {resposta or 'calou'} — "
                          f"{rotulo}: {comando}")
    for rotulo, comando in CALA:
        resposta, alvo = decisao(comando)
        if resposta:
            falhas.append(f"  DEVIA CALAR e {resposta} — "
                          f"{rotulo}: {comando} ({alvo})")
    _testar_comportamento(falhas)
    total = len(ORIENTA) + len(VETA) + len(CALA)
    if falhas:
        print(f"FALHOU: {len(falhas)} casos")
        print("\n".join(falhas))
        return 1
    print(f"OK: {total} casos de decisão — {len(ORIENTA)} orientam, "
          f"{len(VETA)} vetam, {len(CALA)} calam — e o comportamento "
          "(saída, recibo, falha aberta) confere")
    return 0


if __name__ == "__main__":
    if "--testar" in sys.argv:
        sys.exit(testar())
    if "--avaliar" in sys.argv:
        sys.exit(avaliar(sys.argv))
    sys.exit(main())
