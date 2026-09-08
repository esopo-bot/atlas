import argparse
import contextlib
import fnmatch
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
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
PORTAS_QUE_O_INDICE_PRECISA = (("MILVUS_ADDRESS", "o banco de vetores"),
                               ("OLLAMA_HOST", "quem gera os vetores"))
TEMPO_DA_SONDA_EM_SEGUNDOS = 1.5
PORTA_RESPONDE = "  {} responde em {}"
PORTA_MUDA = ("  {} NÃO responde em {} — declarado não é respondendo, e a "
              "ronda vai falhar quando chegar nele")
PORTA_SEM_ENDERECO = "  {} sem endereço declarado em {}: nada a sondar"
NEM_UMA_PORTA_RESPONDE = ("Nenhuma porta do índice responde: o motor de "
                          "contêineres parece parado. Para levantar: "
                          "docker compose -f .agents/indice/docker-compose.yml "
                          "up -d")
ESTADO_DA_ULTIMA_RONDA = ("última ronda em {quando}: {feitos} indexado(s), "
                          "{pulados} já estava(m), {sem_elegivel} sem arquivo "
                          "elegível, {falharam} falhou(ram), em {duracao}")
SEM_RONDA_AINDA = "nenhuma ronda registrada ainda"

PROTOCOLO = "2024-11-05"
QUEM_CHAMA = {"name": "indexar", "version": "1"}
FERRAMENTA_DE_INDEXAR = "index_codebase"
FERRAMENTA_DO_ESTADO = "get_indexing_status"
FERRAMENTA_DE_DESFAZER = "clear_index"
CAMPO_DO_CAMINHO = "path"

TEMPO_DE_HANDSHAKE = 60
TEMPO_POR_ALVO = 8 * 3600
TEMPO_DA_SINCRONIZACAO = 8 * 3600
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
LINHA_DO_QUE_O_IGNORAR_TIROU = ("      {} arquivo(s) fora da conta porque o "
                                "`ignorar` de {} os exclui — eles nunca "
                                "chegariam ao servidor, e contá-los inflava "
                                "a régua")
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
NAO_TERMINOU = "o servidor deu a indexação por falha: {}"
NAO_COUBE_NO_TETO = ("não terminou em {} — a coleção pela metade foi desfeita, "
                     "e o alvo entra inteiro na próxima ronda; se ele é "
                     "grande, rode com `--tempo-limite` maior")
ANDANDO = "andando"
MARCA_DE_CONCLUSAO_NO_REGISTRO = "Indexing completed successfully"
MARCA_DE_FALHA_NO_REGISTRO = "Indexing failed for"
MARCAS_DE_SINCRONIZACAO_FEITA = ("Index sync completed for all codebases",
                                 "No codebases indexed. Skipping sync")
MARCA_DE_SINCRONIZACAO_PULADA = "Another MCP process is already syncing"
SINCRONIZACAO_FEITA = "feita"
SINCRONIZACAO_PULADA = "pulada"
TRAVA_DA_SINCRONIZACAO = Path.home() / ".context" / "mcp-sync.lock"
ARQUIVO_DO_DONO_DA_TRAVA = "owner.json"
TRAVA_ORFA_REMOVIDA = ("  trava de sincronização do processo {} removida: o "
                       "processo já morreu, e o servidor só a reclamaria "
                       "depois de 10 min")
SINCRONIZACAO_PULADA_POR_TRAVA = ("  a sincronização foi pulada: outro servidor "
                                  "do índice segura a trava em {} — o que "
                                  "mudou desde a última ronda entra na "
                                  "próxima")
VARIAVEL_DO_INTERVALO_DE_SYNC = "CLAUDE_CONTEXT_SYNC_INTERVAL_MS"
INTERVALO_DE_SYNC_QUE_NAO_ATRAPALHA = str(24 * 3600 * 1000)
VARIAVEL_DA_SINCRONIZACAO = "CLAUDE_CONTEXT_BACKGROUND_SYNC"
SINCRONIZACAO_DESLIGADA = "false"
SEM_SINCRONIZACAO = ("  sincronização desligada: com `--refazer` cada alvo é "
                     "reconstruído do zero, e sincronizar os outros só "
                     "disputaria quem gera os vetores")
ESPERANDO_SINCRONIZACAO = ("  o servidor sincroniza o que mudou nos alvos já "
                           "indexados antes do primeiro disparo")
SINCRONIZACAO_FECHOU = "  sincronização feita em {}"
SINCRONIZACAO_NAO_FECHOU = ("  a sincronização não fechou em {} — a ronda "
                            "segue, mas o que ela indexar agora pode "
                            "disputar o Ollama com ela")
INTERRUPCAO = ("interrompido com {} alvo(s) em curso: desfazendo cada um, "
               "para o servidor não os chamar de completos na subida "
               "seguinte")
DESFEITO = "  {} — desfeito; entra inteiro na próxima ronda"
NAO_DESFEZ = ("  {} — não deu para desfazer: ficou pela metade, reindexe "
              "com `--refazer`")
CODIGO_DA_INTERRUPCAO = 130
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


def maquina_e_porta(endereco: str):
    limpo = re.sub(r"^[a-zA-Z]+://", "", (endereco or "").strip())
    limpo = limpo.split("/")[0]
    if ":" not in limpo:
        return None
    maquina, _, porta = limpo.rpartition(":")
    try:
        return maquina or "127.0.0.1", int(porta)
    except ValueError:
        return None


def a_porta_responde(endereco: str) -> bool:
    alvo = maquina_e_porta(endereco)
    if alvo is None:
        return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sonda:
        sonda.settimeout(TEMPO_DA_SONDA_EM_SEGUNDOS)
        return sonda.connect_ex(alvo) == 0


def sondagem_das_portas(dado: dict) -> list:
    ambiente = dado.get(CAMPO_DO_AMBIENTE) or {}
    achados = []
    for chave, quem in PORTAS_QUE_O_INDICE_PRECISA:
        endereco = ambiente.get(chave)
        if not endereco:
            achados.append((quem, None, PORTA_SEM_ENDERECO.format(
                quem, ARQUIVO_DOS_ALVOS)))
            continue
        responde = a_porta_responde(endereco)
        molde = PORTA_RESPONDE if responde else PORTA_MUDA
        achados.append((quem, responde, molde.format(quem, endereco)))
    return achados


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
    if not esta_ligado(dado):
        return 0
    sondagem = sondagem_das_portas(dado)
    for _, _, linha in sondagem:
        print(linha)
    respostas = [responde for _, responde, _ in sondagem]
    if respostas and not any(respostas):
        print(NEM_UMA_PORTA_RESPONDE)
    return 0 if all(respostas) else 1


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


def o_ignorar_exclui(relativo: Path, ignorar) -> bool:
    if not ignorar:
        return False
    texto = relativo.as_posix()
    return any(fnmatch.fnmatch(texto, padrao)
               or fnmatch.fnmatch("/" + texto, padrao)
               for padrao in ignorar)


def contagem_do_servidor(caminho: str, extensoes, ignorar=None) -> dict:
    raiz = Path(caminho).expanduser()
    conta = {"elegiveis": None if extensoes is None else 0, "ocultos": 0,
             "json": 0, "ignorados": 0}
    for arquivo in arquivos_sob_o_alvo(caminho):
        if arquivo.suffix == EXTENSAO_DE_JSON:
            conta["json"] += 1
        if extensoes is None or arquivo.suffix not in extensoes:
            continue
        relativo = arquivo.relative_to(raiz)
        if o_ignorar_exclui(relativo, ignorar):
            conta["ignorados"] += 1
        elif sob_pasta_oculta(relativo):
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


def ambiente_que_nao_atrapalha(ambiente: dict, refazer: bool = False) -> dict:
    """A sincronização periódica do servidor reindexa por mudança em cima do
    alvo que está sendo indexado; a ronda a empurra para um dia e deixa só a
    inicial, que ela espera terminar antes do primeiro disparo. Com
    `--refazer` não há o que sincronizar: cada alvo é reconstruído."""
    completo = dict(ambiente or {})
    if refazer:
        completo.setdefault(VARIAVEL_DA_SINCRONIZACAO, SINCRONIZACAO_DESLIGADA)
    completo.setdefault(VARIAVEL_DO_INTERVALO_DE_SYNC,
                        INTERVALO_DE_SYNC_QUE_NAO_ATRAPALHA)
    return completo


def veredito_do_registro(linhas: list):
    """Lê o que o servidor escreveu no stderr desde o disparo: concluiu,
    falhou, ou ainda nada."""
    for linha in linhas:
        if MARCA_DE_CONCLUSAO_NO_REGISTRO in linha:
            return FEITO, linha.strip()
        if MARCA_DE_FALHA_NO_REGISTRO in linha:
            return FALHOU, linha.strip()
    return None, ""


def sincronizacao_terminou(linhas: list):
    """Lê o registro: a sincronização inicial fechou, foi pulada porque outro
    servidor segura a trava, ou ainda nada."""
    for linha in linhas:
        if any(marca in linha for marca in MARCAS_DE_SINCRONIZACAO_FEITA):
            return SINCRONIZACAO_FEITA
        if MARCA_DE_SINCRONIZACAO_PULADA in linha:
            return SINCRONIZACAO_PULADA
    return None


def processo_vivo(pid: int) -> bool:
    if os.name == "nt":
        saida = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                               capture_output=True, text=True)
        return str(pid) in saida.stdout
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def dono_da_trava(trava: Path):
    try:
        return int(json.loads((trava / ARQUIVO_DO_DONO_DA_TRAVA)
                              .read_text(encoding="utf-8")).get("pid"))
    except (OSError, ValueError, TypeError):
        return None


def limpar_trava_orfa(trava: Path = TRAVA_DA_SINCRONIZACAO,
                      vivo=processo_vivo) -> str:
    """Servidor morto de fora deixa a trava global de sincronização, e o
    próximo só a reclama depois de 10 min — a ronda inicial pula a
    sincronização e espera por uma marca que nunca vem."""
    if not trava.is_dir():
        return ""
    pid = dono_da_trava(trava)
    if pid is not None and vivo(pid):
        return ""
    shutil.rmtree(trava, ignore_errors=True)
    return TRAVA_ORFA_REMOVIDA.format(pid if pid is not None else "?")


class Servidor:
    def __init__(self, caminho: str, ambiente: dict, refazer: bool = False):
        self.processo = subprocess.Popen(
            ["node", str(Path(caminho).expanduser())],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1,
            encoding="utf-8", errors="replace",
            env=dict(os.environ,
                     **ambiente_que_nao_atrapalha(ambiente, refazer)))
        self.proxima_id = 1
        self.registro = []
        self.partida = 0
        threading.Thread(target=self.le_o_registro, daemon=True).start()

    def le_o_registro(self) -> None:
        for linha in self.processo.stderr:
            self.registro.append(linha)

    def desde_a_partida(self) -> list:
        return self.registro[self.partida:]

    def espera_sincronizacao(self, teto: int, intervalo: int):
        comeco = time.monotonic()
        while time.monotonic() - comeco < teto:
            dito = sincronizacao_terminou(self.registro)
            if dito:
                return dito
            time.sleep(intervalo)
        return None

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
        self.partida = len(self.registro)
        return self.pergunta("tools/call", {
            "name": FERRAMENTA_DE_INDEXAR, "arguments": argumentos}, teto)

    def estado(self, caminho: str, teto: int):
        return self.pergunta("tools/call", {
            "name": FERRAMENTA_DO_ESTADO,
            "arguments": {CAMPO_DO_CAMINHO: str(Path(caminho).expanduser())}},
            teto)

    def espera_terminar(self, caminho: str, teto: int, intervalo: int):
        """Espera pelo registro, nunca pela consulta de estado: cada
        `get_indexing_status` roda a recuperação do servidor, que grava como
        completo qualquer alvo em curso que já tenha linhas no banco."""
        comeco = time.monotonic()
        while time.monotonic() - comeco < teto:
            dito, linha = veredito_do_registro(self.desde_a_partida())
            if dito:
                return dito, linha
            time.sleep(intervalo)
        return ANDANDO, ""

    def desfaz(self, caminho: str, teto: int):
        return self.pergunta("tools/call", {
            "name": FERRAMENTA_DE_DESFAZER,
            "arguments": {CAMPO_DO_CAMINHO: str(Path(caminho).expanduser())}},
            teto)

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


def sincronizar_antes_do_primeiro_disparo(servidor, refazer: bool,
                                          comeco: float) -> str:
    """A sincronização inicial é quem traz o que mudou nos alvos já
    indexados; a ronda a espera para não disputar quem gera os vetores com o
    próprio trabalho. Com `--refazer` ela nem sobe."""
    if refazer:
        print(SEM_SINCRONIZACAO, flush=True)
        return SINCRONIZACAO_DESLIGADA
    print(ESPERANDO_SINCRONIZACAO, flush=True)
    dito = servidor.espera_sincronizacao(TEMPO_DA_SINCRONIZACAO,
                                         INTERVALO_DA_ESPERA)
    gasto = duracao(time.monotonic() - comeco)
    if dito == SINCRONIZACAO_FEITA:
        print(SINCRONIZACAO_FECHOU.format(gasto), flush=True)
    elif dito == SINCRONIZACAO_PULADA:
        print(SINCRONIZACAO_PULADA_POR_TRAVA.format(TRAVA_DA_SINCRONIZACAO),
              flush=True)
    else:
        print(SINCRONIZACAO_NAO_FECHOU.format(gasto), flush=True)
    return dito


def desfazer_a_metade(servidor, caminho: str) -> bool:
    """Alvo que o servidor deu por falho fica com a coleção pela metade, e na
    subida seguinte ele a chama de completa; apagar agora é o que faz a
    próxima ronda refazê-lo inteiro."""
    resposta = servidor.desfaz(caminho, TEMPO_DE_HANDSHAKE)
    desfez = veredito(resposta) == FEITO
    print((DESFEITO if desfez else NAO_DESFEZ).format(caminho), flush=True)
    return desfez


def desfazer_o_que_anda(servidor, em_curso: list) -> list:
    """Apaga a coleção de cada alvo em curso; devolve os que não deu."""
    if not em_curso:
        return []
    print(INTERRUPCAO.format(len(em_curso)), file=sys.stderr, flush=True)
    nao_desfeitos = []
    for caminho in em_curso:
        resposta = servidor.desfaz(caminho, TEMPO_DE_HANDSHAKE)
        if veredito(resposta) == FEITO:
            print(DESFEITO.format(caminho), file=sys.stderr, flush=True)
        else:
            nao_desfeitos.append(caminho)
            print(NAO_DESFEZ.format(caminho), file=sys.stderr, flush=True)
    return nao_desfeitos


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


def ensaiar(alvos: list, extensoes, ignorar=None) -> int:
    print(CABECA_DO_ENSAIO.format(len(alvos)))
    for caminho in alvos:
        total = quantos_arquivos(caminho)
        rastreados = quantos_rastreados(caminho)
        conta = contagem_do_servidor(caminho, extensoes, ignorar)
        print(LINHA_DO_ENSAIO.format(
            caminho, total,
            rastreados if rastreados >= 0 else NAO_MEDIDO,
            NAO_MEDIDO if conta["elegiveis"] is None else conta["elegiveis"]))
        if conta["ignorados"]:
            print(LINHA_DO_QUE_O_IGNORAR_TIROU.format(
                conta["ignorados"], ARQUIVO_DOS_ALVOS))
        if (sobra := excesso_de_nao_rastreados(total, rastreados)):
            print(AVISO_DO_EXCESSO.format(sobra, ARQUIVO_DOS_ALVOS))
        for aviso in avisos_do_alvo(caminho, extensoes, conta):
            print(aviso)
    return 0


def disparar_um_alvo(servidor, i: int, total: int, caminho: str, teto: int,
                     refazer: bool, extensoes, ignorar, em_curso: list) -> str:
    """Dispara um alvo e espera ele terminar pelo registro do servidor, um
    por vez: alvo em paralelo é o que a recuperação do servidor grava como
    completo antes da hora. O que não termina no teto é desfeito."""
    print(LINHA_DO_COMECO.format(i, total, caminho), flush=True)
    conta = contagem_do_servidor(caminho, extensoes, ignorar)
    if conta["elegiveis"] == 0:
        print(LINHA_DO_FIM.format(i, total, caminho, PULADO_SEM_ELEGIVEL,
                                  duracao(0)), flush=True)
        return PULADO_SEM_ELEGIVEL
    comeco = time.monotonic()
    resposta = servidor.indexa(caminho, teto, refazer, ignorar)
    dito = veredito(resposta)
    explicacao = texto_da_resposta(resposta)[:200] or NAO_RESPONDEU.format(teto)
    if dito == FEITO:
        em_curso.append(caminho)
        sobrou = max(1, int(teto - (time.monotonic() - comeco)))
        dito, linha = servidor.espera_terminar(
            caminho, sobrou, INTERVALO_DA_ESPERA)
        em_curso.remove(caminho)
        gasto = duracao(time.monotonic() - comeco)
        if dito == ANDANDO:
            dito, explicacao = FALHOU, NAO_COUBE_NO_TETO.format(gasto)
        elif dito == FALHOU:
            explicacao = NAO_TERMINOU.format(linha[:200])
    gasto = duracao(time.monotonic() - comeco)
    print(LINHA_DO_FIM.format(i, total, caminho, dito, gasto), flush=True)
    if dito == FALHOU:
        print(LINHA_DO_ESTADO.format(explicacao), flush=True)
        if explicacao != NAO_RESPONDEU.format(teto):
            desfazer_a_metade(servidor, caminho)
    else:
        dito_pelo_servidor = texto_da_resposta(servidor.estado(caminho, teto))
        print(LINHA_DO_ESTADO.format(
            dito_pelo_servidor.replace(chr(10), " · ")[:200]), flush=True)
        indexados = quantos_o_servidor_indexou(dito_pelo_servidor)
        elegiveis = (quantos_arquivos(caminho)
                     if conta["elegiveis"] is None else conta["elegiveis"])
        print(LINHA_DA_CONTAGEM.format(elegiveis, indexados)
              if indexados is not None else SEM_CONTAGEM_DO_SERVIDOR,
              flush=True)
    return dito


def indexar(dado: dict, teto: int, refazer: bool = False,
            extensoes=None, cwd: str = "", fabrica=None,
            trava: Path = TRAVA_DA_SINCRONIZACAO) -> int:
    alvos = dado[CAMPO_DOS_ALVOS]
    print(CABECA_DA_RODADA.format(len(alvos), dado[CAMPO_DO_SERVIDOR]))
    if (trava_removida := limpar_trava_orfa(trava)):
        print(trava_removida, flush=True)
    servidor = (fabrica or Servidor)(dado[CAMPO_DO_SERVIDOR],
                                     dado.get(CAMPO_DO_AMBIENTE), refazer)
    if not servidor.apresenta():
        servidor.encerra()
        print(NAO_RESPONDEU.format(TEMPO_DE_HANDSHAKE), file=sys.stderr)
        return 1
    feitos = pulados = sem_elegivel = 0
    comeco_da_rodada = time.monotonic()
    em_curso = []
    try:
        sincronizar_antes_do_primeiro_disparo(servidor, refazer,
                                              comeco_da_rodada)
        for i, caminho in enumerate(alvos, 1):
            dito = disparar_um_alvo(servidor, i, len(alvos), caminho, teto,
                                    refazer, extensoes,
                                    dado.get(CAMPO_DO_QUE_IGNORAR), em_curso)
            feitos += 1 if dito == FEITO else 0
            pulados += 1 if dito == JA_ESTAVA else 0
            sem_elegivel += 1 if dito == PULADO_SEM_ELEGIVEL else 0
    except KeyboardInterrupt:
        desfazer_o_que_anda(servidor, list(em_curso))
        servidor.encerra()
        return CODIGO_DA_INTERRUPCAO
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
             conta == {"elegiveis": 1, "ocultos": 1, "json": 1,
                       "ignorados": 0})
        caso("sem a lista do servidor, elegiveis e nao medido — nunca zero",
             contagem_do_servidor(str(mistura), None)["elegiveis"] is None)

        pesada = raiz / "pesada"
        (pesada / "node_modules" / "fundo").mkdir(parents=True)
        (pesada / "meu.md").write_text("x", encoding="utf-8")
        (pesada / "node_modules" / "a.md").write_text("x", encoding="utf-8")
        (pesada / "node_modules" / "fundo" / "b.md").write_text(
            "x", encoding="utf-8")
        sem_ignorar = contagem_do_servidor(str(pesada), extensoes)
        com_ignorar = contagem_do_servidor(str(pesada), extensoes,
                                           ["**/node_modules/**"])
        caso("sem o ignorar, a conta inflava com o que nunca chegaria ao "
             "servidor — era esta a regua que enganava",
             sem_ignorar["elegiveis"] == 3)
        caso("o `ignorar` do alvos.json sai da conta de elegiveis, e o que "
             "ele tirou e dito em vez de sumir calado",
             com_ignorar["elegiveis"] == 1
             and com_ignorar["ignorados"] == 2)
        caso("padrao que nao casa com nada nao tira ninguem",
             contagem_do_servidor(str(pesada), extensoes,
                                  ["**/vendor/**"])["elegiveis"] == 3)
        caso("sem lista de ignorar a conta segue como antes",
             contagem_do_servidor(str(pesada), extensoes,
                                  [])["elegiveis"] == 3)
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

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ouvinte:
            ouvinte.bind(("127.0.0.1", 0))
            ouvinte.listen(16)
            porta_aberta = ouvinte.getsockname()[1]
            caso("porta que atende é reconhecida como respondendo",
                 a_porta_responde(f"127.0.0.1:{porta_aberta}"))
            caso("o endereço com esquema http também é sondado",
                 a_porta_responde(f"http://127.0.0.1:{porta_aberta}"))
        caso("porta fechada NÃO responde — é este o caso que o --estado "
             "calava, dizendo LIGADO com o motor de contêineres parado",
             not a_porta_responde(f"127.0.0.1:{porta_aberta}"))
        caso("endereço sem porta não vira falso positivo",
             maquina_e_porta("127.0.0.1") is None)
        porta_morta = {CAMPO_DO_LIGADO: True, CAMPO_DOS_ALVOS: ["x"],
                       CAMPO_DO_AMBIENTE: {
                           "MILVUS_ADDRESS": f"127.0.0.1:{porta_aberta}",
                           "OLLAMA_HOST":
                               f"http://127.0.0.1:{porta_aberta}"}}
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            codigo_do_estado = estado(porta_morta, cwd)
        caso("com as portas mudas o estado REPROVA, em vez de sair 0 dizendo "
             "LIGADO",
             codigo_do_estado == 1 and "NÃO responde" in dito.getvalue())
        caso("e ele diz como levantar, em vez de deixar a sessão adivinhar",
             "docker compose" in dito.getvalue())

        concluiu = ("[LOG] [BACKGROUND-INDEX] ✅ Indexing completed "
                    "successfully! Files: 20, Chunks: 310\n")
        falhou_no_lote = ("[ERROR] [BACKGROUND-INDEX] Indexing failed for "
                          "D:\\acervo: Embedding API error (batch size: "
                          "100): fetch failed\n")
        progresso = "[LOG] [BACKGROUND-INDEX] Progress: files (3/20) - 40%\n"
        caso("o registro do servidor diz que concluiu — e e SO por ele que a "
             "ronda sabe: a consulta de estado roda a recuperacao, que grava "
             "como completo o alvo em curso que ja tem linhas no banco",
             veredito_do_registro([progresso, concluiu]) == (FEITO,
                                                             concluiu.strip()))
        caso("registro com falha e falha, com a linha do servidor",
             veredito_do_registro([progresso, falhou_no_lote])[0] == FALHOU)
        caso("registro so com progresso ainda nao decide",
             veredito_do_registro([progresso]) == (None, ""))
        caso("a sincronizacao inicial fecha por qualquer das duas marcas",
             sincronizacao_terminou(["[LOG] [SYNC-DEBUG] Index sync completed "
                                     "for all codebases in 812ms\n"])
             == SINCRONIZACAO_FEITA
             and sincronizacao_terminou(["[LOG] [SYNC-DEBUG] No codebases "
                                         "indexed. Skipping sync.\n"])
             == SINCRONIZACAO_FEITA
             and sincronizacao_terminou([progresso]) is None)
        caso("sincronizacao pulada por trava de outro servidor e reconhecida "
             "— medido: a ronda esperou por uma marca que nunca viria",
             sincronizacao_terminou(["[LOG] [SYNC-DEBUG] Another MCP process "
                                     "is already syncing. Skipping this "
                                     "cycle.\n"]) == SINCRONIZACAO_PULADA)

        trava = raiz / "mcp-sync.lock"
        trava.mkdir()
        (trava / ARQUIVO_DO_DONO_DA_TRAVA).write_text(
            json.dumps({"pid": 4242}), encoding="utf-8")
        caso("trava cujo dono ainda vive fica",
             limpar_trava_orfa(trava, vivo=lambda pid: True) == ""
             and trava.is_dir())
        dito = limpar_trava_orfa(trava, vivo=lambda pid: False)
        caso("trava cujo dono morreu e removida antes de subir o servidor, "
             "e o pid e dito — medido: servidor orfao encerrado deixou a "
             "trava, e o proximo pulou a sincronizacao por 10 min",
             "4242" in dito and not trava.exists())
        caso("sem trava nao ha o que limpar",
             limpar_trava_orfa(trava, vivo=lambda pid: False) == "")
        caso("a ronda empurra a sincronizacao periodica para um dia, sem "
             "sobrescrever o que o dono declarou",
             ambiente_que_nao_atrapalha({})[VARIAVEL_DO_INTERVALO_DE_SYNC]
             == INTERVALO_DE_SYNC_QUE_NAO_ATRAPALHA
             and ambiente_que_nao_atrapalha(
                 {VARIAVEL_DO_INTERVALO_DE_SYNC: "5"})[
                     VARIAVEL_DO_INTERVALO_DE_SYNC] == "5")
        caso("com --refazer a sincronizacao nem sobe: cada alvo e "
             "reconstruido, e sincronizar os outros varreria a arvore "
             "inteira antes do primeiro disparo",
             ambiente_que_nao_atrapalha({}, refazer=True)[
                 VARIAVEL_DA_SINCRONIZACAO] == SINCRONIZACAO_DESLIGADA
             and VARIAVEL_DA_SINCRONIZACAO
             not in ambiente_que_nao_atrapalha({}))

        class ServidorFingido:
            def __init__(self, espera=(FEITO, ""), desfaz_ok=True):
                self.resposta_da_espera = espera
                self.chamadas = []
                self.desfaz_ok = desfaz_ok

            def apresenta(self):
                return True

            def espera_sincronizacao(self, teto, intervalo):
                self.chamadas.append(("sincroniza", ""))
                return SINCRONIZACAO_FEITA

            def indexa(self, caminho, teto, refazer=False, ignorar=None):
                self.chamadas.append(("indexa", caminho))
                return resposta_de("Indexing started in background")

            def espera_terminar(self, caminho, teto, intervalo):
                self.chamadas.append(("espera", caminho))
                return self.resposta_da_espera

            def estado(self, caminho, teto):
                self.chamadas.append(("estado", caminho))
                return resposta_de("Statistics: 2 files, 3 chunks · "
                                   "Status: completed")

            def desfaz(self, caminho, teto):
                self.chamadas.append(("desfaz", caminho))
                return resposta_de("Index cleared", erro=not self.desfaz_ok)

            def encerra(self):
                self.chamadas.append(("encerra", ""))

        fingido = ServidorFingido(desfaz_ok=False)
        saida = io.StringIO()
        with contextlib.redirect_stderr(saida):
            sobraram = desfazer_o_que_anda(fingido, ["d", "e"])
        caso("interrupcao com alvo em curso chama clear_index em cada um, e "
             "o que nao deu para desfazer e nomeado com a saida --refazer",
             [c for c in fingido.chamadas if c[0] == "desfaz"]
             == [("desfaz", "d"), ("desfaz", "e")]
             and sobraram == ["d", "e"] and "--refazer" in saida.getvalue())
        caso("sem alvo em curso a interrupcao nao chama nada",
             desfazer_o_que_anda(ServidorFingido(), []) == [])

        alvo_real = str(acervo)
        configuracao_de_prova = {CAMPO_DOS_ALVOS: [alvo_real],
                                 CAMPO_DO_SERVIDOR: str(servidor)}

        def ronda_fingida(fingido):
            saida = io.StringIO()
            with contextlib.redirect_stdout(saida):
                codigo = indexar(configuracao_de_prova, teto=1,
                                 extensoes={".md"}, cwd=cwd,
                                 fabrica=lambda c, a, refaz: fingido,
                                 trava=raiz / "sem-trava")
            return codigo, [nome for nome, _ in fingido.chamadas], \
                saida.getvalue()

        fingido = ServidorFingido(espera=(FEITO, concluiu.strip()))
        codigo, ordem, dito = ronda_fingida(fingido)
        caso("a ronda espera a sincronizacao inicial ANTES do primeiro "
             "disparo, espera o alvo pelo registro, e so entao consulta o "
             "estado e encerra — nessa ordem",
             codigo == 0 and ordem == ["sincroniza", "indexa", "espera",
                                       "estado", "encerra"]
             and "1 indexado(s)" in dito)

        fingido = ServidorFingido(espera=(ANDANDO, ""))
        codigo, ordem, dito = ronda_fingida(fingido)
        caso("alvo que nao termina no teto e desfeito e contado como falha — "
             "medido: seguir para o proximo com este em curso e o que deixou "
             "6 de 13 alvos pela metade, gravados como completos",
             codigo == 1 and ("desfaz", alvo_real) in fingido.chamadas
             and "não terminou" in dito and "1 falhou" in dito
             and ordem[-1] == "encerra")

        fingido = ServidorFingido(espera=(FEITO, concluiu.strip()))
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            indexar(configuracao_de_prova, teto=1, refazer=True,
                    extensoes={".md"}, cwd=cwd,
                    fabrica=lambda caminho, ambiente, refaz: fingido,
                    trava=raiz / "sem-trava")
        caso("com --refazer a ronda nao espera sincronizacao nenhuma, e diz "
             "por que",
             ("sincroniza", "") not in fingido.chamadas
             and "sincronização desligada" in saida.getvalue())

        fingido = ServidorFingido(espera=(FALHOU, falhou_no_lote.strip()))
        codigo, ordem, dito = ronda_fingida(fingido)
        caso("alvo que o servidor deu por falho e desfeito na hora, com o "
             "erro do servidor colado — lote de embeddings que estoura 5 min "
             "e a causa medida",
             codigo == 1 and ("desfaz", alvo_real) in fingido.chamadas
             and "fetch failed" in dito)

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
        return ensaiar(dado[CAMPO_DOS_ALVOS], extensoes,
                       dado.get(CAMPO_DO_QUE_IGNORAR))
    teto = TEMPO_DA_RONDA if a.ronda and a.tempo_limite == TEMPO_POR_ALVO \
        else a.tempo_limite
    return indexar(dado, teto, a.refazer, extensoes, a.cwd)


if __name__ == "__main__":
    sys.exit(main())
