import re
import sys
from pathlib import Path

BANDEIRA_DE_TESTE = "--testar"

SEPARADORES_DE_COMANDO = re.compile(r"&&|\|\||;|\||\n|\r|\$\(|`|\)")
ASPA_SIMPLES = "'"
ASPA_DUPLA = '"'
ASPAS = "\"'"
ESCAPE = "\\"

INTERPRETADORES = ("python", "python3", "node", "nodejs", "ruby",
                   "perl", "php")
SHELLS_QUE_RECEBEM_COMANDO = ("sh", "bash", "zsh", "dash", "ksh")
OPCAO_QUE_ENTREGA_O_COMANDO = "c"
AVALIADOR = "eval"
LETRA_DE_OPCAO = "-"

MARCA_DE_ESCRITA_DENTRO_DO_SCRIPT = re.compile(
    r"""write|truncate|unlink|remove|rename|\bmkdir\b|['"]w[+bt]*['"]""")
ATRIBUICAO = re.compile(r"\s*(\w+)\s*=[^=]")
NOME_QUE_ESCREVE = re.compile(
    r"(\w+)\s*\.\s*(?:write_text|write_bytes|write|unlink|rename|mkdir)"
    r"|open\s*\(\s*(\w+)\s*,"
    r"|(?:copy|copyfile|move|rmtree)\s*\([^)]*?(\w+)\s*[,)]")
SUFIXOS_DE_ARQUIVO = (".py", ".md", ".json", ".yml", ".yaml", ".ts",
                      ".js", ".txt", ".jsonc")
TAMANHO_MINIMO_DE_LITERAL = 3
TAMANHO_MAXIMO_DE_LITERAL = 300


def literais_entre_aspas(linha: str) -> list:
    achados, aspa_aberta, atual = [], None, []
    i = 0
    while i < len(linha):
        c = linha[i]
        if aspa_aberta is None:
            if c in ASPAS:
                aspa_aberta, atual = c, []
        elif c == ESCAPE and i + 1 < len(linha):
            atual.append(linha[i + 1])
            i += 1
        elif c == aspa_aberta:
            achados.append("".join(atual))
            aspa_aberta = None
        else:
            atual.append(c)
        i += 1
    com_os_de_dentro = []
    for achado in achados:
        com_os_de_dentro.append(achado)
        if any(aspa in achado for aspa in ASPAS):
            com_os_de_dentro += literais_entre_aspas(achado)
    return [a for a in com_os_de_dentro
            if TAMANHO_MINIMO_DE_LITERAL <= len(a) <= TAMANHO_MAXIMO_DE_LITERAL]


def parece_caminho(texto: str) -> bool:
    return ("'" not in texto and '"' not in texto
            and ("/" in texto or texto.endswith(SUFIXOS_DE_ARQUIVO)))


def literais_que_parecem_caminho(linha: str) -> list:
    return [a for a in literais_entre_aspas(linha) if parece_caminho(a)]


def nome_do_programa(token: str) -> str:
    return Path(token.replace("\\", "/")).name.lower()


def chama_interpretador(comando: str) -> bool:
    for segmento in SEPARADORES_DE_COMANDO.split(comando):
        for token in segmento.split():
            if nome_do_programa(token) in INTERPRETADORES:
                return True
    return False


def nomes_que_a_linha_guarda(linha: str) -> list:
    achou = ATRIBUICAO.match(linha)
    return [achou.group(1)] if achou and literais_que_parecem_caminho(
        linha) else []


def nomes_que_a_linha_escreve(linha: str) -> list:
    return [grupo for m in NOME_QUE_ESCREVE.finditer(linha)
            for grupo in m.groups() if grupo]


def caminhos_escritos_dentro_do_script(comando: str) -> list:
    if not chama_interpretador(comando):
        return []
    if not MARCA_DE_ESCRITA_DENTRO_DO_SCRIPT.search(comando):
        return []
    escritos, por_nome = [], {}
    for linha in comando.splitlines():
        literais = literais_que_parecem_caminho(linha)
        if MARCA_DE_ESCRITA_DENTRO_DO_SCRIPT.search(linha):
            escritos += literais
        for nome in nomes_que_a_linha_guarda(linha):
            por_nome.setdefault(nome, []).extend(literais)
    for linha in comando.splitlines():
        if not MARCA_DE_ESCRITA_DENTRO_DO_SCRIPT.search(linha):
            continue
        for nome in nomes_que_a_linha_escreve(linha):
            escritos += por_nome.get(nome, [])
    return escritos


def sem_o_par_de_aspas_que_envolve(token: str) -> str:
    for aspa in (ASPA_DUPLA, ASPA_SIMPLES):
        if len(token) >= 2 and token.startswith(aspa) and token.endswith(aspa):
            return token[1:-1]
    return token


def tokens_crus_de(segmento: str) -> list:
    import shlex
    try:
        return shlex.split(segmento, posix=False)
    except ValueError:
        return segmento.split()


def entrega_o_comando(opcao: str) -> bool:
    return (opcao.startswith(LETRA_DE_OPCAO)
            and not opcao.startswith(LETRA_DE_OPCAO * 2)
            and OPCAO_QUE_ENTREGA_O_COMANDO in opcao[1:])


def corpos_embrulhados(segmento: str) -> list:
    tokens = tokens_crus_de(segmento)
    corpos = []
    for i, token in enumerate(tokens):
        nome = nome_do_programa(token)
        if nome == AVALIADOR and i + 1 < len(tokens):
            corpos.append(" ".join(
                sem_o_par_de_aspas_que_envolve(t) for t in tokens[i + 1:]))
            break
        if nome in SHELLS_QUE_RECEBEM_COMANDO:
            for j in range(i + 1, len(tokens)):
                if entrega_o_comando(tokens[j]) and j + 1 < len(tokens):
                    corpos.append(sem_o_par_de_aspas_que_envolve(
                        tokens[j + 1]))
                    break
                if not tokens[j].startswith(LETRA_DE_OPCAO):
                    break
            break
    return corpos


def com_os_corpos_desembrulhados(segmentos: list, separar) -> list:
    completos = []
    fila = list(segmentos)
    while fila:
        segmento = fila.pop(0)
        completos.append(segmento)
        for corpo in corpos_embrulhados(segmento):
            fila = list(separar(corpo)) + fila
    return completos


CASOS_DE_LITERAL = (
    ("aspa simples", "open('a/b.py', 'w')", ["a/b.py"]),
    ("aspa dupla", 'open("a/b.py", "w")', ["a/b.py"]),
    ("fechamento não vira abertura",
     "x = 'w'; y = 'z'; p = 'a/b.py'", ["a/b.py"]),
    ("literal dentro do corpo aspeado do -c",
     "python -c \"p = 'a/b.py'; open(p, 'w')\"", ["a/b.py"]),
)

CASOS_DE_EMBRULHO = (
    ("sh -c", "sh -c 'git push --force origin main'",
     ["git push --force origin main"]),
    ("bash -lc", 'bash -lc "echo x > a.yml"', ["echo x > a.yml"]),
    ("eval", "eval 'git push origin main'", ["git push origin main"]),
    ("xargs sh -c", "echo x | xargs -I{} sh -c 'rm {}'", ["rm {}"]),
    ("sem embrulho", "echo 'git push'", []),
    ("bash sem -c roda um arquivo, não um corpo", "bash roteiro.sh", []),
)


def testar() -> int:
    falhas = []
    for rotulo, linha, esperado in CASOS_DE_LITERAL:
        veio = literais_que_parecem_caminho(linha)
        if veio != esperado:
            falhas.append(f"literal [{rotulo}]: esperava {esperado}, "
                          f"veio {veio}")
    for rotulo, segmento, esperado in CASOS_DE_EMBRULHO:
        veio = corpos_embrulhados(segmento)
        if veio != esperado:
            falhas.append(f"embrulho [{rotulo}]: esperava {esperado}, "
                          f"veio {veio}")
    aninhado = com_os_corpos_desembrulhados(
        ["sh -c 'bash -c \"git push --force origin main\"'"],
        lambda c: [c])
    if aninhado[-1] != "git push --force origin main":
        falhas.append(f"embrulho aninhado não abriu: {aninhado}")
    python_em_c = caminhos_escritos_dentro_do_script(
        "python -c \"open('.github/workflows/e.yml','w').write('x')\"")
    if python_em_c != [".github/workflows/e.yml"]:
        falhas.append(f"python -c não achou o alvo: {python_em_c}")
    node_em_e = caminhos_escritos_dentro_do_script(
        "node -e \"require('fs').writeFileSync('projetos/x/a.py','x')\"")
    if node_em_e != ["projetos/x/a.py"]:
        falhas.append(f"node -e não achou o alvo: {node_em_e}")
    so_le = caminhos_escritos_dentro_do_script(
        "python -c \"print(open('projetos/x/a.py').read())\"")
    if so_le:
        falhas.append(f"leitura virou escrita: {so_le}")
    total = len(CASOS_DE_LITERAL) + len(CASOS_DE_EMBRULHO) + 4
    for falha in falhas:
        print("FALHOU: " + falha)
    print(f"{'FALHOU' if falhas else 'OK'}: {total} casos — "
          "desembrulhar comando")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else 0)
