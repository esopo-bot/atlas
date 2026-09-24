
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

BANDEIRA_DE_TESTE = "--testar"
PASTA_DOS_PROJETOS = Path.home() / ".claude" / "projects"
SUFIXO_DE_TRANSCRITO = ".jsonl"
PASTA_DOS_SUBAGENTES = "subagents"
PASTA_DOS_ROTEIROS = "workflows"
MOLDE_DOS_AGENTES = "agent-*" + SUFIXO_DE_TRANSCRITO
ARQUIVO_DO_DIARIO = "journal.jsonl"
PREFIXO_DE_ROTEIRO = "wf_"
SEPARADOR_DE_ARVORE = "--"

CAMPO_DA_MENSAGEM = "message"
CAMPO_DO_USO = "usage"
CAMPO_DO_CONTEUDO = "content"
CAMPO_DO_TIPO = "type"
TIPO_DE_USO_DE_FERRAMENTA = "tool_use"
CAMPO_DO_NOME = "name"
CAMPO_DO_AGENTE = "agentId"
CAMPO_DA_FASE = "phase"
TIPO_INICIADO = "started"
TIPO_FALHOU = "failed"
TIPO_RESULTADO = "result"

PARCELAS_DO_USO = ("input_tokens", "output_tokens",
                   "cache_creation_input_tokens", "cache_read_input_tokens")
PARCELAS_NOVAS = ("input_tokens", "output_tokens",
                  "cache_creation_input_tokens")

SEM_PASTA = (
    "erro de ambiente: não achei {alvo}. É lá que o cliente de terminal grava "
    "os transcritos, e sem eles não há o que contar. Se o cliente grava em "
    "outro lugar nesta máquina, aponte com --projeto."
)
SEM_PROJETO = (
    "erro de ambiente: não achei a pasta de transcritos de {cwd} em {alvo}. "
    "O nome dela vem do caminho de trabalho, então sessão aberta em outra "
    "pasta grava em outra. As que existem: {quantas}. Aponte a sua com "
    "--projeto <nome da pasta>."
)
SEM_SESSAO = (
    "erro de uso: não achei a sessão {id} em {projeto}. Liste as que existem "
    "com --panorama."
)
NADA_MEDIDO = "não medido: {alvo} não abriu ({erro})"

TITULO_DO_PANORAMA = "%-9s %-8s %-15s %-13s %s" % (
    "AGENTES", "FALHAS", "TOKENS", "QUANDO", "SESSÃO")
LINHA_DO_PANORAMA = "%-9d %-8d %-15d %-13s %s"
TITULO_POR_AGENTE = "%-15s %-8s %-8s %s" % (
    "TOKENS", "TURNOS", "FERRAM", "AGENTE")
LINHA_POR_AGENTE = "%-15d %-8d %-8d %s"

QUANTOS_NO_PANORAMA = 25
QUANTOS_POR_AGENTE = 15


def pasta_do_projeto(cwd: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in cwd)


def raiz_dos_transcritos(escolhida: str, cwd: str) -> Path:
    if not PASTA_DOS_PROJETOS.is_dir():
        raise SystemExit(SEM_PASTA.format(alvo=PASTA_DOS_PROJETOS.name))
    nome = escolhida or pasta_do_projeto(cwd)
    alvo = PASTA_DOS_PROJETOS / nome
    if not alvo.is_dir():
        quantas = len([p for p in PASTA_DOS_PROJETOS.iterdir() if p.is_dir()])
        raise SystemExit(SEM_PROJETO.format(
            cwd=Path(cwd).name, alvo=PASTA_DOS_PROJETOS.name, quantas=quantas))
    return alvo


def uso_da_linha(linha: str) -> dict:
    try:
        registro = json.loads(linha)
    except ValueError:
        return {}
    if not isinstance(registro, dict):
        return {}
    mensagem = registro.get(CAMPO_DA_MENSAGEM)
    if not isinstance(mensagem, dict):
        return {}
    uso = mensagem.get(CAMPO_DO_USO)
    return uso if isinstance(uso, dict) else {}


def somar_um(caminho: Path, parcelas=PARCELAS_DO_USO):
    total = turnos = 0
    try:
        with caminho.open(encoding="utf-8") as arquivo:
            for linha in arquivo:
                uso = uso_da_linha(linha)
                if not uso:
                    continue
                turnos += 1
                total += sum(uso.get(p, 0) for p in parcelas)
    except OSError as erro:
        print(NADA_MEDIDO.format(alvo=caminho.name, erro=erro),
              file=sys.stderr)
        return None, None
    return total, turnos


def somar_varios(caminhos, parcelas=PARCELAS_DO_USO) -> int:
    total = 0
    for caminho in caminhos:
        parcial, _ = somar_um(caminho, parcelas)
        if parcial:
            total += parcial
    return total


def ferramentas_de(caminho: Path) -> Counter:
    achadas = Counter()
    try:
        with caminho.open(encoding="utf-8") as arquivo:
            for linha in arquivo:
                try:
                    registro = json.loads(linha)
                except ValueError:
                    continue
                mensagem = (registro or {}).get(CAMPO_DA_MENSAGEM) or {}
                conteudo = mensagem.get(CAMPO_DO_CONTEUDO)
                if not isinstance(conteudo, list):
                    continue
                for parte in conteudo:
                    if not isinstance(parte, dict):
                        continue
                    if parte.get(CAMPO_DO_TIPO) == TIPO_DE_USO_DE_FERRAMENTA:
                        achadas[str(parte.get(CAMPO_DO_NOME, ""))] += 1
    except OSError:
        return achadas
    return achadas


def roteiros_da_sessao(raiz: Path, sessao: str):
    pasta = raiz / sessao / PASTA_DOS_SUBAGENTES / PASTA_DOS_ROTEIROS
    if not pasta.is_dir():
        return []
    return sorted(p for p in pasta.iterdir()
                  if p.is_dir() and p.name.startswith(PREFIXO_DE_ROTEIRO))


def agentes_da_sessao(raiz: Path, sessao: str):
    achados = []
    for roteiro in roteiros_da_sessao(raiz, sessao):
        achados.extend(sorted(roteiro.glob(MOLDE_DOS_AGENTES)))
    soltos = raiz / sessao / PASTA_DOS_SUBAGENTES
    if soltos.is_dir():
        achados.extend(sorted(soltos.glob("*" + SUFIXO_DE_TRANSCRITO)))
    return achados


def contar_o_diario(roteiro: Path):
    iniciados = falhados = concluidos = 0
    fases = Counter()
    diario = roteiro / ARQUIVO_DO_DIARIO
    try:
        with diario.open(encoding="utf-8") as arquivo:
            for linha in arquivo:
                try:
                    registro = json.loads(linha)
                except ValueError:
                    continue
                tipo = (registro or {}).get(CAMPO_DO_TIPO)
                if tipo == TIPO_INICIADO:
                    iniciados += 1
                    fases[str(registro.get(CAMPO_DA_FASE) or "sem fase")] += 1
                elif tipo == TIPO_FALHOU:
                    falhados += 1
                elif tipo == TIPO_RESULTADO:
                    concluidos += 1
    except OSError:
        return 0, 0, 0, fases
    return iniciados, falhados, concluidos, fases


def sessoes_com_roteiro(raiz: Path):
    achadas = []
    for pasta in sorted(raiz.iterdir()):
        if not pasta.is_dir():
            continue
        roteiros = roteiros_da_sessao(raiz, pasta.name)
        if roteiros:
            achadas.append((pasta.name, roteiros))
    return achadas


def raiz_e_arvores_de_trabalho(raiz: Path):
    irmas = [raiz]
    if not raiz.parent.is_dir():
        return irmas
    marca = raiz.name + SEPARADOR_DE_ARVORE
    for vizinha in sorted(raiz.parent.iterdir()):
        if vizinha.is_dir() and vizinha.name.startswith(marca):
            irmas.append(vizinha)
    return irmas


def quando(caminho: Path) -> str:
    try:
        import datetime
        marca = datetime.datetime.fromtimestamp(caminho.stat().st_mtime)
        return marca.strftime("%d/%m %H:%M")
    except (OSError, ValueError):
        return "não medido"


def panorama(raiz: Path) -> int:
    linhas = []
    pastas = raiz_e_arvores_de_trabalho(raiz)
    for pasta in pastas:
        for sessao, roteiros in sessoes_com_roteiro(pasta):
            for roteiro in roteiros:
                iniciados, falhados, _, _ = contar_o_diario(roteiro)
                total = somar_varios(roteiro.glob(MOLDE_DOS_AGENTES))
                linhas.append((iniciados, falhados, total,
                               quando(roteiro / ARQUIVO_DO_DIARIO), sessao))
    if not linhas:
        print("nenhum roteiro nesta pasta de transcritos.")
        return 0
    linhas.sort(reverse=True)
    print(TITULO_DO_PANORAMA)
    for linha in linhas[:QUANTOS_NO_PANORAMA]:
        print(LINHA_DO_PANORAMA % linha)
    if len(linhas) > QUANTOS_NO_PANORAMA:
        print("... e mais %d roteiro(s) menores" %
              (len(linhas) - QUANTOS_NO_PANORAMA))
    print()
    print("roteiros: %d | agentes somados: %d | tokens somados: %d"
          % (len(linhas), sum(l[0] for l in linhas), sum(l[2] for l in linhas)))
    print("pastas de transcrito lidas: %d — a raiz e %d árvore(s) de trabalho, "
          "que gravam em pasta própria e some(m) de uma conta só da raiz"
          % (len(pastas), len(pastas) - 1))
    return 0


def gasto_da_sessao(raiz: Path, sessao: str) -> int:
    principal = raiz / (sessao + SUFIXO_DE_TRANSCRITO)
    if not principal.is_file():
        raise SystemExit(SEM_SESSAO.format(id=sessao, projeto=raiz.name))
    agentes = agentes_da_sessao(raiz, sessao)
    for rotulo, alvos in (("a sessão sozinha", [principal]),
                          ("os agentes dela", agentes)):
        novos = somar_varios(alvos, PARCELAS_NOVAS)
        tudo = somar_varios(alvos)
        print("%-18s arquivos=%3d  tokens novos=%11d  com cache lido=%13d"
              % (rotulo, len(alvos), novos, tudo))
    novos_principal = somar_varios([principal], PARCELAS_NOVAS)
    novos_agentes = somar_varios(agentes, PARCELAS_NOVAS)
    soma = novos_principal + novos_agentes
    print()
    print("tokens novos no total: %d" % soma)
    if soma:
        print("fatia que os agentes gastaram, e que o painel da sessão não "
              "mostra: %.1f%%" % (100.0 * novos_agentes / soma))
    return 0


def por_agente(raiz: Path, sessao: str) -> int:
    agentes = agentes_da_sessao(raiz, sessao)
    if not agentes:
        print("a sessão %s não disparou agente nenhum." % sessao)
        return 0
    linhas = []
    for caminho in agentes:
        total, turnos = somar_um(caminho)
        if total is None:
            continue
        ferramentas = ferramentas_de(caminho)
        linhas.append((total, turnos, sum(ferramentas.values()), caminho.stem))
    linhas.sort(reverse=True)
    print(TITULO_POR_AGENTE)
    for linha in linhas[:QUANTOS_POR_AGENTE]:
        print(LINHA_POR_AGENTE % linha)
    if len(linhas) > QUANTOS_POR_AGENTE:
        print("... e mais %d agente(s) mais baratos"
              % (len(linhas) - QUANTOS_POR_AGENTE))
    totais = sorted(l[0] for l in linhas)
    turnos = sorted(l[1] for l in linhas)
    print()
    print("agentes: %d | mediana de tokens: %d | mediana de turnos: %d"
          % (len(linhas), totais[len(totais) // 2], turnos[len(turnos) // 2]))
    for roteiro in roteiros_da_sessao(raiz, sessao):
        iniciados, falhados, concluidos, fases = contar_o_diario(roteiro)
        print()
        print("roteiro %s: %d iniciados, %d com resultado, %d falharam"
              % (roteiro.name, iniciados, concluidos, falhados))
        for fase, quantos in fases.most_common():
            print("   %-24s %d agente(s)" % (fase[:24], quantos))
    return 0


def montar_o_leitor() -> argparse.ArgumentParser:
    leitor = argparse.ArgumentParser(
        description="O gasto de uma sessão e dos agentes que ela disparou. "
                    "Conta tokens; nunca imprime conteúdo de conversa.")
    leitor.add_argument("--panorama", action="store_true",
                        help="todo roteiro já disparado, do mais caro ao menos")
    leitor.add_argument("--sessao", metavar="ID",
                        help="o gasto de uma sessão, separando os agentes")
    leitor.add_argument("--agentes", metavar="ID",
                        help="custo, turnos e fases de cada agente da sessão")
    leitor.add_argument("--projeto", metavar="PASTA", default="",
                        help="a pasta de transcritos, quando a derivada não serve")
    leitor.add_argument(BANDEIRA_DE_TESTE, action="store_true",
                        help="roda a bancada deste instrumento")
    return leitor


def main() -> int:
    argumentos = montar_o_leitor().parse_args()
    raiz = raiz_dos_transcritos(argumentos.projeto, os.getcwd())
    if argumentos.panorama:
        return panorama(raiz)
    if argumentos.sessao:
        return gasto_da_sessao(raiz, argumentos.sessao)
    if argumentos.agentes:
        return por_agente(raiz, argumentos.agentes)
    montar_o_leitor().print_help()
    return 0


def linha_de_uso(entrada, saida, cache_novo, cache_lido) -> str:
    return json.dumps({CAMPO_DA_MENSAGEM: {CAMPO_DO_USO: {
        "input_tokens": entrada, "output_tokens": saida,
        "cache_creation_input_tokens": cache_novo,
        "cache_read_input_tokens": cache_lido}}})


def linha_de_ferramenta(nome: str) -> str:
    return json.dumps({CAMPO_DA_MENSAGEM: {CAMPO_DO_CONTEUDO: [
        {CAMPO_DO_TIPO: TIPO_DE_USO_DE_FERRAMENTA, CAMPO_DO_NOME: nome}]}})


def montar_arvore(base: Path) -> tuple:
    sessao = "sessao-de-prova"
    (base / sessao / PASTA_DOS_SUBAGENTES / PASTA_DOS_ROTEIROS /
     "wf_prova").mkdir(parents=True)
    roteiro = base / sessao / PASTA_DOS_SUBAGENTES / PASTA_DOS_ROTEIROS / "wf_prova"
    (base / (sessao + SUFIXO_DE_TRANSCRITO)).write_text(
        linha_de_uso(10, 20, 30, 1000) + "\n", encoding="utf-8")
    (roteiro / "agent-um.jsonl").write_text(
        linha_de_uso(1, 2, 3, 500) + "\n" + linha_de_ferramenta("Bash") + "\n",
        encoding="utf-8")
    (roteiro / "agent-dois.jsonl").write_text(
        linha_de_uso(5, 5, 5, 5) + "\nlinha quebrada que não é json\n",
        encoding="utf-8")
    (roteiro / ARQUIVO_DO_DIARIO).write_text(
        json.dumps({CAMPO_DO_TIPO: TIPO_INICIADO, CAMPO_DO_AGENTE: "um",
                    CAMPO_DA_FASE: "Busca"}) + "\n" +
        json.dumps({CAMPO_DO_TIPO: TIPO_INICIADO, CAMPO_DO_AGENTE: "dois",
                    CAMPO_DA_FASE: "Busca"}) + "\n" +
        json.dumps({CAMPO_DO_TIPO: TIPO_RESULTADO, CAMPO_DO_AGENTE: "um"}) +
        "\n" +
        json.dumps({CAMPO_DO_TIPO: TIPO_FALHOU, CAMPO_DO_AGENTE: "dois"}) +
        "\n", encoding="utf-8")
    return sessao, roteiro


def testar() -> int:
    import io
    import tempfile
    from contextlib import redirect_stdout
    falhas = []
    with tempfile.TemporaryDirectory(prefix="gasto-") as pasta:
        base = Path(pasta)
        sessao, roteiro = montar_arvore(base)

        if pasta_do_projeto("D:\\atlas") != "D--atlas":
            falhas.append("o nome da pasta de transcritos nasce do caminho de "
                          "trabalho, com o que não é letra nem número virando "
                          "traço")
        if pasta_do_projeto("/home/x/atlas") != "-home-x-atlas":
            falhas.append("a mesma regra vale num caminho de barra normal")

        total, turnos = somar_um(base / (sessao + SUFIXO_DE_TRANSCRITO))
        if total != 1060 or turnos != 1:
            falhas.append("a soma com cache lido deu %r em %r turno(s)"
                          % (total, turnos))
        novos = somar_varios([base / (sessao + SUFIXO_DE_TRANSCRITO)],
                             PARCELAS_NOVAS)
        if novos != 60:
            falhas.append("os tokens novos deixam o cache lido de fora, e "
                          "deram %r" % novos)

        achados = agentes_da_sessao(base, sessao)
        if len(achados) != 2:
            falhas.append("achou %d agente(s), esperava 2" % len(achados))

        iniciados, falhados, concluidos, fases = contar_o_diario(roteiro)
        if (iniciados, concluidos, falhados) != (2, 1, 1):
            falhas.append("o diário deu %r, esperava (2, 1, 1)"
                          % ((iniciados, concluidos, falhados),))
        if fases.get("Busca") != 2:
            falhas.append("as fases não foram contadas")

        ferramentas = ferramentas_de(roteiro / "agent-um.jsonl")
        if ferramentas.get("Bash") != 1:
            falhas.append("não contou a ferramenta que o agente usou")

        quebrada = somar_um(roteiro / "agent-dois.jsonl")[0]
        if quebrada != 20:
            falhas.append("linha ilegível derruba a conta em vez de ser "
                          "pulada: deu %r" % quebrada)

        ausente = somar_um(base / "nao-existe.jsonl")
        if ausente != (None, None):
            falhas.append("arquivo que não abre tem de virar não medido, "
                          "nunca zero: deu %r" % (ausente,))

        saida = io.StringIO()
        with redirect_stdout(saida):
            gasto_da_sessao(base, sessao)
        texto = saida.getvalue()
        if "fatia que os agentes gastaram" not in texto:
            falhas.append("o resumo da sessão não diz a fatia dos agentes")
        if "linha quebrada" in texto or "Bash" in texto:
            falhas.append("a saída vazou conteúdo de transcrito, e transcrito "
                          "carrega comando e saída de comando")

        saida = io.StringIO()
        with redirect_stdout(saida):
            por_agente(base, sessao)
        if "roteiro wf_prova" not in saida.getvalue():
            falhas.append("o detalhe por agente não mostrou o roteiro")

        saida = io.StringIO()
        with redirect_stdout(saida):
            panorama(base)
        if "roteiros: 1" not in saida.getvalue():
            falhas.append("o panorama não achou o roteiro da árvore de prova")

        vazia = Path(pasta) / "vazia"
        vazia.mkdir()
        saida = io.StringIO()
        with redirect_stdout(saida):
            panorama(vazia)
        if "nenhum roteiro" not in saida.getvalue():
            falhas.append("pasta sem roteiro tem de dizer isso, não estourar")

        raiz_nomeada = Path(pasta) / "projeto"
        raiz_nomeada.mkdir()
        montar_arvore(raiz_nomeada)
        arvore = Path(pasta) / ("projeto" + SEPARADOR_DE_ARVORE + "frente")
        arvore.mkdir()
        montar_arvore(arvore)
        irmas = raiz_e_arvores_de_trabalho(raiz_nomeada)
        if len(irmas) != 2:
            falhas.append(
                "árvore de trabalho grava em pasta de transcrito própria, e a "
                "conta da raiz a perde: achou %d pasta(s), esperava 2"
                % len(irmas))
        saida = io.StringIO()
        with redirect_stdout(saida):
            panorama(raiz_nomeada)
        if "roteiros: 2" not in saida.getvalue():
            falhas.append("o panorama tem de somar a raiz e as árvores de "
                          "trabalho, e somou só uma")

    total_de_casos = 15
    if falhas:
        for linha in falhas:
            print("  " + linha)
        print("FALHOU: %d de %d casos — o gasto da sessão"
              % (len(falhas), total_de_casos))
        return 1
    print("OK: %d casos — o gasto da sessão" % total_de_casos)
    return 0


if __name__ == "__main__":
    for canal in (sys.stdin, sys.stdout, sys.stderr):
        if not getattr(canal, "closed", True) and hasattr(canal, "reconfigure"):
            canal.reconfigure(encoding="utf-8", errors="replace")
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
