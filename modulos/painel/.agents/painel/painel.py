import argparse
import contextlib
import errno
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DESCRICAO_DA_CLI = ("painel de controle — dispara sessão headless e mostra o "
                    "estado do executor de roteiros, no navegador")
AJUDA_CWD = "worktree ou clone descartável onde a sessão roda"
AJUDA_ROTEIROS = ("pastas de roteiro, por vírgula; a primeira vence "
                  "o nome repetido")
AJUDA_FORCAR_ARVORE_SUJA = "sobe mesmo com mudança não commitada no --cwd"

ERRO_CWD_OBRIGATORIO = (
    "erro de uso: --cwd é obrigatório (worktree ou clone descartável);\n"
    "a sessão da execução pula permissões e não deve tocar a árvore "
    "que importa.")
ERRO_CWD_NAO_E_PASTA = "erro de uso: --cwd não é pasta: {}"
ERRO_SEM_ENCADEADOR = ("erro de ambiente: falta o encadeador — rode\n"
                       "  python montar.py --modulo encadeador")
ERRO_SEM_O_COMANDO_CLAUDE = (
    "erro de ambiente: o comando {} não está no PATH; a etapa de "
    "sessão morreria. Quem manda no comando é ENCADEADOR_SESSAO.")
ERRO_ARVORE_SUJA = (
    "PAREI — {} tem mudança não commitada.\n"
    "A sessão da execução roda com permissões puladas: numa árvore com "
    "trabalho seu dentro, um erro dela custa caro.\n"
    "Use um worktree descartável:\n"
    "  git worktree add /tmp/executor HEAD\n"
    "Se você sabe o que está fazendo: --forcar-arvore-suja")
ERRO_PORTA_NAO_ABRIU = "erro de ambiente: não consegui abrir a porta {}: {}"

RECADO_PORTA_JA_E_DESTE_REPOSITORIO = (
    "o painel de controle deste repositório já está no ar: "
    "http://127.0.0.1:{porta}\n"
    "  (nada a fazer — abra o endereço acima)")
RECADO_PORTA_DE_OUTRO_REPOSITORIO = (
    "PAREI — a porta {porta} é do painel de controle de OUTRO repositório:\n"
    "  {ocupante}\n"
    "Uma porta por repositório é o desenho. Suba este noutra:\n"
    "  --porta {proxima_porta}")
RECADO_PORTA_DE_ESTRANHO = (
    "PAREI — a porta {porta} está ocupada, e não por um painel de controle.\n"
    "Quem está nela:\n"
    "  ss -ltnp | grep :{porta}\n"
    "Encerre aquele, ou suba este noutra porta:\n"
    "  --porta {outra_porta}")

ANUNCIO_NO_AR = "painel de controle em http://127.0.0.1:{} — camada {}"
ANUNCIO_REPOSITORIO = "  repositório (o painel de controle): {}"
ANUNCIO_SESSOES = "  sessões rodam em:                   {}"
ANUNCIO_EVIDENCIAS = "  evidências em:                         {}"
ANUNCIO_ROTEIROS = "  roteiros de:                      {} ({} encontrados)"
ANUNCIO_COMO_ENCERRAR = "Ctrl+C encerra."
ANUNCIO_ENCERRADO = "\nencerrado."

ERRO_ROTA_DESCONHECIDA = "rota desconhecida"
ERRO_CORPO_INVALIDO = "corpo inválido"
ERRO_NOME_DE_TRABALHO = ("nome de trabalho inválido: minúsculo, sem barra nem "
                         "espaço, até 64")
ERRO_ALVO_OCUPADO = (
    "já existe execução rodando neste alvo: {}. "
    "Uma por vez — duas sessões na mesma árvore se atropelam. "
    "Espere terminar, ou suba outro painel de controle "
    "apontando para outro repositório.")
ERRO_SEM_PEDIDO = "escreva um pedido ou escolha um roteiro"
ERRO_ROTEIRO_COLADO_NO_LUGAR_DO_PEDIDO = (
    "isso é um roteiro, não um pedido. Salve-o como .json "
    "na pasta de roteiros e escolha-o na lista — colado "
    "aqui, o JSON inteiro viraria o texto de UMA sessão.")
ERRO_ROTEIRO_DESCONHECIDO = "roteiro desconhecido: {}"
ERRO_ROTEIRO_ILEGIVEL = "roteiro ilegível: {}"
ERRO_ROTEIRO_SEM_ETAPAS = "roteiro sem lista de etapas"
ERRO_ANDAMENTO_SEM_JSON = "o andamento não devolveu JSON"
ERRO_ANDAMENTO_FALHOU = "o andamento falhou: {}"
ERRO_DISPARO_FALHOU = "não consegui disparar: {}"

RECADO_TRAVA_DE_OUTRO_PAINEL = "{} (outro painel de controle, pid {})"
RECADO_SEM_REPOSITORIO_DE_ISSUES = "sem repositório de issues configurado"
RECADO_GH_MUDO = "sem dado (o gh não respondeu)"
RECADO_SEM_REDE_OU_GH = "sem dado (rede ou gh indisponível)"
PROXIMA_ACAO_JA_ESTA_NO_AR = (
    "rodando agora — espere. A etapa só escreve evidência quando termina, "
    "então pasta vazia no começo é o esperado. Não dispare de novo: a "
    "trava recusaria.")

RESULTADO_DO_CASO_FALHO = "FALHOU: {}"
RESUMO_DOS_CASOS = "{}: {} casos"
RESUMO_DAS_FALHAS = " — {} falharam"
VEREDITO_OK = "OK"
VEREDITO_FALHOU = "FALHOU"

CODIGO_NADA_A_FAZER = 0
CODIGO_ERRO_DE_USO = 2

VERSAO_DESCONHECIDA = "desconhecida"
PREFIXO_DA_VERSAO_NO_MONTAR = "VERSAO = "
ABERTURAS_DO_CABECALHO_DO_MONTAR = ("#", '"', "'")

TIMEOUT_DA_PERGUNTA_A_PORTA_S = 3
TIMEOUT_DO_GIT_S = 20
TIMEOUT_DO_GH_S = 30
TIMEOUT_DO_ANDAMENTO_S = 60

TETO_SESSAO_S_ESPELHO_DO_ENCADEADOR = 3600
SITUACOES_GRAVADAS_QUE_VENCEM_A_INFERENCIA = ("dormindo", "aguardando-resposta")
CHAVES_DA_ESPERA_GRAVADA = ("desde", "ate", "porque", "issue", "etapa")
SITUACAO_DESCONHECIDA = "desconhecida"
SITUACAO_ENCERRADO = "encerrado"
SITUACAO_TRABALHANDO = "trabalhando"
PROCESSO_RODANDO = "rodando"
PROCESSO_ENCERRADO = "encerrado"
PROCESSO_DESCONHECIDO = "desconhecido"
ESTADO_EM_CURSO = "em-curso"

ARQUIVO_ESTADO = "estado.json"
ARQUIVO_EXECUTOR = "nucleo/executor.json"
SUFIXO_DO_ROTEIRO = ".roteiro.json"
SUFIXO_DA_DESCRICAO = ".md"
INSTALADOR = "montar.py"
BANDEIRA_DE_VERSAO = "--versao"
MARCA_DA_VERSAO = "camada"
TEMPO_DO_INSTALADOR = 60
CHAVE_DESCRICAO = "descricao"
SEM_DESCRICAO = ("Esta rotina não tem descrição: escreva um .md com o mesmo "
                 "nome ao lado do roteiro, ou um campo \"descricao\" nele.")
SUFIXO_DO_LOG = ".log"
PREFIXO_DA_TRAVA = ".trava-"
DIGITOS_DO_RESUMO_DO_ALVO = 12
INTERVALO_DO_QUADRO_S_POR_CORTESIA_DE_REDE = 120
LIMITE_DE_ISSUES_NO_QUADRO = 30
MARCA_DE_MOLDE_NAO_PREENCHIDO = "${"
CAUDA_DO_LOG_NA_TELA = 4000
CAUDA_DO_ERRO_DO_ANDAMENTO = 400

TETO_PADRAO_DE_CICLOS, TETO_MINIMO, TETO_MAXIMO = 3, 1, 9
TURNOS_PADRAO_ACIMA_DO_TETO_DO_MOTOR, TURNOS_MINIMO, TURNOS_MAXIMO = 24, 4, 120
ETAPA_DO_PEDIDO = "pedido"
ETAPA_DA_VERIFICACAO = "verifica"
PREFIXO_DO_PEDIDO_DO_PAINEL = "painel"
PREFIXO_DA_EXECUCAO_SEM_NOME = "execucao"
NOME_QUE_PODE_VIRAR_PASTA = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

PORTA_PADRAO = 4000
DIR_EVIDENCIAS_PADRAO = "tmp/evidencias"
ROTEIROS_PADRAO = "execucoes,tmp"
ENDERECO_LOCAL = "127.0.0.1"
SILENCIO_DO_SERVIDOR = None


def raiz_da_camada_procurando_o_encadeador() -> Path:
    este_arquivo = Path(__file__).resolve()
    for pasta in este_arquivo.parents:
        if (pasta / ".agents" / "encadeador" / "encadeador.py").exists():
            return pasta
    return este_arquivo.parents[2]


RAIZ = raiz_da_camada_procurando_o_encadeador()
ENCADEADOR = RAIZ / ".agents" / "encadeador" / "encadeador.py"


def repositorio_que_responde_na_porta(porta: int) -> str | None:
    try:
        with urllib.request.urlopen(
                f"http://{ENDERECO_LOCAL}:{porta}/trabalhos",
                timeout=TIMEOUT_DA_PERGUNTA_A_PORTA_S) as resposta:
            return json.loads(resposta.read()).get("repositorio")
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def descendentes_lendo_proc(pai: int) -> list:
    filhos_por_pai = {}
    try:
        for entrada in os.listdir("/proc"):
            if not entrada.isdigit():
                continue
            try:
                with open(f"/proc/{entrada}/stat", encoding="utf-8") as arquivo:
                    campos = arquivo.read().rsplit(")", 1)[1].split()
                filhos_por_pai.setdefault(int(campos[1]), []).append(int(entrada))
            except (OSError, IndexError, ValueError):
                continue
    except OSError:
        return []
    fila, achados = [pai], []
    while fila:
        for pid in filhos_por_pai.get(fila.pop(), []):
            achados.append(pid)
            fila.append(pid)
    return achados


VARIAVEL_DA_SESSAO = "ENCADEADOR_SESSAO"
PADRAO_DA_SESSAO = "claude"


def comando_da_sessao() -> str:
    declarado = os.environ.get(VARIAVEL_DA_SESSAO, PADRAO_DA_SESSAO)
    return (shlex.split(declarado) or [PADRAO_DA_SESSAO])[0]


def sessoes_de_modelo_entre(pids: list) -> int:
    vivas = 0
    for pid in pids:
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as arquivo:
                if comando_da_sessao().encode() in arquivo.read():
                    vivas += 1
        except OSError:
            continue
    return vivas


def vivacidade_do_que_o_motor_gravou(gravado: dict, **acrescimo) -> dict:
    espera = {chave: gravado.get(chave) for chave in CHAVES_DA_ESPERA_GRAVADA}
    return {"situacao": gravado["situacao"], **espera, **acrescimo}


def vivacidade(proc, inicio: float | None, gravado: dict = None) -> dict:
    if proc is None:
        if gravado and gravado.get("situacao"):
            return vivacidade_do_que_o_motor_gravou(gravado, de_fora=True)
        return {"situacao": SITUACAO_DESCONHECIDA}
    if proc.poll() is not None:
        return {"situacao": SITUACAO_ENCERRADO, "codigo": proc.returncode}
    filhos = descendentes_lendo_proc(proc.pid)
    sessoes = sessoes_de_modelo_entre(filhos) if filhos else None
    decorrido = int(time.time() - inicio) if inicio else None
    situacao_gravada = gravado.get("situacao") if gravado else None
    if situacao_gravada in SITUACOES_GRAVADAS_QUE_VENCEM_A_INFERENCIA:
        return vivacidade_do_que_o_motor_gravou(
            gravado, sessoes=sessoes, decorrido_s=decorrido)
    return {"situacao": SITUACAO_TRABALHANDO,
            "sessoes": sessoes,
            "decorrido_s": decorrido,
            "teto_s": TETO_SESSAO_S_ESPELHO_DO_ENCADEADOR,
            "resta_s": (max(0, TETO_SESSAO_S_ESPELHO_DO_ENCADEADOR - decorrido)
                        if decorrido is not None else None)}


def configuracao_do_executor_sem_validar(cwd) -> dict | None:
    try:
        dado = json.loads((Path(cwd) / ARQUIVO_EXECUTOR)
                          .read_text(encoding="utf-8"))
        return dado if isinstance(dado, dict) else None
    except (OSError, ValueError):
        return None


def estado_que_o_motor_gravou(dir_evidencias, trabalho) -> dict | None:
    try:
        dado = json.loads((Path(dir_evidencias) / trabalho / ARQUIVO_ESTADO)
                          .read_text(encoding="utf-8"))
        return dado if isinstance(dado, dict) else None
    except (OSError, ValueError):
        return None


def calar_o_convite_a_disparar_o_que_ja_esta_no_ar(estado: dict) -> dict:
    situacao = (estado.get("vivacidade") or {}).get("situacao")
    esperando_alguem = situacao in SITUACOES_GRAVADAS_QUE_VENCEM_A_INFERENCIA
    if (estado.get("processo") == PROCESSO_RODANDO and not esperando_alguem
            and estado.get("estado") == ESTADO_EM_CURSO):
        estado["proxima_acao"] = PROXIMA_ACAO_JA_ESTA_NO_AR
    return estado


def decidir_porta_ocupada(porta: int, repositorio: str,
                          ocupante: str | None) -> tuple:
    if ocupante == repositorio:
        return CODIGO_NADA_A_FAZER, RECADO_PORTA_JA_E_DESTE_REPOSITORIO.format(
            porta=porta)
    if ocupante:
        return CODIGO_ERRO_DE_USO, RECADO_PORTA_DE_OUTRO_REPOSITORIO.format(
            porta=porta, ocupante=ocupante, proxima_porta=porta + 1)
    return CODIGO_ERRO_DE_USO, RECADO_PORTA_DE_ESTRANHO.format(
        porta=porta, outra_porta=porta + 10)


def versao_da_camada_declarada_no_topo_do_montar() -> str:
    try:
        linhas = (RAIZ / "montar.py").read_text(encoding="utf-8").splitlines()
    except OSError:
        return VERSAO_DESCONHECIDA
    for linha in linhas:
        if linha.startswith(PREFIXO_DA_VERSAO_NO_MONTAR):
            return linha.split("=", 1)[1].strip().strip("\"'")
        if linha.strip() and not linha.startswith(ABERTURAS_DO_CABECALHO_DO_MONTAR):
            break
    return VERSAO_DESCONHECIDA


def carimbo_utc_de_agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def nome_de_trabalho(prefixo: str = PREFIXO_DO_PEDIDO_DO_PAINEL) -> str:
    return f"{prefixo}-{carimbo_utc_de_agora()}"


def recusa_do_nome_de_trabalho(nome: str) -> str | None:
    if not NOME_QUE_PODE_VIRAR_PASTA.match(nome or ""):
        return ERRO_NOME_DE_TRABALHO
    return None


def inteiro_na_faixa_ou_padrao(valor, minimo: int, maximo: int,
                               padrao: int) -> int:
    esta_na_faixa = isinstance(valor, int) and minimo <= valor <= maximo
    return valor if esta_na_faixa else padrao


def descricao_do_roteiro(caminho: Path) -> str:
    irmao = caminho.with_suffix(SUFIXO_DA_DESCRICAO)
    if irmao.is_file():
        texto = irmao.read_text(encoding="utf-8", errors="replace").strip()
        if texto:
            return texto
    with contextlib.suppress(OSError, json.JSONDecodeError):
        dado = json.loads(caminho.read_text(encoding="utf-8"))
        if isinstance(dado, dict) and isinstance(dado.get(CHAVE_DESCRICAO), str):
            return dado[CHAVE_DESCRICAO].strip()
    return SEM_DESCRICAO


def parece_roteiro(dado) -> bool:
    return isinstance(dado, dict) and isinstance(dado.get("etapas"), list)


def roteiro_do_pedido_com_verificacao(
        prompt: str, teto: int = TETO_PADRAO_DE_CICLOS,
        turnos: int = TURNOS_PADRAO_ACIMA_DO_TETO_DO_MOTOR,
        issue: int = None) -> dict:
    roteiro = {
        "teto": teto,
        "etapas": [
            {"nome": ETAPA_DO_PEDIDO, "tipo": "sessao", "prompt": prompt,
             "max-turnos": turnos},
            {"nome": ETAPA_DA_VERIFICACAO, "tipo": "verificacao",
             "depende": [ETAPA_DO_PEDIDO]},
        ],
    }
    if issue:
        roteiro["issue"] = int(issue)
    return roteiro


def tem_mudanca_nao_commitada(cwd: Path) -> bool:
    try:
        r = subprocess.run(["git", "status", "--porcelain"], cwd=cwd,
                           capture_output=True, text=True,
                           timeout=TIMEOUT_DO_GIT_S)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0 and bool(r.stdout.strip())


class PonteParaOEncadeador:

    def __init__(self, cwd: Path, dir_evidencias: Path, dirs_roteiros: list):
        self.cwd = cwd
        self.dir = dir_evidencias
        self.roteiros = dirs_roteiros
        self.rodando: dict[str, subprocess.Popen] = {}
        self.inicio: dict[str, float] = {}
        self.trava = threading.Lock()
        self._quadro, self._quadro_em = None, 0.0

    def _arquivo_de_trava_deste_alvo(self) -> Path:
        resumo_do_caminho_do_alvo = hashlib.sha256(
            str(self.cwd).encode()).hexdigest()[:DIGITOS_DO_RESUMO_DO_ALVO]
        return self.dir / f"{PREFIXO_DA_TRAVA}{resumo_do_caminho_do_alvo}.json"

    def _trabalho_desta_sessao_ainda_no_ar(self) -> str | None:
        with self.trava:
            for nome, proc in self.rodando.items():
                if proc.poll() is None:
                    return nome
        return None

    def _dono_vivo_da_trava_em_arquivo(self) -> str | None:
        try:
            dono = json.loads(self._arquivo_de_trava_deste_alvo()
                              .read_text(encoding="utf-8"))
            os.kill(int(dono["pid"]), 0)
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return None
        return RECADO_TRAVA_DE_OUTRO_PAINEL.format(
            dono.get("trabalho", "?"), dono["pid"])

    def ocupado(self) -> str | None:
        return (self._trabalho_desta_sessao_ainda_no_ar()
                or self._dono_vivo_da_trava_em_arquivo())

    def gravar_trava(self, pid: int, trabalho: str) -> None:
        self._arquivo_de_trava_deste_alvo().write_text(
            json.dumps({"pid": pid, "trabalho": trabalho,
                        "cwd": str(self.cwd)}),
            encoding="utf-8")

    def _roteiros_por_nome_com_a_primeira_pasta_vencendo(self) -> dict:
        achados = {}
        for pasta in self.roteiros:
            if not pasta.is_dir():
                continue
            for candidato in sorted(pasta.glob("*.json")):
                if not candidato.is_file() or candidato.name in achados:
                    continue
                try:
                    dado = json.loads(candidato.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if parece_roteiro(dado):
                    achados[candidato.name] = candidato
        return achados

    def catalogo(self) -> list:
        return sorted(self._roteiros_por_nome_com_a_primeira_pasta_vencendo())

    def catalogo_com_descricao(self) -> list:
        achados = self._roteiros_por_nome_com_a_primeira_pasta_vencendo()
        return [{"nome": nome, "descricao": descricao_do_roteiro(achados[nome])}
                for nome in sorted(achados)]

    def ler_roteiro_do_catalogo(self, nome: str) -> tuple[dict | None, str | None]:
        alvo = self._roteiros_por_nome_com_a_primeira_pasta_vencendo().get(nome)
        if alvo is None:
            return None, ERRO_ROTEIRO_DESCONHECIDO.format(nome)
        try:
            dado = json.loads(alvo.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            return None, ERRO_ROTEIRO_ILEGIVEL.format(e)
        if not parece_roteiro(dado):
            return None, ERRO_ROTEIRO_SEM_ETAPAS
        return dado, None

    def disparar(self, roteiro: dict, trabalho: str) -> dict:
        self.dir.mkdir(parents=True, exist_ok=True)
        alvo = self.dir / f"{trabalho}{SUFIXO_DO_ROTEIRO}"
        alvo.write_text(json.dumps(roteiro, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        log = (self.dir / f"{trabalho}{SUFIXO_DO_LOG}").open("w",
                                                             encoding="utf-8")
        proc = subprocess.Popen(
            [sys.executable, str(ENCADEADOR), "executar",
             "--roteiro", str(alvo), "--trabalho", trabalho,
             "--dir", str(self.dir), "--cwd", str(self.cwd)],
            stdout=log, stderr=subprocess.STDOUT, cwd=str(self.cwd))
        with self.trava:
            self.rodando[trabalho] = proc
            self.inicio[trabalho] = time.time()
        self.gravar_trava(proc.pid, trabalho)
        return {"trabalho": trabalho, "roteiro": alvo.name}

    def andamento(self, trabalho: str, roteiro: Path | None = None) -> dict:
        comando = [sys.executable, str(ENCADEADOR), "andamento",
                   "--trabalho", trabalho, "--dir", str(self.dir)]
        if roteiro and roteiro.exists():
            comando += ["--roteiro", str(roteiro)]
        r = subprocess.run(comando, capture_output=True, text=True,
                           cwd=str(self.cwd), timeout=TIMEOUT_DO_ANDAMENTO_S)
        if r.returncode != 0:
            return {"erro": (r.stderr or r.stdout)
                    .strip()[:CAUDA_DO_ERRO_DO_ANDAMENTO]}
        try:
            estado = json.loads(r.stdout)
        except json.JSONDecodeError:
            return {"erro": ERRO_ANDAMENTO_SEM_JSON}
        with self.trava:
            proc = self.rodando.get(trabalho)
        estado["processo"] = (PROCESSO_RODANDO if proc and proc.poll() is None
                              else PROCESSO_ENCERRADO if proc
                              else PROCESSO_DESCONHECIDO)
        gravado = estado_que_o_motor_gravou(self.dir, trabalho)
        estado["gravado"] = gravado
        estado["vivacidade"] = vivacidade(proc, self.inicio.get(trabalho),
                                          gravado)
        calar_o_convite_a_disparar_o_que_ja_esta_no_ar(estado)
        log = self.dir / f"{trabalho}{SUFIXO_DO_LOG}"
        estado["log"] = (log.read_text(encoding="utf-8",
                                       errors="replace")[-CAUDA_DO_LOG_NA_TELA:]
                         if log.exists() else "")
        return estado

    def _issues_abertas_do_repositorio(self, repositorio: str) -> dict:
        try:
            r = subprocess.run(
                ["gh", "issue", "list", "--repo", repositorio, "--state",
                 "open", "--limit", str(LIMITE_DE_ISSUES_NO_QUADRO),
                 "--json", "number,title"],
                capture_output=True, text=True, timeout=TIMEOUT_DO_GH_S)
            if r.returncode != 0:
                return {"issues": [], "recado": RECADO_GH_MUDO}
            return {"issues": json.loads(r.stdout), "repositorio": repositorio}
        except (OSError, subprocess.SubprocessError, ValueError):
            return {"issues": [], "recado": RECADO_SEM_REDE_OU_GH}

    def backlog_das_issues_com_cache(self) -> dict:
        momento = time.time()
        with self.trava:
            fresco = momento - self._quadro_em
            if self._quadro and fresco < INTERVALO_DO_QUADRO_S_POR_CORTESIA_DE_REDE:
                return self._quadro
        configuracao = configuracao_do_executor_sem_validar(self.cwd) or {}
        repositorio = (configuracao.get("issues") or {}).get("repositorio") or ""
        if not repositorio or MARCA_DE_MOLDE_NAO_PREENCHIDO in repositorio:
            achado = {"issues": [], "recado": RECADO_SEM_REPOSITORIO_DE_ISSUES}
        else:
            achado = self._issues_abertas_do_repositorio(repositorio)
        with self.trava:
            self._quadro, self._quadro_em = achado, momento
        return achado

    def _resumo_do_trabalho(self, nome: str) -> dict:
        gravado = estado_que_o_motor_gravou(self.dir, nome) or {}
        tem_roteiro_ao_lado = (self.dir / f"{nome}{SUFIXO_DO_ROTEIRO}").exists()
        return {"nome": nome,
                "execucao": bool(gravado) or tem_roteiro_ao_lado,
                "situacao": gravado.get("situacao"),
                "issue": gravado.get("issue")}

    def trabalhos(self) -> list:
        if not self.dir.is_dir():
            return []
        pastas = sorted((d for d in self.dir.iterdir() if d.is_dir()),
                        key=lambda d: d.name, reverse=True)
        return [self._resumo_do_trabalho(pasta.name) for pasta in pastas]


PAGINA = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mesa do executor de roteiros</title><style>
/* A mesa é um instrumento, não um site. Uma família monoespaçada carrega
   todo dado e todo rótulo — placa de equipamento, silkscreen —, e a sans
   entra só onde há frase para ler. Cor é SINAL: o que não é estado não tem
   cor. */
:root{
  --papel:#fbfaf7; --tinta:#1c1b19; --grafite:#6b6862; --fraco:#9a968d;
  --linha:#e5e2da; --sulco:#f1eee7;
  --segue:#2f6f4e; --para:#a32e28; --pergunta:#b0741e; --corre:#2b5c8a;
  --mono:ui-monospace,"SF Mono","Cascadia Mono","Roboto Mono",Menlo,monospace;
  --sans:ui-sans-serif,system-ui,"Segoe UI",Roboto,sans-serif;
}
@media(prefers-color-scheme:dark){:root{
  --papel:#17161a; --tinta:#eceae4; --grafite:#9b978f; --fraco:#6d6960;
  --linha:#2c2a2f; --sulco:#201f24;
  --segue:#5fae83; --para:#e0685f; --pergunta:#e0a34e; --corre:#6ea8dd;
}}
*{box-sizing:border-box}
body{margin:0;padding:28px 20px 64px;background:var(--papel);color:var(--tinta);
  font:14px/1.55 var(--sans);-webkit-font-smoothing:antialiased}
.mesa{max-width:1080px;margin:0 auto}

/* placa de identificação */
.placa{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;
  border-bottom:2px solid var(--tinta);padding-bottom:10px;margin-bottom:2px}
.placa h1{margin:0;font:600 15px/1 var(--mono);letter-spacing:.22em;
  text-transform:uppercase}
.selo{font:500 11px/1 var(--mono);letter-spacing:.1em;color:var(--grafite);
  border:1px solid var(--linha);border-radius:2px;padding:4px 7px}
.farol{margin-left:auto;display:flex;align-items:center;gap:7px;
  font:600 11px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase}
.bulbo{width:8px;height:8px;border-radius:50%;background:var(--fraco);
  box-shadow:0 0 0 3px color-mix(in srgb,var(--fraco) 22%,transparent)}
.f-corre .bulbo{background:var(--corre);box-shadow:0 0 0 3px color-mix(in srgb,var(--corre) 22%,transparent);animation:pulsa 1.6s ease-in-out infinite}
.f-corre{color:var(--corre)} .f-segue .bulbo{background:var(--segue)} .f-segue{color:var(--segue)}
.f-para .bulbo{background:var(--para)} .f-para{color:var(--para)}
.f-pergunta .bulbo{background:var(--pergunta)} .f-pergunta{color:var(--pergunta)}
@keyframes pulsa{0%,100%{opacity:1}50%{opacity:.35}}
@media(prefers-reduced-motion:reduce){.f-corre .bulbo{animation:none}}

/* coordenadas: onde a máquina está apoiada */
.coord{display:grid;grid-template-columns:auto 1fr;gap:0 18px;
  border-bottom:1px solid var(--linha);padding:12px 0;margin-bottom:20px}
.coord dt{font:500 10px/1.9 var(--mono);letter-spacing:.16em;color:var(--fraco);
  text-transform:uppercase}
.coord dd{margin:0;font:13px/1.9 var(--mono);word-break:break-all}

/* comandos */
.comandos{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:6px}
label.campo{display:flex;align-items:center;gap:7px;
  font:500 10px/1 var(--mono);letter-spacing:.14em;color:var(--fraco);
  text-transform:uppercase}
select,input,textarea{font:13px/1.4 var(--mono);color:var(--tinta);
  background:var(--sulco);border:1px solid var(--linha);border-radius:3px;
  padding:7px 9px}
textarea{width:100%;min-height:104px;resize:vertical;margin:10px 0 0;
  background:var(--sulco)}
button{font:600 11px/1 var(--mono);letter-spacing:.16em;text-transform:uppercase;
  color:var(--papel);background:var(--tinta);border:0;border-radius:3px;
  padding:11px 20px;cursor:pointer}
button:disabled{opacity:.4;cursor:default}
:focus-visible{outline:2px solid var(--corre);outline-offset:2px}
.nota{font:12px/1.5 var(--sans);color:var(--fraco);flex:1 1 220px}
.direita{margin-left:auto}

/* A ASSINATURA: a fita de evidências. O encadeador imprime uma evidência por etapa,
   em ordem — a tela mostra a fita saindo dele, com a borda serrilhada de
   papel picotado feita só com gradiente. */
.fita{margin:24px 0 0;border:1px solid var(--linha);border-radius:3px;
  background:var(--sulco);overflow:hidden}
.fita-topo{display:flex;justify-content:space-between;align-items:center;
  padding:9px 14px 9px 30px;border-bottom:1px solid var(--linha);
  font:500 10px/1 var(--mono);letter-spacing:.16em;color:var(--fraco);
  text-transform:uppercase}
.tira{position:relative;margin:0;padding:0;list-style:none}
.tira::before{content:"";position:absolute;left:9px;top:0;bottom:0;width:7px;
  background:radial-gradient(circle at 3.5px 5px,var(--papel) 2.2px,transparent 2.4px)
    0 0/7px 13px repeat-y}
.linha-r{display:grid;grid-template-columns:34px 1fr 84px 52px;gap:12px;
  align-items:baseline;padding:11px 14px 11px 30px;
  border-bottom:1px dashed var(--linha);font:13px/1.5 var(--mono)}
.linha-r:last-child{border-bottom:0}
.ordem{color:var(--fraco);font-size:11px;letter-spacing:.08em}
.nome{font-weight:500}
.vd{font:600 10px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase}
.vd.segue{color:var(--segue)}
.desenho{display:flex;flex-wrap:wrap;align-items:center;gap:.35rem;margin:.6rem 0}
.passo{padding:.2rem .5rem;border-radius:.35rem;font-size:.82rem;
  border:1px solid var(--borda);white-space:nowrap}
.passo.segue{background:var(--segue);color:#fff;border-color:var(--segue)}
.passo.para{background:var(--para);color:#fff;border-color:var(--para)}
.passo.pergunta{background:var(--pergunta);color:#000;border-color:var(--pergunta)}
.passo.espera{opacity:.55}
.passo.agora{outline:2px solid var(--corre);outline-offset:1px;font-weight:600}
.seta{opacity:.4;font-size:.8rem}
.conta{margin:.1rem 0 .6rem;font-size:.8rem;opacity:.75}
.quadro{margin:.5rem 0;border:1px solid var(--borda);border-radius:.4rem;
  max-height:9rem;overflow:auto;font-size:.85rem}
.quadro-topo{padding:.25rem .5rem;opacity:.7;font-size:.78rem;
  border-bottom:1px solid var(--borda)}
.issue{display:flex;gap:.5rem;align-items:center;padding:.2rem .5rem}
.issue .num{opacity:.6;min-width:2.6rem}
.issue .tit{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.disparar-issue{font-size:.75rem;padding:.1rem .45rem} .vd.para{color:var(--para)}
.vd.pergunta{color:var(--pergunta)} .vd.espera{color:var(--fraco)}
.ciclo{color:var(--fraco);font-size:11px;text-align:right}
.detalhe{grid-column:2/-1;font:12.5px/1.55 var(--sans);color:var(--grafite);
  margin-top:5px}
.detalhe b{color:var(--tinta)}
.vazia{padding:22px 30px;color:var(--fraco);font:13px/1 var(--mono)}

/* recados */
.recado{border-left:2px solid var(--corre);background:var(--sulco);
  padding:12px 15px;margin:20px 0 0;border-radius:0 3px 3px 0;
  font:13.5px/1.6 var(--sans)}
.recado b{font:600 10px/1 var(--mono);letter-spacing:.16em;text-transform:uppercase;
  display:block;margin-bottom:6px;color:var(--grafite)}
.recado.perg{border-left-color:var(--pergunta)}
.recado.perg b{color:var(--pergunta)}
.recado.ruim{border-left-color:var(--para)} .recado.ruim b{color:var(--para)}

/* rodapé de vivacidade e o log cru */
.rodape{display:flex;gap:10px 26px;flex-wrap:wrap;align-items:baseline;
  margin-top:16px;padding-top:12px;border-top:1px solid var(--linha);
  font:12px/1.6 var(--mono);color:var(--grafite)}
.rodape b{color:var(--tinta);font-weight:600}
details{margin-top:16px}
summary{cursor:pointer;font:500 10px/1 var(--mono);letter-spacing:.16em;
  color:var(--fraco);text-transform:uppercase;padding:6px 0}
pre{margin:8px 0 0;padding:13px 15px;background:var(--sulco);
  border:1px solid var(--linha);border-radius:3px;overflow:auto;max-height:300px;
  font:12px/1.6 var(--mono);white-space:pre-wrap;color:var(--grafite)}
.oquefaz{grid-column:1/-1;margin:2px 0 6px;padding:8px 10px;
  border-left:3px solid var(--linha);background:var(--fundo2, transparent);
  font:12px/1.55 var(--mono);white-space:pre-wrap;color:var(--grafite)}
@media(max-width:620px){
  .linha-r{grid-template-columns:28px 1fr;gap:6px}
  .vd,.ciclo{grid-column:2;text-align:left}
  .coord{grid-template-columns:1fr}
}
</style></head><body><div class="mesa">

<div class="placa">
  <h1>Mesa do executor de roteiros</h1>
  <span class="selo" id="versao">—</span>
  <span class="farol" id="farol"><span class="bulbo"></span><span id="farol-txt">sem trabalho</span></span>
</div>

<dl class="coord">
  <dt>repositório</dt><dd id="repositorio">—</dd>
  <dt>sessão</dt><dd id="alvo">—</dd>
  <dt>evidências</dt><dd id="evidencias">—</dd>
</dl>

<div class="comandos">
  <label class="campo">disparar
    <select id="modo"><option value="prompt">um pedido meu</option></select>
  </label>
  <div id="oquefaz" class="oquefaz" hidden></div>
  <button id="b">Disparar</button>
  <label class="campo" id="lturnos">turnos
    <input id="turnos" type="number" value="24" min="4" max="120" style="width:62px">
  </label>
  <label class="campo" id="lteto" title="quantas vezes a execução pode reprovar antes de escalar">ciclos
    <input id="teto" type="number" value="3" min="1" max="9" style="width:52px">
  </label>
  <label class="campo" id="lissue" title="o número da issue que este trabalho atende: a execução conta a história lá, passo a passo">issue
    <input id="issue" type="number" min="1" placeholder="—" style="width:64px">
  </label>
  <span class="nota" id="dica"></span>
  <label class="campo direita" title="mostrar também os trabalhos que já terminaram">
    <input id="historico" type="checkbox"> histórico
  </label>
  <label class="campo direita">acompanhar <select id="sel"></select></label>
</div>
<div id="quadro" class="quadro"></div>
<textarea id="p" placeholder="O pedido, completo. A sessão nasce sem contexto: diga onde olhar, o que medir e o que você aceita como prova."></textarea>

<div id="saida"></div>
</div>
<script>
const $=i=>document.getElementById(i);
let atual=null, assinatura='', parado=false;

const ESTADOS={'aguardando-aprovacao':['f-pergunta','pergunta'],
  'parada':['f-para','parada'],'completa':['f-segue','completa'],
  'em-curso':['f-corre','trabalhando']};
const TITULOS={'aguardando-aprovacao':'❓ PERGUNTA','parada':'⛔ parada',
  'completa':'✓ completa','em-curso':'⏳ rodando'};

function esc(s){return String(s??'').replace(/[<&>]/g,c=>({'<':'&lt;','&':'&amp;','>':'&gt;'}[c]))}
function mm(s){return s==null?'?':Math.floor(s/60)+'m'+String(s%60).padStart(2,'0')}
function modoRoteiro(){return $('modo').value!=='prompt'}

let ROTINAS={};
function ajusta(){
  const m=modoRoteiro();
  for(const i of ['p','lteto','lturnos'])$(i).style.display=m?'none':'';
  const cx=$('oquefaz'), texto=m?(ROTINAS[$('modo').value]||''):'';
  cx.textContent=texto; cx.hidden=!texto;
  $('dica').textContent=m
    ?'execução de várias etapas — o prompt de cada uma está dentro do arquivo'
    :'vira uma execução de uma etapa mais a verificação. Turnos de menos = a sessão morre sem entregar nada';
}

// Vivacidade: sessão de modelo espera a API quase o tempo todo — medido, 443s
// de relógio para 5s de CPU. O sinal aqui não é processador: é o processo
// existir, quantas sessões respiram, e quanto falta para o teto que mata
// sozinho. Espera com prazo não é travamento.
function vivo(v){
  if(!v||v.situacao==='desconhecida')return '';
  if(v.situacao==='encerrado')return `processo <b>encerrado</b> · exit ${v.codigo}`;
  // Espera não é trabalho. O motor grava dormindo e aguardando-resposta, e a
  // mesa repete o que ele gravou em vez de dizer "trabalhando" com ninguém
  // trabalhando — era o defeito 4.
  if(v.situacao==='dormindo')
    return `<b>dormindo</b> até ${v.ate||'?'} (${v.porque||'espera'})` +
           `${v.etapa?` na etapa <b>${v.etapa}</b>`:''} · ninguém está trabalhando`;
  if(v.situacao==='aguardando-resposta')
    return `<b>aguardando você</b> na issue ${v.issue||'?'}` +
           `${v.etapa?`, etapa <b>${v.etapa}</b>`:''} · responda lá e retome`;
  const s=v.sessoes==null?'sessões não medidas aqui'
    :`<b>${v.sessoes}</b> sessão${v.sessoes===1?'':'es'} viva${v.sessoes===1?'':'s'}`;
  return `${s} · <b>${mm(v.decorrido_s)}</b> corridos · morre sozinha em ${mm(v.resta_s)}`;
}

function farol(estado){
  const [cls,txt]=ESTADOS[estado]||['','sem trabalho'];
  $('farol').className='farol '+cls; $('farol-txt').textContent=txt;
  document.title=(TITULOS[estado]?TITULOS[estado]+' · ':'')+'Mesa do executor de roteiros';
}

function fita(d){
  const et=d.etapas||[];
  if(!et.length)return '<p class="vazia">nenhuma evidência ainda</p>';
  return et.map(e=>{
    const vd=e.veredito||'espera';
    const faltas=(e.faltas||[]).map(esc).join('<br>');
    const perg=e.pergunta?`<b>${esc(e.pergunta)}</b>`:'';
    const det=[perg,faltas].filter(Boolean).join('<br>');
    return `<li class="linha-r">
      <span class="ordem">${String(e.ordem).padStart(2,'0')}</span>
      <span class="nome">${esc(e.nome)}</span>
      <span class="vd ${vd}">${vd==='espera'?'·····':vd}</span>
      <span class="ciclo">${e.ciclo?e.ciclo.i+'/'+e.ciclo.teto:''}</span>
      ${det?`<span class="detalhe">${det}</span>`:''}</li>`;
  }).join('');
}

// O desenho da execução: a mesma matéria-prima da fita, lida de relance.
// Cada etapa é um quadrado — verde passou, vermelho parou, e a que está em
// curso pisca. Quem olha vê o passo atual e o que falta sem ler linha.
function desenho(d){
  const et=d.etapas||[];
  if(!et.length)return '';
  const atual=et.findIndex(e=>!e.veredito);
  const passos=et.map((e,i)=>{
    const vd=e.veredito||'espera';
    const eu=(i===atual)?' agora':'';
    return `<span class="passo ${vd}${eu}" title="${esc(e.nome)}: ${vd}">` +
           `${esc(e.nome)}</span>`;
  }).join('<span class="seta">→</span>');
  const feitas=et.filter(e=>e.veredito).length;
  return `<div class="desenho">${passos}</div>` +
         `<p class="conta">${feitas} de ${et.length} etapas · ` +
         `${et.length-feitas} pela frente</p>`;
}

function pinta(d){
  if(d.erro){$('saida').innerHTML=`<div class="recado ruim"><b>não consegui ler</b>${esc(d.erro)}</div>`;farol();return}
  farol(d.estado);
  const perg=(d.etapas||[]).filter(e=>e.pergunta);
  const v=vivo(d.vivacidade);
  $('saida').innerHTML=`
    ${perg.length?`<div class="recado perg"><b>o executor de roteiros está te perguntando</b>
      ${perg.map(e=>`<code>${esc(e.nome)}</code>: ${esc(e.pergunta)}`).join('<br>')}
      <br><br>Ela fica parada até você responder — nada roda enquanto isso.</div>`:''}
    ${desenho(d)}
    <div class="fita">
      <div class="fita-topo"><span>fita de evidências</span>
        <span>${esc(d.estado||'')} · ${d.paras??0} parada${d.paras===1?'':'s'}</span></div>
      <ul class="tira">${fita(d)}</ul>
    </div>
    ${d.proxima_acao?`<div class="recado"><b>próxima ação</b>${esc(d.proxima_acao)}</div>`:''}
    ${v?`<div class="rodape">${v}</div>`:''}
    ${d.log?`<details><summary>log da execução</summary><pre>${esc(d.log)}</pre></details>`:''}`;
}

async function ciclo(){
  const t=$('sel').value;
  let d; try{ d=await (await fetch('/estado?trabalho='+encodeURIComponent(t||''))).json() }
  catch(e){ return }
  $('versao').textContent='camada '+d.versao;
  $('repositorio').textContent=d.repositorio; $('alvo').textContent=d.alvo;
  $('evidencias').textContent=d.evidencias;

  const md=$('modo'), antesM=md.value;
  const listaM=['prompt'].concat(d.roteiros);
  if(md.dataset.chave!==listaM.join('|')){
    md.dataset.chave=listaM.join('|');
    md.innerHTML='<option value="prompt">um pedido meu</option>'
      +d.roteiros.map(n=>`<option value="${esc(n)}">${esc(n)}</option>`).join('');
    if(antesM)md.value=antesM;
  }
  if(d.rotinas){
    ROTINAS={}; for(const r of d.rotinas)ROTINAS[r.nome]=r.descricao;
  }
  ajusta();
  // O backlog do quadro configurado, e o disparo a partir de uma issue.
  const q=$('quadro');
  if(q){
    const qs=(d.quadro&&d.quadro.issues)||[];
    const chave=JSON.stringify(qs)+(d.modo||'');
    if(q.dataset.chave!==chave){
      q.dataset.chave=chave;
      const soIssues=d.modo==='so-issues';
      q.innerHTML=qs.length
        ? `<div class="quadro-topo">backlog de ${esc((d.quadro||{}).repositorio||'')}</div>`
          + qs.map(i=>`<div class="issue"><span class="num">#${i.number}</span>
              <span class="tit">${esc(i.title)}</span>
              ${soIssues?'':`<button class="disparar-issue" data-n="${i.number}">disparar</button>`}
             </div>`).join('')
        : `<div class="quadro-topo">${esc((d.quadro||{}).recado||'sem dado')}</div>`;
      q.querySelectorAll('.disparar-issue').forEach(b=>b.onclick=()=>{
        $('p').value=`Trabalhe a issue #${b.dataset.n}: leia o corpo dela `
          +`e siga o prompt refinado que estiver lá.`;
        $('issue').value=b.dataset.n; $('p').focus();
      });
    }
  }
  // Trabalho terminado sai da lista padrão: mesa com trinta itens mortos
  // esconde o que está vivo. O histórico continua a um clique.
  const tudo=$('historico')&&$('historico').checked;
  const lista=tudo?d.trabalhos
    :d.trabalhos.filter(x=>!['completa','parada'].includes(x.situacao));
  const s=$('sel'), nomes=lista.map(x=>x.nome);
  if(s.dataset.chave!==nomes.join('|')){
    s.dataset.chave=nomes.join('|');
    const antes=s.value;
    const selo=x=>x.situacao==='dormindo'?' 💤':x.situacao==='aguardando-resposta'?' ⏸'
      :x.situacao==='completa'?' ✅':x.situacao==='parada'?' ❌':'';
    s.innerHTML=lista.map(x=>`<option value="${esc(x.nome)}">${esc(x.nome)}${selo(x)}${x.execucao?'':' (avulso)'}</option>`).join('')
      ||'<option value="">nenhum</option>';
    if(antes&&nomes.includes(antes))s.value=antes;
    else if(atual&&nomes.includes(atual))s.value=atual;
  }

  // Com uma execução no ar, o botão de disparar FECHA. A trava por alvo
  // recusaria o segundo disparo, mas deixar o botão vivo é convidar para o
  // erro e explicar depois — e a mesa já sabe, pelo estado gravado, que há
  // trabalho andando. Vale para execução disparada aqui ou fora daqui.
  const EM_CURSO=['rodando','dormindo','aguardando-resposta'];
  const ocupada=d.trabalhos.filter(x=>EM_CURSO.includes(x.situacao));
  const b=$('b');
  if(b){
    b.disabled=ocupada.length>0;
    b.title=ocupada.length
      ? `${ocupada[0].nome} está no ar (${ocupada[0].situacao}) — a trava do alvo recusaria um segundo disparo`
      : '';
    b.textContent=ocupada.length?'No ar…':'Disparar';
  }

  const a=d.andamento;
  if(!a){farol();return}
  if(!nomes.includes(t)||!d.trabalhos.find(x=>x.nome===t&&x.execucao)){
    $('saida').innerHTML=`<div class="recado"><b>fora do executor de roteiros</b>
      <code>${esc(t)}</code> é trilha de evidências avulsas — de um gancho, por
      exemplo —, sem roteiro ao lado. Lida como execução daria estado falso,
      então a mesa não opina.</div>`; farol(); return;
  }
  // Só repinta quando algo mudou: a mesa fica aberta por horas e repintar
  // HTML a cada 2,5s por nada custa bateria e derruba texto selecionado.
  const nova=JSON.stringify(a);
  if(nova!==assinatura){assinatura=nova; pinta(a)}
  parado=a.processo!=='rodando';
}

async function disparar(){
  const corpo=modoRoteiro()?{roteiro:$('modo').value}
    :{prompt:$('p').value.trim(),teto:+$('teto').value,turnos:+$('turnos').value,issue:+$('issue').value||null};
  if(!modoRoteiro()&&!corpo.prompt){$('p').focus();return}
  $('b').disabled=true; $('b').textContent='Disparando';
  let d; try{
    d=await (await fetch('/disparar',{method:'POST',
      headers:{'content-type':'application/json'},body:JSON.stringify(corpo)})).json();
  } finally { $('b').disabled=false; $('b').textContent='Disparar' }
  if(d.erro){$('saida').innerHTML=`<div class="recado ruim"><b>não disparei</b>${esc(d.erro)}</div>`;return}
  atual=d.trabalho; assinatura=''; await ciclo(); $('sel').value=atual; ciclo();
}

$('b').onclick=disparar;
$('sel').onchange=()=>{assinatura='';ciclo()};
$('modo').onchange=ajusta;
ajusta(); ciclo();
// Ritmo por necessidade: 2,5s enquanto a execução anda, 10s quando não há o
// que ver. Uma mesa aberta a noite inteira não deve acordar o disco à toa.
setInterval(()=>{if(!parado||Math.random()<.25)ciclo()},2500);
</script></body></html>"""


def corpo_com_coordenadas_modo_e_quadro(ponte: PonteParaOEncadeador) -> dict:
    configuracao = configuracao_do_executor_sem_validar(ponte.cwd) or {}
    return {"versao": versao_da_camada_declarada_no_topo_do_montar(),
            "repositorio": str(RAIZ),
            "alvo": str(ponte.cwd),
            "evidencias": str(ponte.dir),
            "trabalhos": ponte.trabalhos(),
            "roteiros": ponte.catalogo(),
            "rotinas": ponte.catalogo_com_descricao(),
            "modo": configuracao.get("modo"),
            "quadro": ponte.backlog_das_issues_com_cache()}


def prefixo_do_nome_do_roteiro(escolhido: str) -> str:
    limpo = re.sub(r"[^a-z0-9]+", "-", Path(escolhido).stem.lower()).strip("-")
    return limpo or PREFIXO_DA_EXECUCAO_SEM_NOME


def roteiro_e_prefixo_do_corpo(ponte: PonteParaOEncadeador,
                               corpo: dict) -> tuple:
    escolhido = (corpo.get("roteiro") or "").strip()
    if escolhido:
        roteiro, erro = ponte.ler_roteiro_do_catalogo(escolhido)
        if erro:
            return None, None, erro
        return roteiro, prefixo_do_nome_do_roteiro(escolhido), None
    prompt = (corpo.get("prompt") or "").strip()
    if not prompt:
        return None, None, ERRO_SEM_PEDIDO
    if prompt.lstrip().startswith("{") and '"etapas"' in prompt:
        return None, None, ERRO_ROTEIRO_COLADO_NO_LUGAR_DO_PEDIDO
    teto = inteiro_na_faixa_ou_padrao(corpo.get("teto"), TETO_MINIMO,
                                      TETO_MAXIMO, TETO_PADRAO_DE_CICLOS)
    turnos = inteiro_na_faixa_ou_padrao(
        corpo.get("turnos"), TURNOS_MINIMO, TURNOS_MAXIMO,
        TURNOS_PADRAO_ACIMA_DO_TETO_DO_MOTOR)
    issue = corpo.get("issue")
    issue = issue if isinstance(issue, int) and issue > 0 else None
    prefixo = f"issue-{issue}" if issue else PREFIXO_DO_PEDIDO_DO_PAINEL
    return roteiro_do_pedido_com_verificacao(prompt, teto, turnos, issue), \
        prefixo, None


def fazer_handler(ponte: PonteParaOEncadeador):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_):
            return SILENCIO_DO_SERVIDOR

        def _envia(self, corpo: bytes, tipo: str, codigo: int = 200):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def _json(self, dado: dict, codigo: int = 200):
            self._envia(json.dumps(dado, ensure_ascii=False).encode(),
                        "application/json; charset=utf-8", codigo)

        def do_GET(self):
            rota = urllib.parse.urlparse(self.path)
            if rota.path == "/":
                return self._envia(PAGINA.encode(), "text/html; charset=utf-8")
            if rota.path == "/trabalhos":
                return self._json(corpo_com_coordenadas_modo_e_quadro(ponte))
            if rota.path == "/estado":
                consulta = urllib.parse.parse_qs(rota.query)
                nome = (consulta.get("trabalho") or [""])[0]
                corpo = corpo_com_coordenadas_modo_e_quadro(ponte)
                if nome and not recusa_do_nome_de_trabalho(nome):
                    try:
                        corpo["andamento"] = ponte.andamento(
                            nome, ponte.dir / f"{nome}{SUFIXO_DO_ROTEIRO}")
                    except (OSError, subprocess.SubprocessError) as e:
                        corpo["andamento"] = {
                            "erro": ERRO_ANDAMENTO_FALHOU.format(e)}
                return self._json(corpo)
            if rota.path == "/andamento":
                consulta = urllib.parse.parse_qs(rota.query)
                nome = (consulta.get("trabalho") or [""])[0]
                if erro := recusa_do_nome_de_trabalho(nome):
                    return self._json({"erro": erro}, 400)
                roteiro = ponte.dir / f"{nome}{SUFIXO_DO_ROTEIRO}"
                try:
                    return self._json(ponte.andamento(nome, roteiro))
                except (OSError, subprocess.SubprocessError) as e:
                    return self._json(
                        {"erro": ERRO_ANDAMENTO_FALHOU.format(e)}, 500)
            return self._json({"erro": ERRO_ROTA_DESCONHECIDA}, 404)

        def do_POST(self):
            if urllib.parse.urlparse(self.path).path != "/disparar":
                return self._json({"erro": ERRO_ROTA_DESCONHECIDA}, 404)
            try:
                tamanho = int(self.headers.get("Content-Length") or 0)
                corpo = json.loads(self.rfile.read(tamanho) or b"{}")
            except (ValueError, json.JSONDecodeError):
                return self._json({"erro": ERRO_CORPO_INVALIDO}, 400)
            if ocupado := ponte.ocupado():
                return self._json(
                    {"erro": ERRO_ALVO_OCUPADO.format(ocupado)}, 409)
            roteiro, prefixo, erro = roteiro_e_prefixo_do_corpo(ponte, corpo)
            if erro:
                return self._json({"erro": erro}, 400)
            trabalho = nome_de_trabalho(prefixo)
            if erro := recusa_do_nome_de_trabalho(trabalho):
                return self._json({"erro": erro}, 400)
            try:
                return self._json(ponte.disparar(roteiro, trabalho))
            except (OSError, subprocess.SubprocessError) as e:
                return self._json(
                    {"erro": ERRO_DISPARO_FALHOU.format(e)}, 500)

    return Handler


class BancadaDoPainel:
    def __init__(self):
        self.casos = 0
        self.falhas = []

    def caso(self, nome, ok) -> None:
        self.casos += 1
        if not ok:
            self.falhas.append(nome)


def versao_impressa_pelo_instalador():
    instalador = RAIZ / INSTALADOR
    if not instalador.is_file():
        return versao_da_camada_declarada_no_topo_do_montar()
    saida = subprocess.run(
        [sys.executable, str(instalador), BANDEIRA_DE_VERSAO],
        capture_output=True, text=True,
        timeout=TEMPO_DO_INSTALADOR).stdout.split(MARCA_DA_VERSAO)[-1].split()
    return saida[0] if saida else ""


def _sobre_a_ponte_e_o_catalogo(b) -> None:
    with tempfile.TemporaryDirectory(prefix="painel-h6-") as tmp:
        base = Path(tmp)
        (base / "evidencias" / "t-dorme").mkdir(parents=True)
        (base / "evidencias" / "t-dorme" / "estado.json").write_text(json.dumps({
            "situacao": "dormindo", "ate": "12:36", "porque": "limite de uso",
            "etapa": "analisa", "desde": "2026-08-18T06:36:00-03:00"}),
            encoding="utf-8")
        (base / "evidencias" / "t-espera").mkdir(parents=True)
        (base / "evidencias" / "t-espera" / "estado.json").write_text(json.dumps({
            "situacao": "aguardando-resposta", "issue": 39,
            "etapa": "decide"}), encoding="utf-8")
        (base / "evidencias" / "t-pronta").mkdir(parents=True)
        (base / "evidencias" / "t-pronta" / "estado.json").write_text(json.dumps({
            "situacao": "completa"}), encoding="utf-8")

        class ProcVivo:
            pid = 1

            def poll(self):
                return None

        v = vivacidade(ProcVivo(), time.time() - 60,
                       estado_que_o_motor_gravou(base / "evidencias", "t-dorme"))
        b.caso("motor dormindo NÃO é 'trabalhando' na mesa",
             v["situacao"] == "dormindo" and v["ate"] == "12:36")
        v = vivacidade(ProcVivo(), time.time() - 60,
                       estado_que_o_motor_gravou(base / "evidencias", "t-espera"))
        b.caso("aguardando resposta aparece com o número da issue",
             v["situacao"] == "aguardando-resposta" and v["issue"] == 39)
        v = vivacidade(ProcVivo(), time.time() - 60, None)
        b.caso("sem estado gravado, a mesa segue como era",
             v["situacao"] == "trabalhando")
        b.caso("estado ilegível não derruba a leitura",
             estado_que_o_motor_gravou(base / "evidencias", "nao-existe") is None)

        ponte = PonteParaOEncadeador(base, base / "evidencias", [])
        situacoes = {x["nome"]: x["situacao"] for x in ponte.trabalhos()}
        b.caso("a lista de trabalhos carrega a situação de cada um",
             situacoes == {"t-dorme": "dormindo",
                           "t-espera": "aguardando-resposta",
                           "t-pronta": "completa"})
        b.caso("e ela sai do disco, sem um subprocesso por trabalho",
             ponte.trabalhos() == ponte.trabalhos())

        e = calar_o_convite_a_disparar_o_que_ja_esta_no_ar({
            "processo": "rodando", "estado": "em-curso",
            "proxima_acao": "responda na issue",
            "vivacidade": {"situacao": "aguardando-resposta"}})
        b.caso("quem espera não recebe 'rodando agora — espere'",
             e["proxima_acao"] == "responda na issue")
        e = calar_o_convite_a_disparar_o_que_ja_esta_no_ar({
            "processo": "rodando", "estado": "em-curso",
            "proxima_acao": "execute", "vivacidade": {}})
        b.caso("mas o convite a disparar de novo continua calado",
             "ão dispare de novo" in e["proxima_acao"])

        b.caso("sem repositório configurado o quadro devolve recado, não erro",
             ponte.backlog_das_issues_com_cache()["issues"] == []
             and "sem repositório" in ponte.backlog_das_issues_com_cache()["recado"])
        (base / "nucleo").mkdir()
        (base / "nucleo" / "executor.json").write_text(json.dumps({
            "modo": "so-issues",
            "issues": {"repositorio": "${DONO}/${REPO}"}}), encoding="utf-8")
        ponte._quadro = None
        b.caso("repositório ainda no molde também não vira chamada de rede",
             "sem repositório" in ponte.backlog_das_issues_com_cache()["recado"])
        b.caso("o modo do executor é lido para a mesa esconder o disparo",
             (configuracao_do_executor_sem_validar(base) or {}).get("modo")
             == "so-issues")



def _sobre_o_disparo_e_a_regua(b) -> None:
    b.caso("o vínculo com a issue viaja no roteiro do pedido",
         roteiro_do_pedido_com_verificacao("x", 3, 24, 39)["issue"] == 39)
    b.caso("e sem issue o roteiro não inventa o campo",
         "issue" not in roteiro_do_pedido_com_verificacao("x"))
    b.caso("o botão de disparar fecha com execução no ar",
         "b.disabled=ocupada.length>0" in PAGINA
         and "'rodando','dormindo','aguardando-resposta'" in PAGINA)
    b.caso("e o motivo aparece no próprio botão",
         "a trava do alvo recusaria um segundo disparo" in PAGINA)
    b.caso("a página desenha a execução e o backlog",
         'function desenho' in PAGINA and 'id="quadro"' in PAGINA
         and 'id="issue"' in PAGINA and 'id="historico"' in PAGINA)
    b.caso("o desenho usa os tokens de cor que já existem",
         '.passo.segue' in PAGINA and '.passo.agora' in PAGINA)

    b.caso("nome de trabalho passa na régua da evidência",
         recusa_do_nome_de_trabalho(nome_de_trabalho()) is None)
    b.caso("nome com barra é recusado",
         recusa_do_nome_de_trabalho("a/b") is not None)
    b.caso("nome com maiúscula é recusado",
         recusa_do_nome_de_trabalho("Painel") is not None)
    b.caso("nome vazio é recusado", recusa_do_nome_de_trabalho("") is not None)
    b.caso("nome de 65 é recusado",
         recusa_do_nome_de_trabalho("a" * 65) is not None)



def _sobre_o_roteiro_do_pedido(b) -> None:
    m = roteiro_do_pedido_com_verificacao("olhe o repositório")
    b.caso("prompt livre vira etapa de sessão", m["etapas"][0]["tipo"] == "sessao")
    b.caso("o prompt viaja inteiro", m["etapas"][0]["prompt"] == "olhe o repositório")
    b.caso("a verificação entra sempre", m["etapas"][1]["tipo"] == "verificacao")
    b.caso("a verificação depende da sessão",
         m["etapas"][1]["depende"] == ["pedido"])
    b.caso("o teto viaja", roteiro_do_pedido_com_verificacao("x", 7)["teto"] == 7)

    b.caso("o encadeador está no lugar esperado", ENCADEADOR.exists())
    b.caso("a página cita o disparo", 'id="b"' in PAGINA and "/disparar" in PAGINA)
    b.caso("a página não embute segredo",
         "token" not in PAGINA.lower() and "senha" not in PAGINA.lower())



def _sobre_o_servidor_e_a_porta(b) -> None:
    fonte = Path(__file__).read_text(encoding="utf-8")
    b.caso("o servidor atende mais de uma conexão ao mesmo tempo",
         "ThreadingHTTPServer" in fonte)
    b.caso("porta ocupada vira recado, não traceback",
         "EADDRINUSE" in fonte and "PAREI — a porta" in fonte)
    b.caso("porta livre não tem painel de controle atendendo",
         repositorio_que_responde_na_porta(1) is None)
    b.caso("segundo F5 do MESMO repositório sai 0 — o que se queria já está no "
         "ar, e sair 0 apaga o popup do depurador",
         decidir_porta_ocupada(4000, "/casa", "/casa")[0] == 0)
    b.caso("e o recado dá o endereço em vez de reclamar",
         "http://127.0.0.1:4000" in decidir_porta_ocupada(4000, "/casa", "/casa")[1])
    b.caso("painel de controle de OUTRO repositório na porta sai 2",
         decidir_porta_ocupada(4000, "/casa", "/outra")[0] == 2)
    b.caso("e o recado nomeia o outro repositório",
         "/outra" in decidir_porta_ocupada(4000, "/casa", "/outra")[1])
    b.caso("porta ocupada por quem não é painel de controle sai 2",
         decidir_porta_ocupada(4000, "/casa", None)[0] == 2)
    b.caso("a página mostra os três lugares",
         all(f'id="{i}"' in PAGINA for i in ("repositorio", "alvo", "evidencias")))
    b.caso("uma chamada por ciclo, não duas", "/estado?trabalho=" in PAGINA
         and "/andamento?trabalho=" not in PAGINA)
    b.caso("só repinta quando o estado muda", "assinatura" in PAGINA)
    b.caso("a fita de evidências é a peça central", 'class="fita"' in PAGINA
         and "fita de evidências" in PAGINA)
    b.caso("todo texto de fora passa por escape", "function esc(" in PAGINA)
    b.caso("respeita quem pediu menos movimento",
         "prefers-reduced-motion" in PAGINA)
    b.caso("foco de teclado é visível", ":focus-visible" in PAGINA)
    b.caso("tem tema claro e escuro", "prefers-color-scheme:dark" in PAGINA)
    b.caso("a versão sai do montar.py, e é a mesma que o --versao imprime",
           versao_impressa_pelo_instalador() ==
           versao_da_camada_declarada_no_topo_do_montar())
    b.caso("a página tem onde mostrar a versão", 'id="versao"' in PAGINA)
    b.caso("o título da aba grita a pergunta, para quem trocou de aba ficar "
         "sabendo que a execução travou esperando resposta",
         "aguardando-aprovacao':'❓ PERGUNTA" in PAGINA)
    b.caso("o título distingue os quatro estados",
         all(e in PAGINA for e in ("parada", "completa", "em-curso")))



def _sobre_a_pergunta_e_a_vivacidade(b) -> None:
    b.caso("a pergunta da etapa aparece na tela", "e.pergunta" in PAGINA)
    b.caso("a pergunta tem caixa própria, separada da próxima ação",
         "recado perg" in PAGINA and ".recado.perg{" in PAGINA)

    class ProcFalso:
        def __init__(self, esta_vivo, pid=1):
            self._esta_vivo, self.pid, self.returncode = esta_vivo, pid, 0

        def poll(self):
            return None if self._esta_vivo else 0

    b.caso("sem processo, a situação é desconhecida — não 'morto'",
         vivacidade(None, None)["situacao"] == "desconhecida")
    b.caso("processo encerrado é dito encerrado",
         vivacidade(ProcFalso(False), time.time())["situacao"] == "encerrado")
    vv = vivacidade(ProcFalso(True), time.time() - 120)
    b.caso("processo vivo é dito trabalhando", vv["situacao"] == "trabalhando")
    b.caso("mostra quanto tempo já corre", vv["decorrido_s"] >= 120)
    b.caso("e quanto falta para o teto que mata sozinho",
         vv["resta_s"] == TETO_SESSAO_S_ESPELHO_DO_ENCADEADOR - vv["decorrido_s"])
    b.caso("o teto do painel de controle espelha o do encadeador",
         f"TEMPO_SESSAO = {TETO_SESSAO_S_ESPELHO_DO_ENCADEADOR}" in
         (ENCADEADOR.read_text(encoding="utf-8") if ENCADEADOR.exists() else
          f"TEMPO_SESSAO = {TETO_SESSAO_S_ESPELHO_DO_ENCADEADOR}"))
    b.caso("este processo enxerga os próprios descendentes ou diz que não mede",
         isinstance(descendentes_lendo_proc(os.getpid()), list))
    b.caso("a página mostra a vivacidade", "vivo(d.vivacidade)" in PAGINA)




def _sobre_a_mesa_e_os_turnos(b) -> None:
    with tempfile.TemporaryDirectory() as t:
        base = Path(t)
        (base / "evidencias" / "vinda-de-execucao").mkdir(parents=True)
        (base / "evidencias" / "trilha-de-gancho").mkdir(parents=True)
        (base / "evidencias" / "vinda-de-execucao.roteiro.json").write_text("{}")
        (base / "roteiros").mkdir()
        (base / "roteiros" / "boa.json").write_text(
            json.dumps(roteiro_do_pedido_com_verificacao("oi")), encoding="utf-8")
        (base / "roteiros" / "quebrada.json").write_text("{isso não é json",
                                                         encoding="utf-8")
        (base / "roteiros" / "sem-etapas.json").write_text('{"teto":3}',
                                                           encoding="utf-8")
        (base / "oficiais").mkdir()
        (base / "oficiais" / "boa.json").write_text(
            json.dumps(roteiro_do_pedido_com_verificacao("sou a oficial")),
            encoding="utf-8")
        (base / "oficiais" / "so-daqui.json").write_text(
            json.dumps(roteiro_do_pedido_com_verificacao("x")), encoding="utf-8")
        ponte = PonteParaOEncadeador(base, base / "evidencias",
                                     [base / "oficiais", base / "roteiros"])

        marcas = {t["nome"]: t["execucao"] for t in ponte.trabalhos()}
        b.caso("trabalho com roteiro é execução", marcas["vinda-de-execucao"])
        b.caso("trilha de gancho NÃO é execução",
             marcas["trilha-de-gancho"] is False)

        b.caso("o catálogo junta as duas pastas, e só o que é roteiro — a "
             "quebrada e a sem-etapas ficam de fora",
             ponte.catalogo() == sorted(["boa.json", "so-daqui.json"]))

        (base / "oficiais" / "boa.md").write_text(
            "# A boa\n\nEla faz o que o dono precisa.\n", encoding="utf-8")
        descricoes = {r["nome"]: r["descricao"]
                      for r in ponte.catalogo_com_descricao()}
        b.caso("a descrição vem do .md irmão, inteira",
             "Ela faz o que o dono precisa." in descricoes["boa.json"])
        b.caso("roteiro sem .md irmão nem campo confessa que não tem descrição",
             descricoes["so-daqui.json"] == SEM_DESCRICAO)
        (base / "roteiros" / "com-campo.json").write_text(
            json.dumps(dict(roteiro_do_pedido_com_verificacao("x"),
                            descricao="a descrição mora no roteiro")),
            encoding="utf-8")
        com_campo = {r["nome"]: r["descricao"]
                     for r in ponte.catalogo_com_descricao()}
        b.caso("sem .md irmão, o campo descricao do roteiro serve",
             com_campo["com-campo.json"] == "a descrição mora no roteiro")
        b.caso("nome repetido fica com a pasta oficial",
             ponte.ler_roteiro_do_catalogo("boa.json")[0]["etapas"][0]["prompt"]
             == "sou a oficial")
        b.caso("pasta de roteiros que não existe não derruba",
             PonteParaOEncadeador(base, base / "evidencias",
                                  [base / "nao-existe"]).catalogo() == [])
        b.caso("nada rodando, nada ocupado", ponte.ocupado() is None)
        b.caso("roteiro bom é lido",
             ponte.ler_roteiro_do_catalogo("boa.json")[0] is not None)
        b.caso("roteiro ilegível vira erro, não exceção",
             ponte.ler_roteiro_do_catalogo("quebrada.json")[1] is not None)
        b.caso("roteiro sem etapas é recusado",
             ponte.ler_roteiro_do_catalogo("sem-etapas.json")[1] is not None)
        b.caso("nome fora do catálogo é recusado",
             ponte.ler_roteiro_do_catalogo("../../etc/passwd")[1] is not None)
        b.caso("caminho absoluto é recusado",
             ponte.ler_roteiro_do_catalogo("/etc/passwd")[1] is not None)

        (base / "roteiros" / "nao-e-roteiro.json").write_text(
            '{"regras": [{"id": 1}]}', encoding="utf-8")
        b.caso("json sem etapas fica fora do catálogo — a proposta de regra que "
             "a síntese escreve não é execução",
             "nao-e-roteiro.json" not in ponte.catalogo())
        b.caso("json quebrado também fica fora",
             "quebrada.json" not in ponte.catalogo())
        b.caso("roteiro de verdade continua no catálogo",
             "boa.json" in ponte.catalogo())

        pid_que_nao_existe = 2 ** 22
        ponte.gravar_trava(os.getpid(), "trabalho-vivo")
        b.caso("trava de dono vivo segura, mesmo sendo de OUTRO processo",
             ponte.ocupado() is not None)
        b.caso("a trava diz de quem é", "pid" in (ponte.ocupado() or ""))
        ponte.gravar_trava(pid_que_nao_existe, "trabalho-fantasma")
        b.caso("trava de dono morto não segura ninguém", ponte.ocupado() is None)
        ponte._arquivo_de_trava_deste_alvo().write_text("isso não é json",
                                                        encoding="utf-8")
        b.caso("trava ilegível não trava o repositório", ponte.ocupado() is None)
        ponte._arquivo_de_trava_deste_alvo().unlink()
        b.caso("alvos diferentes, travas diferentes",
             ponte._arquivo_de_trava_deste_alvo()
             != PonteParaOEncadeador(base / "outro", base / "evidencias", [])
             ._arquivo_de_trava_deste_alvo())

    b.caso("o pedido do painel de controle declara os turnos, em vez de herdar "
         "o padrão do motor, que matava o pedido no teto",
         roteiro_do_pedido_com_verificacao("x")["etapas"][0]["max-turnos"] == 24)
    b.caso("e quem dispara pode escolher",
         roteiro_do_pedido_com_verificacao("x", 3, 60)["etapas"][0]["max-turnos"]
         == 60)
    b.caso("turnos aparece na tela, não só ciclos",
         'id="turnos"' in PAGINA and "turnos:+$('turnos').value" in PAGINA)



def _sobre_a_proxima_acao(b) -> None:
    rodando = calar_o_convite_a_disparar_o_que_ja_esta_no_ar({
        "processo": "rodando", "estado": "em-curso",
        "proxima_acao": "nada rodou ainda — rode: python ... executar ..."})
    b.caso("processo vivo: a próxima ação para de mandar executar",
         "executar" not in rodando["proxima_acao"])
    b.caso("e diz que pasta vazia no começo é o esperado",
         "evidência quando termina" in rodando["proxima_acao"])
    encerrado = calar_o_convite_a_disparar_o_que_ja_esta_no_ar({
        "processo": "encerrado", "estado": "em-curso",
        "proxima_acao": "nada rodou ainda — rode: ... executar ..."})
    b.caso("processo morto: o convite a executar FICA — ali ele é verdade",
         "executar" in encerrado["proxima_acao"])
    completa = calar_o_convite_a_disparar_o_que_ja_esta_no_ar({
        "processo": "rodando", "estado": "completa",
        "proxima_acao": "leia as evidências"})
    b.caso("execução completa não tem a mensagem trocada",
         completa["proxima_acao"] == "leia as evidências")



def _sobre_o_encadeador_de_verdade(b) -> None:
    if ENCADEADOR.exists() and shutil.which("git"):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "m.json"
            p.write_text(json.dumps(roteiro_do_pedido_com_verificacao("oi")),
                         encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(ENCADEADOR), "ensaio", "--roteiro", str(p),
                 "--trabalho", "teste-painel", "--dir", tmp, "--cwd", str(RAIZ)],
                capture_output=True, text=True, timeout=60)
            b.caso("o encadeador aceita de verdade o roteiro que o painel de "
                 "controle escreve",
                 r.returncode == 0)
            b.caso("o ensaio lista as duas etapas",
                 "pedido" in r.stdout and "verifica" in r.stdout)



TEMAS_DO_PAINEL = (
    _sobre_a_ponte_e_o_catalogo,
    _sobre_o_disparo_e_a_regua,
    _sobre_o_roteiro_do_pedido,
    _sobre_o_servidor_e_a_porta,
    _sobre_a_pergunta_e_a_vivacidade,
    _sobre_a_mesa_e_os_turnos,
    _sobre_a_proxima_acao,
    _sobre_o_encadeador_de_verdade,
)


def testar() -> int:
    b = BancadaDoPainel()
    for tema in TEMAS_DO_PAINEL:
        tema(b)
    for falha in b.falhas:
        print(RESULTADO_DO_CASO_FALHO.format(falha))
    print(RESUMO_DOS_CASOS.format(
        VEREDITO_FALHOU if b.falhas else VEREDITO_OK, b.casos)
        + (RESUMO_DAS_FALHAS.format(len(b.falhas)) if b.falhas else ""))
    return 1 if b.falhas else 0


def ler_argumentos():
    ap = argparse.ArgumentParser(description=DESCRICAO_DA_CLI)
    ap.add_argument("--cwd", help=AJUDA_CWD)
    ap.add_argument("--porta", type=int, default=PORTA_PADRAO)
    ap.add_argument("--dir", default=DIR_EVIDENCIAS_PADRAO)
    ap.add_argument("--roteiros", default=ROTEIROS_PADRAO, help=AJUDA_ROTEIROS)
    ap.add_argument("--forcar-arvore-suja", action="store_true",
                    help=AJUDA_FORCAR_ARVORE_SUJA)
    ap.add_argument("--testar", action="store_true")
    return ap.parse_args()


def recusa_do_ambiente(cwd: Path, forcar_arvore_suja: bool) -> str | None:
    if not cwd.is_dir():
        return ERRO_CWD_NAO_E_PASTA.format(cwd)
    if not ENCADEADOR.exists():
        return ERRO_SEM_ENCADEADOR
    if not shutil.which(comando_da_sessao()):
        return ERRO_SEM_O_COMANDO_CLAUDE.format(comando_da_sessao())
    if tem_mudanca_nao_commitada(cwd) and not forcar_arvore_suja:
        return ERRO_ARVORE_SUJA.format(cwd)
    return None


def caminho_sob_a_raiz(valor: str) -> Path:
    caminho = Path(valor)
    return (caminho.resolve() if caminho.is_absolute()
            else (RAIZ / caminho).resolve())


def servidor_de_uma_thread_por_conexao(porta: int, handler):
    return ThreadingHTTPServer((ENDERECO_LOCAL, porta), handler)


def recusar_porta(porta: int, erro: OSError) -> int:
    if erro.errno == errno.EADDRINUSE:
        codigo, recado = decidir_porta_ocupada(
            porta, str(RAIZ), repositorio_que_responde_na_porta(porta))
        print(recado, file=sys.stdout if codigo == CODIGO_NADA_A_FAZER
              else sys.stderr)
        return codigo
    print(ERRO_PORTA_NAO_ABRIU.format(porta, erro), file=sys.stderr)
    return CODIGO_ERRO_DE_USO


def anunciar_a_subida(porta: int, cwd: Path, dir_evidencias: Path,
                      dirs_roteiros: list, roteiros_achados: int) -> None:
    print(ANUNCIO_NO_AR.format(
        porta, versao_da_camada_declarada_no_topo_do_montar()))
    print(ANUNCIO_REPOSITORIO.format(RAIZ))
    print(ANUNCIO_SESSOES.format(cwd))
    print(ANUNCIO_EVIDENCIAS.format(dir_evidencias))
    print(ANUNCIO_ROTEIROS.format(", ".join(str(p) for p in dirs_roteiros),
                                  roteiros_achados))
    print(ANUNCIO_COMO_ENCERRAR)


def main() -> int:
    argumentos = ler_argumentos()
    if argumentos.testar:
        return testar()
    if not argumentos.cwd:
        print(ERRO_CWD_OBRIGATORIO, file=sys.stderr)
        return CODIGO_ERRO_DE_USO
    cwd = Path(argumentos.cwd).expanduser().resolve()
    if recusa := recusa_do_ambiente(cwd, argumentos.forcar_arvore_suja):
        print(recusa, file=sys.stderr)
        return CODIGO_ERRO_DE_USO

    dir_evidencias = caminho_sob_a_raiz(argumentos.dir)
    dirs_roteiros = [caminho_sob_a_raiz(p)
                     for p in argumentos.roteiros.split(",") if p.strip()]
    ponte = PonteParaOEncadeador(cwd, dir_evidencias, dirs_roteiros)
    try:
        servidor = servidor_de_uma_thread_por_conexao(argumentos.porta,
                                                      fazer_handler(ponte))
    except OSError as e:
        return recusar_porta(argumentos.porta, e)
    servidor.daemon_threads = True
    anunciar_a_subida(argumentos.porta, cwd, dir_evidencias, dirs_roteiros,
                      len(ponte.catalogo()))
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print(ANUNCIO_ENCERRADO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
