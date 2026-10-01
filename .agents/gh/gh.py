import json
import os
import re
import shlex
import subprocess
import sys

BANDEIRA_DE_TESTE = "--testar"
USO = ("roda o `gh` na conta declarada, e devolve o berro legível quando ele "
       "recusa. Importado por quem fala com issue, etiqueta ou quadro — o "
       "token sai do `gh auth token --user`, e nunca de variável no disco. "
       "Também escreve um bloco marcado no corpo da issue (lê, grava só o "
       "bloco, relê) e o comentário que marca o dono, pela API REST: a "
       "sessão na nuvem recusa o GraphQL que `gh issue` usa por baixo")

GH_PADRAO = "gh"
VARIAVEL_DO_GH = "ATLAS_GH"
VARIAVEL_DA_NUVEM = "CLAUDE_CODE_REMOTE"
VALOR_DA_NUVEM = "true"
SISTEMA_WINDOWS = "nt"
ASPAS = "\"'"
TEMPO_DO_GH = 60
LIMITE_DO_ERRO = 300
NAO_RODOU = "o gh não rodou"
RECUSA_SEM_TOKEN = (
    "a conta {conta} foi pedida e o token dela não se obteve pelo "
    "`gh auth token --user`: a operação não sai por outra conta. "
    "Entre com `gh auth login` nessa conta")

MARCA_QUE_ABRE = "<!-- {} -->"
MARCA_QUE_FECHA = "<!-- /{} -->"
TETO_DO_BLOCO = 12_000
AVISO_DO_TETO = "\n\n_(cortado no teto de {} caracteres do bloco)_"
TENTATIVAS_DO_BLOCO = 3
LIMITE_DO_CORPO_EM_BYTES = 262_144
CAMPO_DAS_ISSUES = "issues"
CAMPO_DE_QUEM_SE_MARCA = "quem_se_marca"
LOGIN_QUE_SERVE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
VALOR_POR_PREENCHER = "${"
FALHA_AO_LER_O_CORPO = "não li o corpo da issue {issue}: {motivo}"
FALHA_AO_GRAVAR_O_CORPO = "não gravei o corpo da issue {issue}: {motivo}"
FALHA_AO_COMENTAR = "não consegui comentar na issue {issue}: {motivo}"
BLOCO_NAO_FICOU = (
    "gravei o bloco `{nome}` no corpo da issue {issue} e reli {vezes} "
    "vez(es), e ele NÃO está lá como escrevi. Outra escrita no mesmo corpo é "
    "a explicação mais provável: quem grava por último vence. Leia o corpo e "
    "rode de novo")
BLOCO_REGRAVADO = (
    "a releitura achou o bloco `{nome}` fora do corpo da issue {issue} depois "
    "de gravado — outra escrita no mesmo corpo — e eu o regravei {vezes} "
    "vez(es) a partir do corpo novo")
CORPO_CHEIO = (
    "não gravei: com o bloco `{nome}`, o corpo da issue {issue} passaria de "
    "{limite} bytes, o teto do rastreador. Pode o corpo antes")
AVISO_SEM_QUEM_SE_MARCA = (
    "o comentário saiu sem marcar ninguém: `issues.quem_se_marca` não está "
    "preenchido em nucleo/executor.json, e sem a marca o dono só o vê se "
    "abrir a issue")


def _sem_as_aspas_que_envolvem(token: str) -> str:
    if len(token) >= 2 and token[0] in ASPAS and token[-1] == token[0]:
        return token[1:-1]
    return token


def partir_comando(valor: str, windows: bool = os.name == SISTEMA_WINDOWS) -> list:
    if not windows:
        return shlex.split(valor)
    return [_sem_as_aspas_que_envolvem(t) for t in shlex.split(valor, posix=False)]


def linha_de_comando(*partes) -> str:
    return " ".join(f'"{parte}"' for parte in partes)


def _comando() -> list:
    return partir_comando(os.environ.get(VARIAVEL_DO_GH, GH_PADRAO))


def sem_retorno_de_carro(entrada):
    return entrada.replace("\r", "") if isinstance(entrada, str) else entrada


def rodar(argumentos: list, ambiente: dict = None, entrada=None):
    try:
        return subprocess.run(
            _comando() + argumentos, input=sem_retorno_de_carro(entrada),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=TEMPO_DO_GH,
            env=dict(os.environ, **(ambiente or {})))
    except (OSError, subprocess.SubprocessError):
        return None


def na_nuvem() -> bool:
    return os.environ.get(VARIAVEL_DA_NUVEM, "").strip().lower() == VALOR_DA_NUVEM


def rota_da_issue(repositorio: str, issue) -> str:
    return f"repos/{repositorio}/issues/{issue}"


def pela_rest(metodo: str, rota: str, dado: dict = None) -> tuple:
    argumentos = ["api", "--method", metodo, rota]
    if dado is None:
        return argumentos, None
    texto = {chave: sem_retorno_de_carro(valor) for chave, valor in dado.items()}
    return argumentos + ["--input", "-"], json.dumps(texto, ensure_ascii=False)


def token_da_conta(conta: str) -> str:
    if not conta:
        return ""
    achou = rodar(["auth", "token", "--user", conta])
    return achou.stdout.strip() if achou and achou.returncode == 0 else ""


def na_conta(conta: str, argumentos: list, entrada=None):
    token = token_da_conta(conta)
    if conta and not token:
        return subprocess.CompletedProcess(
            argumentos, 1, "", RECUSA_SEM_TOKEN.format(conta=conta))
    return rodar(argumentos, {"GH_TOKEN": token} if token else {}, entrada)


def berro(feito) -> str:
    if feito is None:
        return NAO_RODOU
    return ((feito.stderr or feito.stdout).strip()
            or str(feito.returncode))[:LIMITE_DO_ERRO]


def marcas_do_bloco(nome: str) -> tuple:
    return MARCA_QUE_ABRE.format(nome), MARCA_QUE_FECHA.format(nome)


def partes_do_bloco(corpo: str, abre: str, fecha: str) -> tuple:
    inicio = corpo.find(abre)
    fim = corpo.find(fecha)
    if inicio < 0 or fim < 0 or fim < inicio:
        return ()
    return (corpo[:inicio + len(abre)], corpo[inicio + len(abre):fim],
            corpo[fim:])


def no_teto(texto: str) -> str:
    limpo = (texto or "").strip()
    if len(limpo) <= TETO_DO_BLOCO:
        return limpo
    aviso = AVISO_DO_TETO.format(TETO_DO_BLOCO)
    return limpo[:TETO_DO_BLOCO - len(aviso)].rstrip() + aviso


def texto_do_bloco(corpo: str, nome: str):
    partes = partes_do_bloco(corpo or "", *marcas_do_bloco(nome))
    return partes[1].strip() if partes else None


def corpo_com_o_bloco(corpo: str, nome: str, texto: str) -> str:
    abre, fecha = marcas_do_bloco(nome)
    miolo = "\n" + no_teto(texto) + "\n"
    partes = partes_do_bloco(corpo or "", abre, fecha)
    if partes:
        return partes[0] + miolo + partes[2]
    return (corpo or "").rstrip("\n") + "\n\n" + abre + miolo + fecha + "\n"


def ler_o_corpo(conta: str, repositorio: str, issue) -> tuple:
    argumentos, _ = pela_rest("GET", rota_da_issue(repositorio, issue))
    feito = na_conta(conta, argumentos)
    if feito is None or feito.returncode != 0:
        return None, FALHA_AO_LER_O_CORPO.format(issue=issue,
                                                 motivo=berro(feito))
    try:
        corpo = json.loads(feito.stdout or "{}").get("body")
    except (ValueError, AttributeError) as falha:
        return None, FALHA_AO_LER_O_CORPO.format(
            issue=issue, motivo=f"{type(falha).__name__}: {falha}")
    if not isinstance(corpo, str):
        return None, FALHA_AO_LER_O_CORPO.format(
            issue=issue, motivo="o rastreador não devolveu o corpo")
    return corpo.replace("\r", ""), ""


def gravar_o_bloco(conta: str, repositorio: str, issue, nome: str,
                   texto: str) -> tuple:
    esperado = no_teto(texto)
    gravacoes = 0
    while True:
        atual, erro = ler_o_corpo(conta, repositorio, issue)
        if erro:
            return False, erro
        if texto_do_bloco(atual, nome) == esperado:
            return True, (BLOCO_REGRAVADO.format(nome=nome, issue=issue,
                                                 vezes=gravacoes - 1)
                          if gravacoes > 1 else "")
        if gravacoes >= TENTATIVAS_DO_BLOCO:
            return False, BLOCO_NAO_FICOU.format(nome=nome, issue=issue,
                                                 vezes=gravacoes)
        proposto = corpo_com_o_bloco(atual, nome, esperado)
        if len(proposto.encode("utf-8")) > LIMITE_DO_CORPO_EM_BYTES:
            return False, CORPO_CHEIO.format(nome=nome, issue=issue,
                                             limite=LIMITE_DO_CORPO_EM_BYTES)
        argumentos, entrada = pela_rest("PATCH", rota_da_issue(repositorio,
                                                               issue),
                                        {"body": proposto})
        feito = na_conta(conta, argumentos, entrada)
        if feito is None or feito.returncode != 0:
            return False, FALHA_AO_GRAVAR_O_CORPO.format(issue=issue,
                                                         motivo=berro(feito))
        gravacoes += 1


def quem_se_marca(configuracao: dict) -> str:
    issues = (configuracao or {}).get(CAMPO_DAS_ISSUES)
    valor = issues.get(CAMPO_DE_QUEM_SE_MARCA) if isinstance(issues, dict) \
        else None
    if not isinstance(valor, str):
        return ""
    valor = valor.strip().lstrip("@")
    if VALOR_POR_PREENCHER in valor or not LOGIN_QUE_SERVE.match(valor):
        return ""
    return valor


def texto_que_marca(texto: str, login: str) -> tuple:
    if not login:
        return texto, AVISO_SEM_QUEM_SE_MARCA
    return f"@{login} {texto}", ""


def comentar_para_o_dono(conta: str, repositorio: str, issue, texto: str,
                         login: str) -> tuple:
    marcado, aviso = texto_que_marca(texto, login)
    argumentos, entrada = pela_rest(
        "POST", rota_da_issue(repositorio, issue) + "/comments",
        {"body": marcado})
    feito = na_conta(conta, argumentos, entrada)
    if feito is None or feito.returncode != 0:
        return False, FALHA_AO_COMENTAR.format(issue=issue,
                                               motivo=berro(feito)), aviso
    return True, "", aviso


FALSO = """import json
import os
import pathlib
import sys

CAIXA = pathlib.Path(os.environ["GH_TESTE_CAIXA"])
CORPO = CAIXA / "corpo.md"
OUTRO = CAIXA / "outro-escritor.txt"
argv = sys.argv[1:]
if argv[:2] == ["auth", "token"] and (CAIXA / "sem-token.txt").exists():
    sys.stderr.write("token indisponivel\\n")
    sys.exit(2)
token = os.environ.get("GH_TOKEN", "")
(CAIXA / "chamadas.txt").open("a").write(
    " ".join(argv) + chr(9)
    + (token if token.startswith("token-") else "sem-token") + chr(10))
recebido = b""
if "--body-file" in argv:
    recebido = sys.stdin.buffer.read()
    (CAIXA / "corpo-recebido.bin").write_bytes(recebido)
if argv[:2] == ["auth", "token"]:
    print("token-de-" + argv[-1])
elif (CAIXA / "recusa.txt").exists():
    sys.stderr.write("nao vai\\n")
    sys.exit(2)
elif argv[:3] == ["api", "--method", "GET"]:
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({"body": CORPO.read_text(encoding="utf-8")
                      if CORPO.exists() else ""}))
elif argv[:3] == ["api", "--method", "PATCH"]:
    if "--input" in argv:
        recebido = sys.stdin.buffer.read()
        (CAIXA / "corpo-recebido.bin").write_bytes(recebido)
    CORPO.write_text(json.loads(recebido.decode("utf-8"))["body"],
                     encoding="utf-8")
    vezes = int(OUTRO.read_text(encoding="utf-8")) if OUTRO.exists() else 0
    if vezes > 0:
        CORPO.write_bytes((CAIXA / "corpo-do-outro.md").read_bytes())
        OUTRO.write_text(str(vezes - 1), encoding="utf-8")
sys.exit(0)
"""


def testar() -> int:
    import tempfile
    from pathlib import Path

    passou = falhou = 0

    def caso(nome: str, condicao: bool) -> None:
        nonlocal passou, falhou
        if condicao:
            passou += 1
        else:
            falhou += 1
            print(f"FALHOU: {nome}")

    os.environ.pop(VARIAVEL_DA_NUVEM, None)
    with tempfile.TemporaryDirectory() as pasta:
        caixa = Path(pasta)
        falso = caixa / "gh-falso.py"
        falso.write_text(FALSO, encoding="utf-8")
        os.environ["GH_TESTE_CAIXA"] = str(caixa)
        os.environ[VARIAVEL_DO_GH] = linha_de_comando(sys.executable, falso)

        caso("caminho do Windows com espaço e contrabarra fica inteiro: o "
             "shlex posix quebrava C:\\Program Files em dois e comia as barras, "
             "e o gh falso nunca rodava",
             partir_comando(
                 '"C:\\Program Files\\Python314\\python.exe" "C:\\x\\gh falso.py"',
                 windows=True)
             == ["C:\\Program Files\\Python314\\python.exe", "C:\\x\\gh falso.py"])
        caso("no Linux o mesmo comando entre aspas também fica inteiro",
             partir_comando('"/tmp/com espaco/python3" "/tmp/x/gh.py"',
                            windows=False)
             == ["/tmp/com espaco/python3", "/tmp/x/gh.py"])
        caso("a linha de comando que os testes montam vai com aspas em cada "
             "parte — é o que sobrevive aos dois sistemas",
             linha_de_comando("a b", "c") == '"a b" "c"')

        caso("sem conta declarada não há token — e o gh usa a conta ativa",
             token_da_conta("") == "")
        caso("com conta declarada, o token sai do `gh auth token --user`",
             token_da_conta("alguem") == "token-de-alguem")

        os.environ["GH_TOKEN"] = "token-do-dono-ficticio"
        chamadas_antes = (caixa / "chamadas.txt").read_text(encoding="utf-8")
        (caixa / "sem-token.txt").write_text("x", encoding="utf-8")
        recusado = na_conta("alguem", ["issue", "comment", "1"])
        chamadas_depois = (caixa / "chamadas.txt").read_text(encoding="utf-8")
        caso("conta pedida sem token recusa antes da operacao mesmo com GH_TOKEN herdado",
             recusado is not None and recusado.returncode != 0
             and "alguem" in berro(recusado)
             and "gh auth login" in berro(recusado)
             and chamadas_depois == chamadas_antes)
        (caixa / "sem-token.txt").unlink()

        chamada_com_token = na_conta("alguem", ["issue", "comment", "1"])
        novas_chamadas = (caixa / "chamadas.txt").read_text(
            encoding="utf-8")[len(chamadas_depois):]
        caso("token obtido prevalece sobre GH_TOKEN herdado na operacao",
             chamada_com_token is not None and chamada_com_token.returncode == 0
             and "issue comment 1\ttoken-de-alguem\n" in novas_chamadas
             and "issue comment 1\ttoken-do-dono-ficticio" not in novas_chamadas)

        chamada_sem_conta = na_conta("", ["issue", "comment", "1"])
        novas_chamadas = (caixa / "chamadas.txt").read_text(
            encoding="utf-8")[len(chamadas_depois + novas_chamadas):]
        caso("conta vazia continua usando o ambiente herdado",
             chamada_sem_conta is not None and chamada_sem_conta.returncode == 0
             and "issue comment 1\ttoken-do-dono-ficticio\n" in novas_chamadas)
        os.environ.pop("GH_TOKEN", None)

        na_conta("alguem", ["issue", "view", "1"])
        chamadas = (caixa / "chamadas.txt").read_text(encoding="utf-8")
        caso("o comando roda com o token da conta pedida, sem trocar a ativa",
             "token-de-alguem" in chamadas)

        rodar(["issue", "edit", "1", "--body-file", "-"],
              entrada="titulo\r\r\r\nlinha\r\n\r\r\nfim\n")
        recebido = (caixa / "corpo-recebido.bin").read_bytes()
        caso("corpo lido do rastreador volta com retorno de carro sobrando, "
             "e a escrita em modo texto soma mais um por linha: o que vai "
             "pelo stdin sai LIMPO, senão cada gravação engorda o corpo até "
             "o teto do rastreador com caractere que ninguém vê",
             b"\r\r" not in recebido
             and recebido.replace(b"\r", b"") == b"titulo\nlinha\n\nfim\n")

        (caixa / "recusa.txt").write_text("x", encoding="utf-8")
        feito = na_conta("alguem", ["issue", "comment", "1"])
        caso("recusa do gh vira berro legível, nunca silêncio",
             feito is not None and "nao vai" in berro(feito))
        caso("berro de comando que nem rodou também tem texto",
             berro(None) == NAO_RODOU)

        (caixa / "recusa.txt").unlink()
        abre, fecha = marcas_do_bloco("o bloco")
        corpo = "# topo\n\n## Estado\nfeito\n"
        caso("corpo sem o bloco não tem partes: quem escreve sabe que vai criar",
             partes_do_bloco(corpo, abre, fecha) == ())
        com_ele = corpo_com_o_bloco(corpo, "o bloco", "primeira versão")
        caso("bloco que não existe nasce no fim, entre as marcas, e o resto do "
             "corpo fica como estava",
             com_ele.startswith(corpo.rstrip("\n"))
             and texto_do_bloco(com_ele, "o bloco") == "primeira versão"
             and com_ele.rstrip("\n").endswith(fecha))
        outro = corpo_com_o_bloco(com_ele, "o vizinho", "do vizinho")
        trocado = corpo_com_o_bloco(outro, "o bloco", "segunda versão")
        caso("reescrever o bloco troca a seção INTEIRA e não toca o bloco "
             "vizinho nem o texto de gente",
             texto_do_bloco(trocado, "o bloco") == "segunda versão"
             and "primeira versão" not in trocado
             and texto_do_bloco(trocado, "o vizinho") == "do vizinho"
             and trocado.startswith("# topo\n\n## Estado\nfeito\n"))
        caso("marca de fechar antes da de abrir não é bloco: escrever ali "
             "apagaria texto de gente",
             partes_do_bloco(fecha + "\nmeio\n" + abre, abre, fecha) == ())
        longo = no_teto("x" * (TETO_DO_BLOCO * 2))
        caso("texto maior que o teto do bloco sai cortado e diz que cortou — "
             "o corpo tem teto, e bloco sem teto o enche",
             len(longo) <= TETO_DO_BLOCO and longo.endswith(
                 AVISO_DO_TETO.format(TETO_DO_BLOCO)))

        (caixa / "corpo.md").write_text(corpo, encoding="utf-8")
        ok, dito = gravar_o_bloco("alguem", "dono/repo", 7, "o bloco", "vale")
        caso("gravar o bloco lê, grava e relê: ele fica no corpo da issue",
             ok and texto_do_bloco((caixa / "corpo.md").read_text(
                 encoding="utf-8"), "o bloco") == "vale")
        chamadas = (caixa / "chamadas.txt").read_text(encoding="utf-8")
        caso("o corpo se lê e se grava pela API REST, na rota da issue, e "
             "nunca por `gh issue view` ou `gh issue edit`: os dois usam "
             "GraphQL, e a sessão na nuvem recusa GraphQL",
             "api --method GET repos/dono/repo/issues/7\t" in chamadas
             and "api --method PATCH repos/dono/repo/issues/7 --input -"
             in chamadas
             and "issue view 7" not in chamadas
             and "issue edit 7" not in chamadas)
        (caixa / "corpo.md").write_text(corpo, encoding="utf-8")
        gravar_o_bloco("alguem", "dono/repo", 7, "o bloco", "a\r\nb")
        enviado = json.loads((caixa / "corpo-recebido.bin").read_bytes()
                             .decode("utf-8"))["body"]
        caso("o corpo que sobe em JSON também sai sem retorno de carro: "
             "dentro do JSON ele vira escape, e a limpeza do stdin não o via",
             "\r" not in enviado and "a\nb" in enviado)

        _, entrada = pela_rest("POST", "x", {"body": "ação"})
        caso("o texto vai em UTF-8 legível, não em escape de ASCII",
             "ação" in entrada)
        for valor, esperado in (("true", True), ("TRUE", True),
                                ("false", False), ("", False)):
            os.environ[VARIAVEL_DA_NUVEM] = valor
            caso(f"`{VARIAVEL_DA_NUVEM}={valor}` diz nuvem {esperado}",
                 na_nuvem() is esperado)
        os.environ.pop(VARIAVEL_DA_NUVEM, None)

        do_outro = corpo_com_o_bloco(corpo, "o do outro", "escrito pelo outro")
        (caixa / "corpo-do-outro.md").write_text(do_outro, encoding="utf-8")
        (caixa / "corpo.md").write_text(corpo, encoding="utf-8")
        (caixa / "outro-escritor.txt").write_text("99", encoding="utf-8")
        ok, dito = gravar_o_bloco("alguem", "dono/repo", 7, "o bloco", "meu")
        caso("DOIS ESCRITORES: o segundo grava por cima toda vez, e a "
             "releitura acusa em vez de dar por gravado",
             not ok and "NÃO está lá" in dito)

        (caixa / "corpo.md").write_text(corpo, encoding="utf-8")
        (caixa / "outro-escritor.txt").write_text("1", encoding="utf-8")
        ok, dito = gravar_o_bloco("alguem", "dono/repo", 7, "o bloco", "meu")
        final = (caixa / "corpo.md").read_text(encoding="utf-8")
        caso("o segundo grava por cima uma vez: a releitura acusa, regrava a "
             "partir do corpo novo, e o bloco do outro sobrevive",
             ok and "regravei" in dito
             and texto_do_bloco(final, "o bloco") == "meu"
             and texto_do_bloco(final, "o do outro") == "escrito pelo outro")
        (caixa / "outro-escritor.txt").unlink()

        (caixa / "corpo.md").write_text("y" * LIMITE_DO_CORPO_EM_BYTES,
                                        encoding="utf-8")
        antes = (caixa / "chamadas.txt").read_text(encoding="utf-8")
        ok, dito = gravar_o_bloco("alguem", "dono/repo", 7, "o bloco", "meu")
        depois = (caixa / "chamadas.txt").read_text(encoding="utf-8")
        caso("corpo que passaria do teto do rastreador não se grava, e nada "
             "sobe",
             not ok and str(LIMITE_DO_CORPO_EM_BYTES) in dito
             and "edit" not in depois[len(antes):])

        caso("o login de quem se marca sai da configuração local",
             quem_se_marca({"issues": {"quem_se_marca": "a-pessoa"}})
             == "a-pessoa")
        caso("login com molde por preencher, ausente ou fora do formato não "
             "marca ninguém",
             quem_se_marca({"issues": {"quem_se_marca": "${LOGIN}"}}) == ""
             and quem_se_marca({}) == ""
             and quem_se_marca({"issues": "x"}) == ""
             and quem_se_marca({"issues": {"quem_se_marca": "a b"}}) == "")
        texto, aviso = texto_que_marca("espera por você", "a-pessoa")
        caso("com login, o comentário abre marcando a pessoa, e não há aviso",
             texto.startswith("@a-pessoa ") and not aviso)
        texto, aviso = texto_que_marca("espera por você", "")
        caso("sem login, o comentário sai sem marca e o aviso diz o campo",
             "@" not in texto and "quem_se_marca" in aviso)

        os.environ[VARIAVEL_DO_GH] = "/caminho/que/nao/existe/gh"
        caso("gh que não existe devolve None, e não estoura na cara de quem "
             "chamou",
             rodar(["auth", "status"]) is None)
        os.environ.pop(VARIAVEL_DO_GH, None)
        os.environ.pop("GH_TESTE_CAIXA", None)

    print(f"{'OK' if not falhou else 'FALHOU'}: {passou + falhou} casos")
    return 1 if falhou else 0


if __name__ == "__main__":
    for canal in (sys.stdin, sys.stdout, sys.stderr):
        if not getattr(canal, "closed", True) and hasattr(canal, "reconfigure"):
            canal.reconfigure(encoding="utf-8", errors="replace")
    if BANDEIRA_DE_TESTE in sys.argv[1:]:
        sys.exit(testar())
    print(USO)
