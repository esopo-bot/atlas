"""Gancho PreToolUse: nega abrir arquivo de credencial por comando de shell.

O `deny` do `.claude/settings.json` cobre só a ferramenta de leitura de
arquivo. Pelo terminal, `cat .env` passa inteiro — medido. Este gancho fecha
esse lado.

Ele olha o ALVO, não o verbo. `cat`, `less`, `grep`, `Get-Content` e
`python -c open(...)` abrem arquivo do mesmo jeito, e listar verbos é corrida
perdida: sempre falta um.

Três famílias, as mesmas do `deny` — `.env*`, `appsettings*.json` e o que
estiver dentro de `.credenciais/`. Ler página que só FALA do assunto passa.

Rode os testes com:  python .claude/hooks/vetar-credencial.py --testar
"""

import json
import re
import sys

# As três famílias, casadas contra o nome do arquivo — nunca contra o comando
# inteiro. Casar contra o comando inteiro barraria toda página que cita o
# assunto, e gancho largo demais é desligado na primeira semana.
#
# `.env` é exato, `.envrc` é exato e `.env.<algo>` cobre `.env.local` e
# `.env.exemplo` — arquivo de exemplo entra junto, por decisão do dono: as
# quatro regras do `deny` já o pegam, e duas proteções da mesma casa
# discordando é pior que uma barrando demais. Fica de fora, de propósito, o
# nome que só COMEÇA parecido: `.envision.md` é página, não credencial.
NOME_DE_CREDENCIAL = re.compile(r"^(\.env|\.envrc|\.env\..+|appsettings(\..+)?\.json)$")

# Pasta inteira: qualquer pedaço do caminho chamado exatamente assim.
PASTA_DE_CREDENCIAL = ".credenciais"

# As marcas que fazem valer a pena olhar. Sem nenhuma delas o gancho sai na
# primeira linha — ele roda antes de TODO comando de shell da sessão.
MARCAS = (".env", "appsettings", PASTA_DE_CREDENCIAL)

# Documento entregue com o delimitador entre aspas (`<<'FIM'`) é dado literal.
# Sem esta exceção o gancho barra quem escreve o recibo dele — foi assim que
# o veto de branch mordeu o próprio autor. Só o CORPO sai da varredura; o
# resto da linha de abertura fica, senão `cat <<'FIM' > .env` se esconderia
# atrás do documento.
DOCUMENTO_LITERAL = re.compile(
    r"<<-?\s*(['\"])(\w+)\1([^\n]*)\n.*?(?:^\2\s*$|\Z)", re.S | re.M)

# O que vem depois de uma bandeira de mensagem é mensagem, não alvo: a issue
# pede que `git commit -m "explica o .env"` passe. A ressalva é a que o veto
# de branch aprendeu na marra — dentro de aspas duplas o `$(...)` ainda
# executa, então `-m "$(cat .env)"` NÃO é mensagem, é leitura disfarçada.
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


def tirar_mensagem(trecho) -> str:
    """Apaga o valor de uma bandeira de mensagem — só quando é mesmo texto.

    A ressalva é a que o veto de branch aprendeu na marra: dentro de aspas
    duplas o `$(...)` ainda executa. `-m "$(cat .env)"` não é mensagem, é
    leitura disfarçada — e essa fica, para ser varrida.
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


def motivo_da_recusa(comando: str) -> str:
    """Devolve o alvo se o comando abre arquivo de credencial.

    A ordem é o desenho: tira o que é DADO — corpo de documento literal e
    mensagem —, tira as aspas do que sobrou, que é comando, e varre.

    Varrer token a token não serve, e isto foi medido: o `shlex` corta o
    token na aspa, e `cat ".en"v` chegava partido em pedaços que não casavam
    com nada, embora o shell abra o arquivo igual.
    """
    if not comando or not vale_olhar(comando):
        return ""
    texto = DOCUMENTO_LITERAL.sub(r"\3", comando)
    texto = MENSAGEM_COLADA.sub(tirar_mensagem, texto)
    texto = MENSAGEM_SEPARADA.sub(tirar_mensagem, texto)
    return e_credencial(sem_aspas(texto))


def main() -> int:
    try:
        entrada = json.load(sys.stdin)
        comando = entrada.get("tool_input", {}).get("command", "")
    except (json.JSONDecodeError, AttributeError, TypeError):
        return 0  # falha aberto: entrada quebrada não prende a sessão

    alvo = motivo_da_recusa(comando)
    if not alvo:
        return 0  # passagem é silêncio: sair 0 sem imprimir nada

    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"Isto abre '{alvo}', que é arquivo de credencial. O AGENTS.md "
            "manda nunca abrir .env*, appsettings* nem .credenciais/ — e o "
            "segredo que entra na sessão entra também no histórico dela. "
            "O caminho: trabalhe com o NOME da variável (${VARIAVEL}), nunca "
            "com o valor; se precisar mesmo do conteúdo, peça ao dono, que "
            "roda o comando ele mesmo. Para só falar do assunto num texto, "
            "use a bandeira de mensagem ou um documento com o delimitador "
            "entre aspas (<<'FIM')."
        ),
    }}))
    return 0


# --- Testes -----------------------------------------------------------------
# Duas listas, e a segunda é a que importa: gancho largo demais é desligado na
# primeira semana. Cada caso que barra tem um par que passa pelo mesmo
# mecanismo, com alvo que não é credencial.

BARRA = [
    ("abrir direto", "cat .env"),
    ("abrir com aspas", "cat '.env'"),
    ("abrir por dentro do python", 'python -c "print(open(\'.env\').read())"'),
    ("buscar dentro da pasta de credencial", "grep -r SENHA .credenciais/"),
    ("caminho relativo para cima", "less ../.credenciais/gh-bot"),
    ("configuração do .NET", "type appsettings.Production.json"),
    ("no PowerShell", "Get-Content .env.local"),
    ("escondido depois de &&", "git status && cat .env"),
    ("dentro de outro shell", "bash -c 'cat .env'"),
    # A armadilha que o veto de branch já tinha ensinado: dentro de aspas
    # duplas o `$(...)` executa. Bandeira de mensagem não protege isso.
    ("mensagem que na verdade executa", 'git commit -m "$(cat .env)"'),
    ("mensagem colada que na verdade executa",
     'git commit --message="$(cat .env)"'),
    # `--body-file` come um ARQUIVO, não uma mensagem. Um caractere de
    # diferença para `--body`, e o efeito é oposto.
    ("bandeira que parece mensagem mas é arquivo",
     "gh issue comment 13 --body-file .env"),
    ("copiar para fora também é abrir", "cp .env /tmp/copia"),
    ("exemplo entra junto, por decisão do dono", "cat .env.exemplo"),
    # O shell cola os pedaços: `.en''v` abre o mesmo arquivo que `.env`.
    # Medido — o veto de branch ainda tem este furo, e foi por isso que
    # aqui as aspas saem TODAS, não só o par de fora.
    ("aspas coladas no meio do nome", "cat .en''v"),
    ("aspas que cortam o nome em dois", 'cat ".en"v'),
    # `-m` nem sempre é mensagem: no `ls` é bandeira comum, e o que vem
    # depois é alvo de verdade. Por isso a mensagem separada exige aspas.
    ("bandeira que só parece mensagem", "ls -m .env"),
]

DEIXA_PASSAR = [
    ("abrir arquivo comum", "cat README.md"),
    ("abrir arquivo comum com aspas", "cat 'README.md'"),
    ("buscar palavra no conhecimento", "rg TOKEN conhecimento/"),
    ("buscar palavra parecida", 'grep -rn "environment" fluxos/'),
    ("pasta que só começa parecido", "ls .credenciais-explicado/"),
    ("página que fala do assunto", "cat conhecimento/appsettings-explicado.md"),
    ("nome que só começa parecido", "cat .envision.md"),
    # O caso que a issue exige na lista que passa: falar de credencial num
    # texto não é abrir credencial.
    ("mensagem de commit que cita o arquivo",
     'git commit -m "explica o .env no LEIAME"'),
    ("mensagem colada na bandeira com igual",
     'git commit --message="ajusta o .env de exemplo"'),
    ("corpo de comentário pelo gh", 'gh issue comment 13 --body "o gancho barra .env"'),
    # Foi este caso que barrou o recibo do veto de branch. O recibo DESTE
    # gancho é entregue exatamente assim.
    ("documento literal é dado, não comando",
     "gh issue comment 13 --body-file - <<'FIM'\ncat .env\nFIM"),
    ("o ritual da casa", "python montar.py --sincronizar"),
    ("o próprio autoteste", "python .claude/hooks/vetar-credencial.py --testar"),
    # O par do furo acima: aspa colada no meio de um nome que não é
    # credencial continua passando. Sem este caso, o conserto viraria
    # suspeita de todo nome com aspa no meio.
    ("aspas coladas em nome comum", "cat REA''DME.md"),
    ("aspas que cortam nome comum em dois", 'cat "REA"DME.md'),
    ("bandeira comum com alvo comum", "ls -m conhecimento/"),
]


def testar() -> int:
    falhas = []
    for rotulo, comando in BARRA:
        if not motivo_da_recusa(comando):
            falhas.append(f"  DEVIA BARRAR e passou — {rotulo}: {comando}")
    for rotulo, comando in DEIXA_PASSAR:
        alvo = motivo_da_recusa(comando)
        if alvo:
            falhas.append(f"  DEVIA PASSAR e barrou — {rotulo}: {comando} ({alvo})")
    total = len(BARRA) + len(DEIXA_PASSAR)
    if falhas:
        print(f"FALHOU: {len(falhas)} de {total} casos")
        print("\n".join(falhas))
        return 1
    print(f"OK: {total} casos — {len(BARRA)} barrados, {len(DEIXA_PASSAR)} liberados")
    return 0


if __name__ == "__main__":
    sys.exit(testar() if "--testar" in sys.argv else main())
