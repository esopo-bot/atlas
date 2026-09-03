import argparse
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

BANDEIRA_DE_TESTE = "--testar"
USO = ("indexa o acervo pelo servidor do índice, um alvo por vez, para rodar "
       "em segundo plano. Fala JSON-RPC direto com o servidor, sem depender "
       "do cliente MCP da sessão — assim a indexação sobrevive à sessão que "
       "a disparou")

ARQUIVO_DOS_ALVOS = ".agents/indice/alvos.json"
CAMPO_DOS_ALVOS = "alvos"
CAMPO_DO_SERVIDOR = "servidor"
CAMPO_DO_AMBIENTE = "ambiente"
CAMPO_DO_QUE_IGNORAR = "ignorar"
CAMPO_DOS_PADROES_IGNORADOS = "ignorePatterns"
CAMPO_DO_LIGADO = "ligado"
ARQUIVO_DA_ULTIMA_RONDA = ".agents/indice/ultima-ronda.json"
TEMPO_DA_RONDA = 300
RONDA_DESLIGADA = ("índice desligado em {}: nada a indexar. Ligue com "
                   "`indexar.py --ligar` quando quiser a ronda no ritual")
LIGADO = "índice LIGADO em {}: a ronda indexa o que mudou em {} alvo(s)"
DESLIGADO = "índice desligado em {}: a ronda não roda"
ESTADO_DA_ULTIMA_RONDA = ("última ronda em {quando}: {feitos} indexado(s), "
                          "{pulados} já estava(m), {sem_elegivel} sem arquivo "
                          "elegível, {falharam} falhou(ram), em {duracao}")
SEM_RONDA_AINDA = "nenhuma ronda registrada ainda"

PROTOCOLO = "2024-11-05"
QUEM_CHAMA = {"name": "indexar", "version": "1"}
FERRAMENTA_DE_INDEXAR = "index_codebase"
FERRAMENTA_DO_ESTADO = "get_indexing_status"
CAMPO_DO_CAMINHO = "path"

TEMPO_DE_HANDSHAKE = 60
TEMPO_POR_ALVO = 8 * 3600
INTERVALO_DA_ESPERA = 5

RECUSA_SEM_ALVOS = ("sem alvos: declare `{}` com a lista de caminhos a "
                    "indexar. O instrumento não adivinha o que é acervo")
RECUSA_SEM_SERVIDOR = ("sem `{}` declarado em {}: diga o caminho do "
                       "`dist/index.js` do servidor do índice. A receita de "
                       "instalar está na página do módulo")
RECUSA_SERVIDOR_AUSENTE = "o servidor declarado não existe: {}"
RECUSA_ALVO_AUSENTE = "alvo que não existe no disco: {}"
NAO_RESPONDEU = "o servidor não respondeu em {}s"
LINHA_DO_ENSAIO = ("  {} — {} arquivo(s) sob ele, {} rastreado(s) no git, {} "
                   "com extensão que o servidor indexa")
AVISO_DO_EXCESSO = ("      ATENÇÃO: {} arquivo(s) que o git não rastreia — "
                    "quase sempre artefato de build ou cache. O servidor "
                    "filtra por extensão, então imagem e binário não entram "
                    "no índice; o custo é a VARREDURA da árvore, e o lixo só "
                    "entra se o excesso for texto ou código. Confira de onde "
                    "vem antes de disparar, e declare `ignorar` em {} se for "
                    "o caso")
FOLGA_QUE_NAO_ASSUSTA = 2
EXTENSAO_DE_JSON = ".json"
PONTO = "."
BARRA = "/"
MARCA_DE_EXCECAO = "!"
COMENTARIO_NO_SERVIDOR = "//"
ARQUIVO_DAS_EXTENSOES_DO_SERVIDOR = ("..", "..", "claude-context-core",
                                     "dist", "context.js")
LISTA_DAS_EXTENSOES_NO_SERVIDOR = re.compile(
    r"DEFAULT_SUPPORTED_EXTENSIONS\s*=\s*\[(.*?)\];", re.S)
EXTENSAO_NA_LISTA = re.compile(r"'(\.[A-Za-z0-9]+)'")
NAO_MEDIDO = "não medido"
AVISO_SEM_ELEGIVEL = ("      ATENÇÃO: nenhum arquivo com extensão que o "
                      "servidor aceite. Ele acha 0, marca 100% e NUNCA diz "
                      "completed — o indexador esperaria o teto inteiro por "
                      "nada. Este alvo será PULADO na rodada")
AVISO_DO_JSON = ("      ATENÇÃO: {} arquivo(s) .json — a extensão .json NÃO "
                 "está na lista do servidor instalado (ela vem comentada no "
                 "código dele), então eles não entram no índice, densos ou "
                 "não. Aponte o alvo para a versão em prosa do mesmo "
                 "conteúdo, se houver")
AVISO_DE_PASTA_OCULTA = ("      ATENÇÃO: {} arquivo(s) elegível(is) sob pasta "
                         "que começa com ponto — o servidor pula toda pasta "
                         "oculta, em qualquer profundidade. Para indexá-la, "
                         "declare-a como alvo próprio")
AVISO_DA_EXCECAO_COM_BARRA = ("      ATENÇÃO: o {} deste alvo reabre pasta "
                              "com barra no fim (`{}`), e o servidor NÃO "
                              "reabre pasta assim: ele testa o nome sem a "
                              "barra, e a exclusão anterior vence. Escreva a "
                              "exceção sem a barra, que o git aceita igual")
PULADO_SEM_ELEGIVEL = "pulado: nenhum arquivo com extensão que o servidor aceite"
CABECA_DO_ENSAIO = "ENSAIO — {} alvo(s), nada será indexado:"
CABECA_DA_RODADA = "indexando {} alvo(s) pelo servidor {}"
LINHA_DO_COMECO = "  [{}/{}] {} — começou"
LINHA_DO_FIM = "  [{}/{}] {} — {} em {}"
FEITO = "indexado"
DISPARADO = "disparado"
MARCA_DE_COMPLETO = "Status: completed"
QUANTOS_O_SERVIDOR_DIZ = re.compile(r"Statistics:\s*(\d+)\s+files")
LINHA_DA_CONTAGEM = ("        {} arquivo(s) elegível(is) sob o alvo, {} "
                     "indexado(s) pelo servidor")
SEM_CONTAGEM_DO_SERVIDOR = ("        o servidor não disse quantos arquivos "
                            "indexou — não dá para comparar")
MARCA_DE_ANDANDO = "currently being indexed"
NAO_TERMINOU = ("o alvo foi disparado mas nao terminou em {} — o servidor "
                "indexa em segundo plano, e matar o processo aqui aborta o "
                "trabalho dele")
JA_ESTAVA = "já estava indexado"
FALHOU = "FALHOU"
MARCA_DE_JA_INDEXADO = "already indexed"
CAMPO_DE_ERRO_DA_FERRAMENTA = "isError"
LINHA_DO_ESTADO = "        {}"
RESUMO_COM_PULADOS = ("{} indexado(s), {} já estava(m), {} pulado(s) sem arquivo "
                      "elegível, {} falhou(ram), em {}")
RESUMO = "{} de {} alvo(s) indexado(s), em {}"


def duracao(segundos: float) -> str:
    return f"{segundos / 60:.1f} min" if segundos >= 60 else f"{segundos:.0f}s"


def configuracao(cwd: str = "") -> dict:
    alvo = Path(cwd or ".") / ARQUIVO_DOS_ALVOS
    try:
        return json.loads(alvo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def gravar_configuracao(dado: dict, cwd: str = "") -> None:
    alvo = Path(cwd or ".") / ARQUIVO_DOS_ALVOS
    alvo.write_text(json.dumps(dado, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def esta_ligado(dado: dict) -> bool:
    return bool(dado.get(CAMPO_DO_LIGADO))


def estado_em_uma_linha(dado: dict) -> str:
    if esta_ligado(dado):
        return LIGADO.format(ARQUIVO_DOS_ALVOS,
                             len(dado.get(CAMPO_DOS_ALVOS) or []))
    return DESLIGADO.format(ARQUIVO_DOS_ALVOS)


def ligar(dado: dict, cwd: str, ligado: bool) -> int:
    dado[CAMPO_DO_LIGADO] = ligado
    gravar_configuracao(dado, cwd)
    print(estado_em_uma_linha(dado))
    return 0


def ultima_ronda(cwd: str = ""):
    alvo = Path(cwd or ".") / ARQUIVO_DA_ULTIMA_RONDA
    try:
        return json.loads(alvo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def gravar_ultima_ronda(cwd: str, resumo: dict) -> None:
    alvo = Path(cwd or ".") / ARQUIVO_DA_ULTIMA_RONDA
    alvo.write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def estado(dado: dict, cwd: str) -> int:
    print(estado_em_uma_linha(dado))
    registro = ultima_ronda(cwd)
    print(ESTADO_DA_ULTIMA_RONDA.format(**registro) if registro
          else SEM_RONDA_AINDA)
    return 0


def recusa_da_configuracao(dado: dict, cwd: str = "") -> str:
    alvos = dado.get(CAMPO_DOS_ALVOS) or []
    if not alvos:
        return RECUSA_SEM_ALVOS.format(ARQUIVO_DOS_ALVOS)
    servidor = dado.get(CAMPO_DO_SERVIDOR) or ""
    if not servidor:
        return RECUSA_SEM_SERVIDOR.format(CAMPO_DO_SERVIDOR, ARQUIVO_DOS_ALVOS)
    if not Path(servidor).expanduser().is_file():
        return RECUSA_SERVIDOR_AUSENTE.format(servidor)
    for caminho in alvos:
        if not Path(caminho).expanduser().is_dir():
            return RECUSA_ALVO_AUSENTE.format(caminho)
    return ""


def arquivos_sob_o_alvo(caminho: str) -> list:
    raiz = Path(caminho).expanduser()
    return [a for a in raiz.rglob("*") if a.is_file()]


def quantos_arquivos(caminho: str) -> int:
    return len(arquivos_sob_o_alvo(caminho))


def extensoes_do_servidor(servidor: str):
    pasta_do_servidor = Path(servidor).expanduser().resolve().parent
    fonte = pasta_do_servidor.joinpath(*ARQUIVO_DAS_EXTENSOES_DO_SERVIDOR)
    try:
        texto = fonte.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    lista = LISTA_DAS_EXTENSOES_NO_SERVIDOR.search(texto)
    if not lista:
        return None
    vivas = [linha for linha in lista.group(1).splitlines()
             if not linha.strip().startswith(COMENTARIO_NO_SERVIDOR)]
    return set(EXTENSAO_NA_LISTA.findall("\n".join(vivas)))


def sob_pasta_oculta(relativo: Path) -> bool:
    return any(parte.startswith(PONTO) for parte in relativo.parts[:-1])


def contagem_do_servidor(caminho: str, extensoes) -> dict:
    raiz = Path(caminho).expanduser()
    conta = {"elegiveis": None if extensoes is None else 0, "ocultos": 0,
             "json": 0}
    for arquivo in arquivos_sob_o_alvo(caminho):
        if arquivo.suffix == EXTENSAO_DE_JSON:
            conta["json"] += 1
        if extensoes is None or arquivo.suffix not in extensoes:
            continue
        if sob_pasta_oculta(arquivo.relative_to(raiz)):
            conta["ocultos"] += 1
        else:
            conta["elegiveis"] += 1
    return conta


def excecoes_que_o_servidor_nao_reabre(caminho: str) -> list:
    achadas = []
    for arquivo in sorted(Path(caminho).expanduser().glob(".*ignore")):
        if not arquivo.is_file():
            continue
        for linha in arquivo.read_text(encoding="utf-8",
                                       errors="replace").splitlines():
            linha = linha.strip()
            if linha.startswith(MARCA_DE_EXCECAO) and linha.endswith(BARRA):
                achadas.append((arquivo.name, linha))
    return achadas


def quantos_rastreados(caminho: str) -> int:
    try:
        feito = subprocess.run(["git", "ls-files", "--", str(caminho)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return -1
    if feito.returncode != 0:
        return -1
    return len([l for l in feito.stdout.split("\n") if l.strip()])


def excesso_de_nao_rastreados(total: int, rastreados: int) -> int:
    if rastreados < 0 or rastreados == 0:
        return 0
    return total - rastreados if total > rastreados * FOLGA_QUE_NAO_ASSUSTA \
        else 0


class Servidor:
    def __init__(self, caminho: str, ambiente: dict):
        self.processo = subprocess.Popen(
            ["node", str(Path(caminho).expanduser())],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
            encoding="utf-8", errors="replace",
            env=dict(os.environ, **(ambiente or {})))
        self.proxima_id = 1

    def manda(self, mensagem: dict) -> None:
        self.processo.stdin.write(json.dumps(mensagem) + "\n")
        self.processo.stdin.flush()

    def espera(self, identidade: int, teto: int):
        comeco = time.monotonic()
        while time.monotonic() - comeco < teto:
            linha = self.processo.stdout.readline()
            if not linha:
                return None
            try:
                resposta = json.loads(linha)
            except ValueError:
                continue
            if resposta.get("id") == identidade:
                return resposta
        return None

    def pergunta(self, metodo: str, parametros: dict, teto: int):
        identidade = self.proxima_id
        self.proxima_id += 1
        self.manda({"jsonrpc": "2.0", "id": identidade, "method": metodo,
                    "params": parametros})
        return self.espera(identidade, teto)

    def apresenta(self) -> bool:
        pronto = self.pergunta("initialize", {
            "protocolVersion": PROTOCOLO, "capabilities": {},
            "clientInfo": QUEM_CHAMA}, TEMPO_DE_HANDSHAKE)
        if pronto is None:
            return False
        self.manda({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return True

    def indexa(self, caminho: str, teto: int, refazer: bool = False,
               ignorar=None):
        argumentos = {CAMPO_DO_CAMINHO:
                      str(Path(caminho).expanduser().resolve())}
        if refazer:
            argumentos["force"] = True
        if ignorar:
            argumentos[CAMPO_DOS_PADROES_IGNORADOS] = list(ignorar)
        return self.pergunta("tools/call", {
            "name": FERRAMENTA_DE_INDEXAR, "arguments": argumentos}, teto)

    def estado(self, caminho: str, teto: int):
        return self.pergunta("tools/call", {
            "name": FERRAMENTA_DO_ESTADO,
            "arguments": {CAMPO_DO_CAMINHO: str(Path(caminho).expanduser())}},
            teto)

    def espera_terminar(self, caminho: str, teto: int, intervalo: int,
                        relator=None):
        comeco = time.monotonic()
        ultimo = ""
        while time.monotonic() - comeco < teto:
            ultimo = texto_da_resposta(self.estado(caminho, TEMPO_DE_HANDSHAKE))
            if terminou(ultimo):
                return True, ultimo
            if not ainda_anda(ultimo):
                return False, ultimo
            if relator:
                relator(ultimo)
            time.sleep(intervalo)
        return False, ultimo

    def encerra(self) -> None:
        self.processo.kill()


def texto_da_resposta(resposta) -> str:
    if not isinstance(resposta, dict):
        return ""
    partes = (resposta.get("result") or {}).get("content") or []
    return " ".join(p.get("text", "") for p in partes if isinstance(p, dict))


def quantos_o_servidor_indexou(texto: str):
    achado = QUANTOS_O_SERVIDOR_DIZ.search(texto or "")
    return int(achado.group(1)) if achado else None


def terminou(texto: str) -> bool:
    return MARCA_DE_COMPLETO in texto


def ainda_anda(texto: str) -> bool:
    return MARCA_DE_ANDANDO in texto


def veredito(resposta) -> str:
    if resposta is None or "error" in resposta:
        return FALHOU
    if not (resposta.get("result") or {}).get(CAMPO_DE_ERRO_DA_FERRAMENTA):
        return FEITO
    return (JA_ESTAVA if MARCA_DE_JA_INDEXADO in texto_da_resposta(resposta)
            else FALHOU)


def avisos_do_alvo(caminho: str, extensoes, conta: dict) -> list:
    avisos = []
    if conta["elegiveis"] == 0:
        avisos.append(AVISO_SEM_ELEGIVEL)
    if conta["json"] and extensoes is not None \
            and EXTENSAO_DE_JSON not in extensoes:
        avisos.append(AVISO_DO_JSON.format(conta["json"]))
    if conta["ocultos"]:
        avisos.append(AVISO_DE_PASTA_OCULTA.format(conta["ocultos"]))
    for arquivo, linha in excecoes_que_o_servidor_nao_reabre(caminho):
        avisos.append(AVISO_DA_EXCECAO_COM_BARRA.format(arquivo, linha))
    return avisos


def ensaiar(alvos: list, extensoes) -> int:
    print(CABECA_DO_ENSAIO.format(len(alvos)))
    for caminho in alvos:
        total = quantos_arquivos(caminho)
        rastreados = quantos_rastreados(caminho)
        conta = contagem_do_servidor(caminho, extensoes)
        print(LINHA_DO_ENSAIO.format(
            caminho, total,
            rastreados if rastreados >= 0 else NAO_MEDIDO,
            NAO_MEDIDO if conta["elegiveis"] is None else conta["elegiveis"]))
        if (sobra := excesso_de_nao_rastreados(total, rastreados)):
            print(AVISO_DO_EXCESSO.format(sobra, ARQUIVO_DOS_ALVOS))
        for aviso in avisos_do_alvo(caminho, extensoes, conta):
            print(aviso)
    return 0


def indexar(dado: dict, teto: int, refazer: bool = False,
            extensoes=None, cwd: str = "") -> int:
    alvos = dado[CAMPO_DOS_ALVOS]
    servidor = Servidor(dado[CAMPO_DO_SERVIDOR], dado.get(CAMPO_DO_AMBIENTE))
    print(CABECA_DA_RODADA.format(len(alvos), dado[CAMPO_DO_SERVIDOR]))
    if not servidor.apresenta():
        servidor.encerra()
        print(NAO_RESPONDEU.format(TEMPO_DE_HANDSHAKE), file=sys.stderr)
        return 1
    feitos = pulados = sem_elegivel = 0
    comeco_da_rodada = time.monotonic()
    for i, caminho in enumerate(alvos, 1):
        print(LINHA_DO_COMECO.format(i, len(alvos), caminho), flush=True)
        conta = contagem_do_servidor(caminho, extensoes)
        if conta["elegiveis"] == 0:
            sem_elegivel += 1
            print(LINHA_DO_FIM.format(i, len(alvos), caminho,
                                      PULADO_SEM_ELEGIVEL, duracao(0)),
                  flush=True)
            continue
        comeco = time.monotonic()
        resposta = servidor.indexa(caminho, teto, refazer,
                                   dado.get(CAMPO_DO_QUE_IGNORAR))
        gasto = duracao(time.monotonic() - comeco)
        dito = veredito(resposta)
        if dito == FEITO:
            sobrou = max(1, int(teto - (time.monotonic() - comeco)))
            fechou, ultimo = servidor.espera_terminar(
                caminho, sobrou, INTERVALO_DA_ESPERA)
            gasto = duracao(time.monotonic() - comeco)
            if not fechou:
                dito = FALHOU
                resposta = {"result": {"content": [{"type": "text", "text": (
                    NAO_TERMINOU.format(gasto) + " — " + ultimo)}]}}
        feitos += 1 if dito == FEITO else 0
        pulados += 1 if dito == JA_ESTAVA else 0
        print(LINHA_DO_FIM.format(i, len(alvos), caminho, dito, gasto),
              flush=True)
        if dito == FALHOU:
            print(LINHA_DO_ESTADO.format(
                texto_da_resposta(resposta)[:200] or NAO_RESPONDEU.format(teto)),
                flush=True)
        else:
            dito_pelo_servidor = texto_da_resposta(
                servidor.estado(caminho, teto))
            print(LINHA_DO_ESTADO.format(
                dito_pelo_servidor.replace(chr(10), " · ")[:200]), flush=True)
            indexados = quantos_o_servidor_indexou(dito_pelo_servidor)
            elegiveis = (quantos_arquivos(caminho)
                         if conta["elegiveis"] is None else conta["elegiveis"])
            print(LINHA_DA_CONTAGEM.format(elegiveis, indexados)
                  if indexados is not None else SEM_CONTAGEM_DO_SERVIDOR,
                  flush=True)
    servidor.encerra()
    falharam = len(alvos) - feitos - pulados - sem_elegivel
    gasto = duracao(time.monotonic() - comeco_da_rodada)
    print(RESUMO_COM_PULADOS.format(feitos, pulados, sem_elegivel, falharam,
                                    gasto))
    gravar_ultima_ronda(cwd, {
        "quando": time.strftime("%Y-%m-%dT%H:%M:%S"), "feitos": feitos,
        "pulados": pulados, "sem_elegivel": sem_elegivel,
        "falharam": falharam, "duracao": gasto})
    return 0 if not falharam else 1


def testar() -> int:
    import tempfile

    passou = falhou = 0

    def caso(nome: str, condicao: bool) -> None:
        nonlocal passou, falhou
        if condicao:
            passou += 1
        else:
            falhou += 1
            print(f"FALHOU: {nome}")

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        servidor = raiz / "servidor.js"
        servidor.write_text("", encoding="utf-8")
        acervo = raiz / "acervo"
        acervo.mkdir()
        (acervo / "um.md").write_text("x", encoding="utf-8")
        (acervo / "dois.md").write_text("y", encoding="utf-8")

        caso("sem alvos declarados o instrumento recusa e diz o arquivo",
             ARQUIVO_DOS_ALVOS in recusa_da_configuracao({}))
        caso("sem servidor declarado ele recusa e ensina o campo",
             CAMPO_DO_SERVIDOR in recusa_da_configuracao(
                 {CAMPO_DOS_ALVOS: [str(acervo)]}))
        caso("servidor declarado que não existe é recusado ANTES de subir "
             "processo — senão a falha vira 'não respondeu', que manda "
             "procurar no lugar errado",
             "não existe" in recusa_da_configuracao(
                 {CAMPO_DOS_ALVOS: [str(acervo)],
                  CAMPO_DO_SERVIDOR: str(raiz / "nao-existe.js")}))
        caso("alvo que não existe no disco é recusado antes de indexar",
             "não existe no disco" in recusa_da_configuracao(
                 {CAMPO_DOS_ALVOS: [str(raiz / "fantasma")],
                  CAMPO_DO_SERVIDOR: str(servidor)}))
        caso("configuração inteira passa sem recusa",
             recusa_da_configuracao({CAMPO_DOS_ALVOS: [str(acervo)],
                                     CAMPO_DO_SERVIDOR: str(servidor)}) == "")
        caso("o ensaio conta os arquivos sob cada alvo, para o dono saber o "
             "tamanho antes de disparar de madrugada",
             quantos_arquivos(str(acervo)) == 2)
        caso("configuração ilegível não estoura — devolve vazio e a recusa "
             "explica",
             configuracao(str(raiz)) == {})
        def resposta_de(texto, erro=False):
            return {"result": {"content": [{"type": "text", "text": texto}],
                               **({"isError": True} if erro else {})}}

        caso("resposta limpa e indexação feita",
             veredito(resposta_de("Indexed 14 files")) == FEITO)
        caso("resposta com isError dizendo 'already indexed' NAO e falha — "
             "e alvo que ja estava, e chamar isso de falha faria a rodada "
             "noturna parecer quebrada toda madrugada",
             veredito(resposta_de("Codebase is already indexed. Use force",
                                  erro=True)) == JA_ESTAVA)
        caso("resposta com isError de qualquer outra causa E falha — o campo "
             "isError vive DENTRO do result, entao olhar so o erro de topo "
             "transforma recusa em sucesso",
             veredito(resposta_de("Milvus connection refused",
                                  erro=True)) == FALHOU)
        caso("servidor que nao respondeu e falha, nao sucesso",
             veredito(None) == FALHOU)
        caso("erro de protocolo tambem e falha",
             veredito({"error": {"code": -1}}) == FALHOU)
        caso("o texto da resposta e extraido para o relato",
             "Indexed" in texto_da_resposta(resposta_de("Indexed 14 files")))
        caso("resposta que nao e objeto nao estoura",
             texto_da_resposta(None) == "")

        caso("estado com 'Status: completed' e alvo terminado",
             terminou("Statistics: 14 files · Status: completed"))
        caso("estado com 'currently being indexed' ainda anda — e o "
             "instrumento NAO pode encerrar aqui, porque matar o processo "
             "aborta a indexacao em segundo plano do servidor",
             ainda_anda("Codebase is currently being indexed. Progress: 3%")
             and not terminou("Progress: 3%"))
        caso("estado que nao diz nem uma coisa nem outra encerra a espera em "
             "vez de girar ate o teto",
             not terminou("erro qualquer") and not ainda_anda("erro qualquer"))

        caso("acervo com muito arquivo nao rastreado e acusado no ensaio — "
             "4972 no disco contra 277 no git e artefato de build, e indexar "
             "isso enche o indice de lixo",
             excesso_de_nao_rastreados(4972, 277) == 4695)
        caso("acervo cujo total bate com o rastreado nao acusa nada",
             excesso_de_nao_rastreados(20, 18) == 0)
        caso("git que nao respondeu nao vira acusacao — nao medido nao e "
             "excesso",
             excesso_de_nao_rastreados(4972, -1) == 0)
        caso("pasta sem nada rastreado tambem nao acusa: pode ser acervo "
             "legitimo fora do git",
             excesso_de_nao_rastreados(4972, 0) == 0)

        caso("a contagem do servidor sai do texto do estado, para ficar ao "
             "lado da contagem do disco — 157 no alvo e 100 indexados e uma "
             "diferenca que passa calada se os numeros nao aparecem juntos",
             quantos_o_servidor_indexou(
                 "Statistics: 100 files, 340 chunks") == 100)
        caso("estado sem estatistica nao vira zero — nao medido nao e zero",
             quantos_o_servidor_indexou("indexando...") is None
             and quantos_o_servidor_indexou("") is None
             and quantos_o_servidor_indexou(None) is None)

        nucleo_do_servidor = raiz / "@zilliz" / "claude-context-core" / "dist"
        nucleo_do_servidor.mkdir(parents=True)
        mcp_do_servidor = raiz / "@zilliz" / "claude-context-mcp" / "dist"
        mcp_do_servidor.mkdir(parents=True)
        (mcp_do_servidor / "index.js").write_text("", encoding="utf-8")
        (nucleo_do_servidor / "context.js").write_text(
            "const DEFAULT_SUPPORTED_EXTENSIONS = [\n"
            "    // Programming languages\n"
            "    '.py', '.md',\n"
            "    // '.txt',  '.json', '.yaml',\n"
            "];\nconst OUTRA = ['.zip'];\n", encoding="utf-8")
        extensoes = extensoes_do_servidor(str(mcp_do_servidor / "index.js"))
        caso("a lista de extensoes sai do CODIGO do servidor instalado, e a "
             "linha comentada nao conta — foi assim que .json ficou de fora "
             "sem ninguem saber",
             extensoes == {".py", ".md"})
        caso("servidor sem o arquivo de extensoes nao vira lista vazia — e "
             "nao medido",
             extensoes_do_servidor(str(servidor)) is None)

        mistura = raiz / "mistura"
        (mistura / ".oculta").mkdir(parents=True)
        (mistura / "a.md").write_text("x", encoding="utf-8")
        (mistura / ".oculta" / "b.md").write_text("x", encoding="utf-8")
        (mistura / "c.json").write_text("{}", encoding="utf-8")
        (mistura / ".gitignore").write_text("*\n!a.md\n!docs/\n!src\n",
                                            encoding="utf-8")
        conta = contagem_do_servidor(str(mistura), extensoes)
        caso("a contagem imita o servidor: extensao aceita fora de pasta "
             "oculta e elegivel; sob pasta com ponto e oculto; .json e "
             "contado a parte",
             conta == {"elegiveis": 1, "ocultos": 1, "json": 1})
        caso("sem a lista do servidor, elegiveis e nao medido — nunca zero",
             contagem_do_servidor(str(mistura), None)["elegiveis"] is None)
        caso("alvo sem arquivo elegivel e acusado — o servidor acha 0, diz "
             "100% e nunca diz completed, e a pessoa espera o teto inteiro",
             AVISO_SEM_ELEGIVEL in avisos_do_alvo(
                 str(mistura), extensoes,
                 {"elegiveis": 0, "ocultos": 0, "json": 0}))
        avisos = avisos_do_alvo(str(mistura), extensoes, conta)
        caso("o .json e acusado pela EXTENSAO, nao pelo tamanho: o servidor "
             "instalado nao a aceita",
             any("extensão .json NÃO" in a for a in avisos))
        caso("arquivo elegivel sob pasta oculta e acusado, com a saida — "
             "declarar a pasta como alvo proprio",
             any("pasta oculta" in a for a in avisos))
        caso("excecao de gitignore com barra no fim e acusada, e a sem barra "
             "nao: o servidor testa o nome sem a barra e a exclusao vence",
             excecoes_que_o_servidor_nao_reabre(str(mistura))
             == [(".gitignore", "!docs/")])
        caso("alvo com .json onde o servidor aceita .json nao e acusado por "
             "isso",
             not any(".json" in a for a in avisos_do_alvo(
                 str(mistura), {".json", ".md"}, conta)))

        caso("duração sai em minutos quando passa de um minuto",
             duracao(90) == "1.5 min" and duracao(30) == "30s")

        (raiz / ".agents" / "indice").mkdir(parents=True)
        cwd = str(raiz)
        caso("sem a chave, o índice está desligado — a ronda nasce muda, e "
             "quem quer o ritual indexando liga de propósito",
             not esta_ligado({}) and not esta_ligado(configuracao(cwd)))
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            ligar({CAMPO_DOS_ALVOS: [str(acervo)]}, cwd, True)
        caso("--ligar grava a chave no arquivo dos alvos e diz que ligou",
             esta_ligado(configuracao(cwd)) and "LIGADO" in saida.getvalue())
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            ligar(configuracao(cwd), cwd, False)
        caso("--desligar desliga sem apagar os alvos",
             not esta_ligado(configuracao(cwd))
             and configuracao(cwd)[CAMPO_DOS_ALVOS] == [str(acervo)])
        caso("sem ronda registrada, o estado diz isso em vez de inventar "
             "zero",
             ultima_ronda(cwd) is None)
        gravar_ultima_ronda(cwd, {"quando": "2026-09-03T06:00:00",
                                  "feitos": 1, "pulados": 9,
                                  "sem_elegivel": 0, "falharam": 0,
                                  "duracao": "12s"})
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            estado(configuracao(cwd), cwd)
        caso("o estado mostra a última ronda gravada, com os quatro números",
             "1 indexado(s), 9 já estava(m)" in saida.getvalue())

    print(f"{'OK' if not falhou else 'FALHOU'}: {passou + falhou} casos")
    return 1 if falhou else 0


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=USO)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--ensaio", action="store_true",
                        help="mostra os alvos e o tamanho, sem indexar")
    parser.add_argument("--tempo-limite", type=int, default=TEMPO_POR_ALVO,
                        help="teto em segundos de cada alvo")
    parser.add_argument("--refazer", action="store_true",
                        help="reindexa o que já está indexado")
    parser.add_argument("--ligar", action="store_true",
                        help="liga a ronda: o ritual passa a indexar o que "
                             "mudou")
    parser.add_argument("--desligar", action="store_true",
                        help="desliga a ronda sem apagar nada")
    parser.add_argument("--estado", action="store_true",
                        help="diz se está ligado e como foi a última ronda")
    parser.add_argument("--ronda", action="store_true",
                        help="indexa só o que mudou, se ligado; feito para o "
                             "ritual, com teto curto por alvo")
    parser.add_argument(BANDEIRA_DE_TESTE, action="store_true")
    return parser


def main() -> int:
    if BANDEIRA_DE_TESTE in sys.argv[1:]:
        return testar()
    a = montar_parser().parse_args()
    dado = configuracao(a.cwd)
    if a.ligar or a.desligar:
        return ligar(dado, a.cwd, a.ligar)
    if a.estado:
        return estado(dado, a.cwd)
    if a.ronda and not esta_ligado(dado):
        print(RONDA_DESLIGADA.format(ARQUIVO_DOS_ALVOS))
        return 0
    if (recusa := recusa_da_configuracao(dado, a.cwd)):
        print(recusa, file=sys.stderr)
        return 2
    extensoes = extensoes_do_servidor(dado[CAMPO_DO_SERVIDOR])
    if a.ensaio:
        return ensaiar(dado[CAMPO_DOS_ALVOS], extensoes)
    teto = TEMPO_DA_RONDA if a.ronda and a.tempo_limite == TEMPO_POR_ALVO \
        else a.tempo_limite
    return indexar(dado, teto, a.refazer, extensoes, a.cwd)


if __name__ == "__main__":
    sys.exit(main())
