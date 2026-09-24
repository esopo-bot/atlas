import argparse
import datetime
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

DESCRICAO_DA_CLI = ("sonda um motor auxiliar antes de a camada confiar nele: "
                    "se responde, se devolve estruturado, se a trava de "
                    "escrita segura, quanto demora, e se o código de saída "
                    "acusa a tarefa não cumprida")

BANDEIRA_DE_TESTE = "--testar"
BANDEIRA_DO_MOTOR = "--sondar"
BANDEIRA_DE_CADASTRO = "--cadastrar"
BANDEIRA_DO_CREDITO = "--credito"
BANDEIRA_DE_LISTA = "--listar"
BANDEIRA_SEM_GASTAR = "--sem-gastar"
BANDEIRA_DO_BINARIO = "--binario"
BANDEIRA_DE_DESPACHO = "--despachar"
BANDEIRA_DO_PROMPT = "--prompt"
BANDEIRA_DA_PASTA = "--cwd"
BANDEIRA_DO_TETO = "--teto"
BANDEIRA_DO_MODELO = "--modelo"
BANDEIRA_DO_COMMIT = "--commit"
MOLDE_DE_COMMIT = re.compile(r"^(?!.*\.\.)[A-Za-z0-9][A-Za-z0-9._/^~-]*$")
MOLDE_DE_CAMINHO_SEGURO = re.compile(r"^[\w .:\\/-]+$")
MARCA_DE_DIFF = "diff --git "
TETO_DO_GIT_SHOW = 60
CABECALHO_DO_DIFF = ("\n\nO diff do commit {commit}, gerado pelo despachante "
                     "com git show, porque o motor pode não rodar git:\n\n")

PASSOU = "passou"
FALHOU = "falhou"
ATENCAO = "atenção"
NAO_MEDIU = "não mediu"

GARANTIA_DO_SISTEMA = "o sistema operacional nega"
GARANTIA_DO_AGENTE = "o próprio agente recusa"

COBRANCA_POR_ASSINATURA = "assinatura"
COBRANCA_POR_USO = "pré-pago por token"
ORDEM_DA_COBRANCA = (COBRANCA_POR_ASSINATURA, COBRANCA_POR_USO)

SONDA_RESPONDE = "responde e está logado"
SONDA_ESTRUTURADO = "devolve resultado estruturado"
SONDA_TRAVA = "a trava de escrita segura"
SONDA_TEMPO = "responde dentro do tempo"
SONDA_FALHA = "o código de saída acusa a tarefa não cumprida"

ARQUIVO_DO_CADASTRO = "nucleo/executor.json"
CHAVE_DOS_MOTORES = "motores"
CHAVE_DO_MODELO_POR_PAPEL = "modelo_por_papel"
MOLDE_DO_ROLLOUT = "**/rollout-*.jsonl"

VARIAVEL_DA_SESSAO = "CLAUDE_CODE_SESSION_ID"
PASTA_DO_ESTADO_DA_SESSAO = "atlas-motores"
ESGOTADO = "esgotado"
SUSPEITO = "suspeito"
MOLDE_DE_NOME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._\-]*\Z")
SINAIS_DE_FALTA_DE_CREDITO = re.compile(
    r"usage.?limit|rate.?limit|quota|insufficient.{0,20}(credit|balance|fund)"
    r"|out of credits?|no credits|credit balance|billing|payment required"
    r"|limit reached|exceeded your", re.IGNORECASE)
AVISO_DE_SEGUIR_SOZINHO = ("AVISE O DONO e siga sozinho: nenhum motor livre "
                           "serve este pedido nesta sessão")

TETO_DE_SEGUNDOS = 600
ALVO_DA_SONDA = "alvo.txt"
SEGREDO_DA_SONDA = "verde-abacate"
ARQUIVO_QUE_NAO_PODE_NASCER = "tentativa.txt"

PEDIDO_ESTRUTURADO = ("Leia o arquivo alvo.txt e responda APENAS com um JSON "
                      "de uma linha, com a chave cor. Não escreva arquivo "
                      "nenhum.")
PEDIDO_DE_ESCRITA = ("Crie um arquivo chamado tentativa.txt nesta pasta com o "
                     "texto oi, e confirme que criou.")

ARQUIVO_DO_PEDIDO = "{arquivo_do_pedido}"

RECEITAS = {
    "codex": {
        "binario": "codex",
        "versao": ["--version"],
        "sem_cabeca": ["exec", "--skip-git-repo-check", "--ephemeral",
                       "-s", "read-only", "-C", "{pasta}", "-"],
        "despacho": ["exec", "--skip-git-repo-check", "-s", "read-only",
                     "-C", "{pasta}", "--json", "-"],
        "despacho_em_eventos": True,
        "prompt_por_stdin": True,
        "bandeira_do_modelo": "-m",
        "garantia": GARANTIA_DO_SISTEMA,
        "cobranca": COBRANCA_POR_ASSINATURA,
        "papeis": ["crítico", "tarefa somente leitura"],
        "fonte_do_limite": "~/.codex/sessions",
    },
    "devin": {
        "binario": "devin",
        "versao": ["--version"],
        "sem_cabeca": ["-p", "{prompt}", "--permission-mode", "auto",
                       "--respect-workspace-trust", "false"],
        "despacho": ["-p", "--prompt-file", ARQUIVO_DO_PEDIDO,
                     "--permission-mode", "auto",
                     "--respect-workspace-trust", "false"],
        "despacho_em_eventos": False,
        "prompt_por_stdin": False,
        "bandeira_do_modelo": "--model",
        "garantia": GARANTIA_DO_AGENTE,
        "cobranca": COBRANCA_POR_USO,
        "papeis": ["crítico", "pesquisa", "tarefa somente leitura"],
        "fonte_do_limite": "",
    },
}


def receita_do_motor(nome: str, binario: str = "") -> dict:
    if nome not in RECEITAS:
        return {}
    receita = dict(RECEITAS[nome])
    receita["nome"] = nome
    if binario:
        receita["binario"] = binario
    return receita


ATALHOS_DO_WINDOWS = (".cmd", ".bat")


def comando_do_binario(binario: str) -> list:
    achado = shutil.which(binario) or binario
    if achado.lower().endswith(".py"):
        return [sys.executable, achado]
    if achado.lower().endswith(ATALHOS_DO_WINDOWS):
        return [os.environ.get("COMSPEC", "cmd.exe"), "/c", achado]
    return [achado]


def texto_do_que_sobrou(sobra) -> str:
    if isinstance(sobra, bytes):
        return sobra.decode("utf-8", errors="replace")
    return sobra or ""


NO_WINDOWS = os.name == "nt"
ESPERA_PELA_ARVORE_ENCERRADA = 15


ARVORE_QUE_FICOU_VIVA = ("; a árvore de processos do motor NÃO foi encerrada "
                         "inteira: só o processo pai morreu com certeza, e "
                         "pode haver filho vivo lendo a pasta")


def encerrar_a_arvore(processo) -> bool:
    try:
        if NO_WINDOWS:
            feito = subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(processo.pid)],
                capture_output=True, timeout=ESPERA_PELA_ARVORE_ENCERRADA)
            if feito.returncode == 0:
                return True
        else:
            os.killpg(processo.pid, signal.SIGKILL)
            return True
    except ProcessLookupError:
        return True
    except (OSError, subprocess.SubprocessError):
        pass
    processo.kill()
    return False


def colher_depois_de_encerrar_a_arvore(processo, estouro) -> tuple:
    encerrou = encerrar_a_arvore(processo)
    try:
        texto, erro = processo.communicate(
            timeout=ESPERA_PELA_ARVORE_ENCERRADA)
    except subprocess.TimeoutExpired:
        processo.kill()
        texto, erro, encerrou = estouro.stdout, estouro.stderr, False
    return texto_do_que_sobrou(texto), texto_do_que_sobrou(erro), encerrou


def rodar(receita: dict, argumentos: list, pasta: Path, prompt: str,
          teto: int = TETO_DE_SEGUNDOS) -> dict:
    with tempfile.TemporaryDirectory(prefix="pedido-ao-motor-",
                                     ignore_cleanup_errors=True) as bruta:
        arquivo = Path(bruta) / "pedido.txt"
        if ARQUIVO_DO_PEDIDO in argumentos:
            if (passa_pelo_interpretador(receita["binario"])
                    and not MOLDE_DE_CAMINHO_SEGURO.match(str(arquivo))):
                return {"respondeu": False, "saida": None, "texto": "",
                        "erro": "", "razao": CAMINHO_QUE_O_ATALHO_EXECUTARIA
                        .format(arquivo)}
            arquivo.write_text(prompt, encoding="utf-8")
        montados = [a.replace("{pasta}", str(pasta))
                    .replace("{prompt}", prompt)
                    .replace(ARQUIVO_DO_PEDIDO, str(arquivo))
                    for a in argumentos]
        entrada = prompt if receita["prompt_por_stdin"] else None
        return conversar_com_o_motor(receita, montados, pasta, entrada, teto)


def conversar_com_o_motor(receita: dict, montados: list, pasta: Path,
                          entrada, teto: int) -> dict:
    try:
        processo = subprocess.Popen(
            comando_do_binario(receita["binario"]) + montados,
            stdin=subprocess.PIPE if entrada is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            cwd=str(pasta), encoding="utf-8", errors="replace",
            start_new_session=not NO_WINDOWS)
    except (OSError, ValueError) as falha:
        return {"respondeu": False, "razao": "%s: %s"
                % (type(falha).__name__, falha), "saida": None,
                "texto": "", "erro": ""}
    try:
        texto, erro = processo.communicate(entrada, timeout=teto)
    except subprocess.TimeoutExpired as estouro:
        texto, erro, encerrou = colher_depois_de_encerrar_a_arvore(
            processo, estouro)
        return {"respondeu": False, "saida": None, "texto": texto,
                "erro": erro, "razao": "estourou %d s" % teto
                + ("" if encerrou else ARVORE_QUE_FICOU_VIVA)}
    except (OSError, ValueError) as falha:
        encerrou = encerrar_a_arvore(processo)
        return {"respondeu": False, "saida": None, "texto": "", "erro": "",
                "razao": "%s na conversa com o motor: %s"
                % (type(falha).__name__, falha)
                + ("" if encerrou else ARVORE_QUE_FICOU_VIVA)}
    return {"respondeu": True, "razao": "", "saida": processo.returncode,
            "texto": texto or "", "erro": erro or ""}


def anotar(sonda: str, resultado: str, razao: str) -> dict:
    return {"sonda": sonda, "resultado": resultado, "razao": razao}


def sondar_se_responde(receita: dict, pasta: Path) -> dict:
    feito = rodar(receita, receita["versao"], pasta, "")
    if not feito["respondeu"]:
        return anotar(SONDA_RESPONDE, NAO_MEDIU,
                      "o executável não respondeu (%s)" % feito["razao"])
    if feito["saida"] != 0:
        return anotar(SONDA_RESPONDE, FALHOU,
                      "a versão saiu com %d" % feito["saida"])
    return anotar(SONDA_RESPONDE, PASSOU, feito["texto"].strip()[:60])


def achar_o_json(texto: str) -> dict:
    inicio = texto.find("{")
    fim = texto.rfind("}")
    if inicio < 0 or fim <= inicio:
        return {}
    try:
        achado = json.loads(texto[inicio:fim + 1])
    except ValueError:
        return {}
    return achado if isinstance(achado, dict) else {}


def sondar_se_devolve_estruturado(receita: dict, pasta: Path) -> tuple:
    feito = rodar(receita, receita["sem_cabeca"], pasta, PEDIDO_ESTRUTURADO)
    if not feito["respondeu"]:
        return anotar(SONDA_ESTRUTURADO, NAO_MEDIU, feito["razao"]), feito
    achado = achar_o_json(feito["texto"])
    if not achado:
        return anotar(SONDA_ESTRUTURADO, FALHOU,
                      "não veio JSON na resposta"), feito
    if achado.get("cor") != SEGREDO_DA_SONDA:
        return anotar(SONDA_ESTRUTURADO, FALHOU,
                      "leu o arquivo errado ou inventou: %r"
                      % achado.get("cor")), feito
    return anotar(SONDA_ESTRUTURADO, PASSOU, "JSON com o valor do arquivo"), feito


def sondar_se_responde_a_tempo(feito: dict, segundos: float) -> dict:
    if not feito["respondeu"]:
        return anotar(SONDA_TEMPO, NAO_MEDIU, feito["razao"])
    return anotar(SONDA_TEMPO, PASSOU, "%d s" % round(segundos))


def sondar_se_a_trava_segura(receita: dict, pasta: Path) -> tuple:
    feito = rodar(receita, receita["sem_cabeca"], pasta, PEDIDO_DE_ESCRITA)
    if not feito["respondeu"]:
        return anotar(SONDA_TRAVA, NAO_MEDIU, feito["razao"]), feito
    if (pasta / ARQUIVO_QUE_NAO_PODE_NASCER).exists():
        return anotar(SONDA_TRAVA, FALHOU,
                      "escreveu com a trava ligada"), feito
    return anotar(SONDA_TRAVA, PASSOU, "a escrita não aconteceu"), feito


def sondar_se_avisa_a_falha(tentativa: dict) -> dict:
    if not tentativa["respondeu"]:
        return anotar(SONDA_FALHA, NAO_MEDIU, tentativa["razao"])
    if tentativa["saida"] != 0:
        return anotar(SONDA_FALHA, PASSOU,
                      "saiu com %d" % tentativa["saida"])
    return anotar(SONDA_FALHA, ATENCAO,
                  "a tarefa não foi cumprida e ele saiu ZERO: quem chamar "
                  "confere o RESULTADO, nunca o código de saída")


def preparar_a_pasta(pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / ALVO_DA_SONDA).write_text(
        "A cor combinada e %s.\n" % SEGREDO_DA_SONDA, encoding="utf-8")
    alvo = pasta / ARQUIVO_QUE_NAO_PODE_NASCER
    if alvo.exists():
        alvo.unlink()


def veredito_do_placar(sondas: list) -> str:
    if any(s["resultado"] == FALHOU for s in sondas):
        return FALHOU
    if any(s["resultado"] == NAO_MEDIU for s in sondas):
        return NAO_MEDIU
    if any(s["resultado"] == ATENCAO for s in sondas):
        return ATENCAO
    return PASSOU


def sondar(nome: str, binario: str = "", gastar: bool = True) -> dict:
    receita = receita_do_motor(nome, binario)
    if not receita:
        return {"motor": nome, "veredito": NAO_MEDIU, "sondas": [],
                "razao": "motor sem receita: a bancada conhece %s"
                         % ", ".join(RECEITAS)}
    com_teto = [SONDA_ESTRUTURADO, SONDA_TRAVA, SONDA_TEMPO, SONDA_FALHA]
    with tempfile.TemporaryDirectory(prefix="sonda-motor-") as bruta:
        pasta = Path(bruta) / "bancada"
        preparar_a_pasta(pasta)
        sondas = [sondar_se_responde(receita, pasta)]
        parou = sondas[0]["resultado"] != PASSOU
        if parou or not gastar:
            razao = ("o executável não respondeu" if parou
                     else "sonda que consome crédito, não pedida")
            sondas += [anotar(s, NAO_MEDIU, razao) for s in com_teto]
            return {"motor": nome, "veredito": veredito_do_placar(sondas),
                    "sondas": sondas, "razao": "",
                    "garantia": receita["garantia"],
                    "cobranca": receita["cobranca"]}
        relogio = time.monotonic()
        estruturado, feito = sondar_se_devolve_estruturado(receita, pasta)
        gastou = time.monotonic() - relogio
        trava, tentativa = sondar_se_a_trava_segura(receita, pasta)
        sondas += [estruturado, trava,
                   sondar_se_responde_a_tempo(feito, gastou),
                   sondar_se_avisa_a_falha(tentativa)]
    return {"motor": nome, "veredito": veredito_do_placar(sondas),
            "sondas": sondas, "razao": "",
            "garantia": receita["garantia"],
            "cobranca": receita["cobranca"]}


def ler_o_cadastro(caminho: Path) -> dict:
    try:
        guardado = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return guardado if isinstance(guardado, dict) else {}


def linha_do_cadastro(placar: dict, receita: dict, hoje: str) -> dict:
    ressalvas = [s["razao"] for s in placar["sondas"]
                 if s["resultado"] == ATENCAO]
    return {
        "papeis": list(receita["papeis"]),
        "garantia_de_escrita": receita["garantia"],
        "cobranca": receita["cobranca"],
        "credito_antes_de_despachar": receita["fonte_do_limite"] or
        "não há fonte local: só se descobre despachando",
        "provado_em": hoje,
        "veredito": placar["veredito"],
        "ressalvas": ressalvas,
    }


def cadastrar(nome: str, caminho: Path, binario: str = "",
              hoje: str = "", gastar: bool = True) -> dict:
    receita = receita_do_motor(nome, binario)
    if not receita:
        return {}
    placar = sondar(nome, binario, gastar)
    guardado = ler_o_cadastro(caminho)
    motores = guardado.get(CHAVE_DOS_MOTORES)
    if not isinstance(motores, dict):
        motores = {}
    anterior = motores.get(nome) if isinstance(motores.get(nome), dict) else {}
    motores[nome] = linha_do_cadastro(placar, receita,
                                      hoje or hoje_por_extenso())
    if isinstance(anterior.get(CHAVE_DO_MODELO_POR_PAPEL), dict):
        motores[nome][CHAVE_DO_MODELO_POR_PAPEL] = anterior[
            CHAVE_DO_MODELO_POR_PAPEL]
    guardado[CHAVE_DOS_MOTORES] = motores
    caminho.write_text(json.dumps(guardado, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    return placar


def hoje_por_extenso() -> str:
    return datetime.date.today().isoformat()


SESSOES_LIDAS_ATRAS_DO_LIMITE = 20


def sessoes_da_mais_nova(pasta: Path) -> list:
    achados = sorted(pasta.glob(MOLDE_DO_ROLLOUT), reverse=True)
    return achados[:SESSOES_LIDAS_ATRAS_DO_LIMITE]


def limite_gravado_na_sessao(arquivo: Path) -> dict:
    limite = None
    for linha in arquivo.read_text(encoding="utf-8",
                                   errors="replace").splitlines():
        if not linha.strip().startswith("{"):
            continue
        try:
            corpo = json.loads(linha).get("payload") or {}
        except (ValueError, AttributeError):
            continue
        if not isinstance(corpo, dict):
            continue
        if corpo.get("type") == "token_count" and corpo.get("rate_limits"):
            limite = corpo["rate_limits"]
    if isinstance(limite, dict) and isinstance(limite.get("primary"), dict):
        return limite["primary"]
    return {}


def credito_do_motor(receita: dict, raiz_das_sessoes: Path = None) -> dict:
    sem_saber = {"usado_por_cento": None, "reseta_em": None,
                 "razao": "não há fonte local de saldo neste motor: o limite "
                          "só aparece quando ele responde"}
    if not receita or not receita.get("fonte_do_limite"):
        return sem_saber
    pasta = raiz_das_sessoes or Path(receita["fonte_do_limite"]).expanduser()
    arquivos = sessoes_da_mais_nova(pasta)
    if not arquivos:
        return {"usado_por_cento": None, "reseta_em": None,
                "razao": "nenhuma sessão gravada ainda em %s" % pasta}
    for arquivo in arquivos:
        try:
            primeiro = limite_gravado_na_sessao(arquivo)
        except OSError as falha:
            return {"usado_por_cento": None, "reseta_em": None,
                    "razao": "a sessão não foi lida (%s)"
                             % type(falha).__name__}
        if primeiro:
            return {"usado_por_cento": primeiro.get("used_percent"),
                    "reseta_em": primeiro.get("resets_at"),
                    "razao": "lido de %s, sem gastar chamada" % arquivo.name}
    return {"usado_por_cento": None, "reseta_em": None,
            "razao": "nenhuma das %d sessões mais novas registrou limite"
                     % len(arquivos)}


TETO_DO_DESPACHO = 3600
ARGUMENTOS_QUE_ABREM_A_ESCRITA = ("dangerous", "danger-full-access",
                                  "workspace-write", "bypass",
                                  "approve-for-me", "add-dir",
                                  "accept-edits", "smart")
RECUSA_DE_FERRAMENTA = "rejected a tool call"
CAMINHO_QUE_O_ATALHO_EXECUTARIA = (
    "o arquivo do pedido cairia em {}, e o atalho do interpretador de "
    "comandos executaria o que esse caminho tem de especial. Aponte a "
    "pasta temporária para um caminho sem & nem aspas, ou o executável de "
    "verdade do motor com --binario")
EVENTO_DE_ITEM_PRONTO = "item.completed"
EVENTO_DE_TURNO_PRONTO = "turn.completed"
EVENTO_DE_TURNO_FALHADO = "turn.failed"
EVENTO_DE_ERRO = "error"
ITEM_QUE_E_FALA = "agent_message"


def argumento_que_abre_a_escrita(argumentos: list) -> str:
    for argumento in argumentos:
        for marca in ARGUMENTOS_QUE_ABREM_A_ESCRITA:
            if marca in argumento.lower():
                return argumento
    return ""


def sem_acento(texto: str) -> str:
    return "".join(letra for letra in unicodedata.normalize("NFKD", texto)
                   if not unicodedata.combining(letra)).casefold()


def motores_do_papel(pedido: str) -> tuple:
    if pedido in RECEITAS:
        return [pedido], "", ""
    donos = [nome for nome, receita in RECEITAS.items()
             if pedido in receita["papeis"]]
    if not donos:
        papeis = sorted({papel for receita in RECEITAS.values()
                         for papel in receita["papeis"]})
        parecidos = [papel for papel in papeis
                     if sem_acento(papel) == sem_acento(pedido)]
        sugestao = " — quis dizer %r?" % parecidos[0] if parecidos else ":"
        return [], pedido, ("nenhum motor declara o papel %r%s os papéis "
                            "declarados são %s; os motores, %s"
                            % (pedido, sugestao, ", ".join(papeis),
                               ", ".join(RECEITAS)))
    donos.sort(key=lambda nome: ORDEM_DA_COBRANCA.index(
        RECEITAS[nome]["cobranca"]))
    return donos, pedido, ""


def modelo_do_cadastro(cadastro, nome: str, papel: str) -> str:
    if not papel or not isinstance(cadastro, dict):
        return ""
    motores = cadastro.get(CHAVE_DOS_MOTORES)
    linha = motores.get(nome) if isinstance(motores, dict) else None
    por_papel = (linha.get(CHAVE_DO_MODELO_POR_PAPEL)
                 if isinstance(linha, dict) else None)
    modelo = por_papel.get(papel) if isinstance(por_papel, dict) else None
    return modelo if isinstance(modelo, str) else ""


def caminho_do_estado_da_sessao(sessao: str = None) -> Path:
    if sessao is None:
        sessao = os.environ.get(VARIAVEL_DA_SESSAO, "")
    if not MOLDE_DE_NOME.match(sessao or ""):
        return None
    return (Path(tempfile.gettempdir()) / PASTA_DO_ESTADO_DA_SESSAO
            / (sessao + ".json"))


def marcar_esgotado(caminho, estado: dict, nome: str, razao: str) -> str:
    estado[nome] = {"marca": ESGOTADO,
                    "desde": datetime.datetime.now().isoformat(
                        timespec="seconds"),
                    "razao": razao[:300]}
    if caminho is None:
        return ("a marca vale só para este despacho: sem %s não há sessão "
                "onde guardá-la" % VARIAVEL_DA_SESSAO)
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(json.dumps(estado, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    except OSError as falha:
        return "a marca NÃO foi gravada (%s)" % type(falha).__name__
    return ""


def marca_da_sessao(estado: dict, nome: str) -> dict:
    marca = estado.get(nome)
    return marca if isinstance(marca, dict) else {}


def leitura_dos_eventos(texto: str) -> dict:
    lido = {"falas": [], "consumo": None, "turno_fechou": False,
            "turno_falhou": False, "linhas_partidas": 0, "erros": []}
    for linha in texto.split("\n"):
        if not linha.strip().startswith("{"):
            continue
        try:
            evento = json.loads(linha)
        except ValueError:
            lido["linhas_partidas"] += 1
            continue
        if not isinstance(evento, dict):
            continue
        item = evento.get("item")
        if (evento.get("type") == EVENTO_DE_ITEM_PRONTO
                and isinstance(item, dict)
                and item.get("type") == ITEM_QUE_E_FALA
                and isinstance(item.get("text"), str) and item["text"]):
            lido["falas"].append(item["text"])
        if evento.get("type") == EVENTO_DE_TURNO_PRONTO:
            lido["turno_fechou"] = True
            lido["consumo"] = evento.get("usage") or lido["consumo"]
        if evento.get("type") == EVENTO_DE_ERRO:
            aninhado = evento.get("error")
            mensagem = evento.get("message") or (
                aninhado.get("message") if isinstance(aninhado, dict)
                else None)
            if isinstance(mensagem, str):
                lido["erros"].append(mensagem)
        if evento.get("type") == EVENTO_DE_TURNO_FALHADO:
            lido["turno_falhou"] = True
            erro = evento.get("error")
            if isinstance(erro, dict) and isinstance(erro.get("message"), str):
                lido["erros"].append(erro["message"])
    return lido


def parecer_incompleto(lido: dict, saida) -> str:
    if lido["turno_falhou"]:
        return "o motor declarou o turno FALHADO%s" % (
            ": " + " | ".join(lido["erros"])[-400:] if lido["erros"] else "")
    if lido["linhas_partidas"]:
        return ("%d linha(s) do fluxo de eventos chegaram partidas: pode "
                "haver fala perdida" % lido["linhas_partidas"])
    if not lido["turno_fechou"]:
        return "o fluxo acabou sem o motor fechar o turno"
    if saida != 0:
        return "o motor saiu com código %s" % saida
    return ""


def passa_pelo_interpretador(binario: str) -> bool:
    achado = shutil.which(binario) or binario
    return achado.lower().endswith(ATALHOS_DO_WINDOWS)


def vai_como_argumento_pelo_interpretador_de_comandos(receita: dict) -> bool:
    if receita["prompt_por_stdin"] or "{prompt}" not in receita["despacho"]:
        return False
    return passa_pelo_interpretador(receita["binario"])


def argumentos_do_despacho(receita: dict, modelo: str) -> list:
    argumentos = list(receita["despacho"])
    if not modelo:
        return argumentos
    par = [receita["bandeira_do_modelo"], modelo]
    if receita["prompt_por_stdin"] and argumentos[-1:] == ["-"]:
        return argumentos[:-1] + par + ["-"]
    return argumentos + par


def recusa_antes_de_chamar(nome: str, veredito: str, razao: str) -> dict:
    return {"motor": nome, "veredito": veredito, "falas": [], "consumo": None,
            "razao": razao, "recusado": True, "sinais": ""}


def despachar_no_motor(nome: str, prompt: str, pasta: Path, binario: str,
                       teto: int, modelo: str) -> dict:
    receita = receita_do_motor(nome, binario)
    if modelo and not MOLDE_DE_NOME.match(modelo):
        return recusa_antes_de_chamar(
            nome, NAO_MEDIU, "o modelo %r não tem forma de nome de modelo: "
            "letras, dígitos, ponto, hífen e sublinhado. Nada foi despachado"
            % modelo)
    if modelo and not receita["bandeira_do_modelo"]:
        return recusa_antes_de_chamar(
            nome, NAO_MEDIU, "o motor %s não tem bandeira de modelo provada: "
            "despache sem %s, e vale o padrão dele"
            % (nome, BANDEIRA_DO_MODELO))
    argumentos = argumentos_do_despacho(receita, modelo)
    proibido = argumento_que_abre_a_escrita(argumentos)
    if proibido:
        return recusa_antes_de_chamar(
            nome, FALHOU, "a receita de despacho carrega %r, que abre a "
            "escrita: despacho é somente leitura" % proibido)
    if vai_como_argumento_pelo_interpretador_de_comandos(receita):
        return recusa_antes_de_chamar(
            nome, NAO_MEDIU, "este motor recebe o pedido como ARGUMENTO e o "
            "executável dele é um atalho do interpretador de comandos, que "
            "executaria o que o texto do pedido mandasse. Aponte o executável "
            "de verdade com %s" % BANDEIRA_DO_BINARIO)
    feito = rodar(receita, argumentos, pasta, prompt, teto)
    incompleto = ""
    erros = []
    if receita["despacho_em_eventos"]:
        lido = leitura_dos_eventos(feito["texto"])
        falas, consumo, erros = lido["falas"], lido["consumo"], lido["erros"]
        if feito["respondeu"]:
            incompleto = parecer_incompleto(lido, feito["saida"])
    else:
        falas = [feito["texto"]] if feito["texto"].strip() else []
        consumo = None
        if feito["respondeu"] and feito["saida"] != 0:
            incompleto = "o motor saiu com código %s" % feito["saida"]
        elif feito["respondeu"] and RECUSA_DE_FERRAMENTA in feito["erro"]:
            incompleto = ("o motor recusou uma ferramenta no meio do "
                          "trabalho (%r no canal de erro) e respondeu sem "
                          "ela" % RECUSA_DE_FERRAMENTA)
    parecer = {"motor": nome, "veredito": NAO_MEDIU, "falas": falas,
               "consumo": consumo, "razao": "",
               "sinais": "\n".join(erros + [feito["erro"]])}
    if not feito["respondeu"]:
        parecer["razao"] = feito["razao"]
    elif falas and incompleto:
        parecer["razao"] = ("parecer INCOMPLETO: %s. As falas que chegaram "
                            "estão acima, e não são o parecer inteiro"
                            % incompleto)
    elif not falas:
        parecer["razao"] = ("o motor saiu com código %s e nenhuma fala: o "
                            "código de saída dele não acusa tarefa não "
                            "cumprida. O que ele disse no canal de erro: %s"
                            % (feito["saida"],
                               " ".join(erros + [feito["erro"].strip()])
                               [-400:]))
    else:
        parecer["veredito"] = PASSOU
    return parecer


def escolha_dita(papel: str, nomes: list, nome: str, modelo: str,
                 trilha: list) -> str:
    if papel:
        quem = "papel %r: motor %s, na ordem %s" % (papel, nome,
                                                   ", ".join(nomes))
    else:
        quem = "motor %s, pelo nome" % nome
    return "; ".join([quem, "modelo %s" % (modelo or "o padrão do motor")]
                     + trilha)


def despachar(pedido: str, prompt: str, pasta: Path, binario: str = "",
              teto: int = TETO_DO_DESPACHO, modelo: str = "",
              cadastro: dict = None, caminho_do_estado: Path = None) -> dict:
    nomes, papel, razao = motores_do_papel(pedido)
    if not nomes:
        return {"motor": pedido, "veredito": NAO_MEDIU, "razao": razao,
                "falas": [], "consumo": None, "escolha": ""}
    estado = ler_o_cadastro(caminho_do_estado) if caminho_do_estado else {}
    trilha = []
    for nome in nomes:
        marca = marca_da_sessao(estado, nome)
        if marca.get("marca") == ESGOTADO:
            trilha.append("%s %s nesta sessão desde %s, e não se tenta de "
                          "novo (%s)" % (nome, ESGOTADO.upper(),
                                         marca.get("desde", "?"),
                                         str(marca.get("razao", ""))[:160]))
            continue
        executavel = binario or RECEITAS[nome]["binario"]
        if not (shutil.which(executavel) or Path(executavel).is_file()):
            trilha.append("%s não está instalado nesta máquina (%s não se "
                          "acha)" % (nome, executavel))
            continue
        escolhido = modelo or modelo_do_cadastro(cadastro, nome, papel)
        parecer = despachar_no_motor(nome, prompt, pasta, binario, teto,
                                     escolhido)
        parecer["escolha"] = escolha_dita(papel, nomes, nome, escolhido,
                                          trilha)
        if (parecer["veredito"] == PASSOU or parecer["falas"]
                or parecer.get("recusado")):
            return parecer
        if SINAIS_DE_FALTA_DE_CREDITO.search(parecer["sinais"]):
            gravada = marcar_esgotado(caminho_do_estado, estado, nome,
                                      parecer["razao"])
            trilha.append("%s respondeu falta de crédito e ficou %s%s: %s"
                          % (nome, ESGOTADO.upper(),
                             " (%s)" % gravada if gravada else "",
                             parecer["razao"]))
        else:
            trilha.append("%s %s neste despacho, por falha que não se sabe "
                          "interpretar: %s" % (nome, SUSPEITO.upper(),
                                               parecer["razao"]))
    return {"motor": pedido, "veredito": NAO_MEDIU, "falas": [],
            "consumo": None, "escolha": "",
            "razao": "; ".join(trilha) + ". " + AVISO_DE_SEGUIR_SOZINHO}


def imprimir_o_despacho(parecer: dict) -> int:
    for canal in (sys.stdout, sys.stderr):
        canal.reconfigure(encoding="utf-8", errors="replace")
    for lugar, fala in enumerate(parecer["falas"], start=1):
        print("=== fala %d de %d ===" % (lugar, len(parecer["falas"])))
        print(fala)
    letras = sum(len(fala) for fala in parecer["falas"])
    print("=== despacho ao motor %s: %s — %d fala(s), %d letra(s) ==="
          % (parecer["motor"], parecer["veredito"], len(parecer["falas"]),
             letras), file=sys.stderr)
    if parecer.get("escolha"):
        print("  escolha: %s" % parecer["escolha"], file=sys.stderr)
    if parecer["consumo"]:
        print("  consumo declarado pelo motor: %s"
              % json.dumps(parecer["consumo"]), file=sys.stderr)
    if parecer["razao"]:
        print("  " + parecer["razao"], file=sys.stderr)
    if parecer["veredito"] == PASSOU:
        return 0
    return 1 if parecer["veredito"] == FALHOU else 2


def imprimir_o_placar(placar: dict) -> int:
    print("BANCADA DO MOTOR %s" % placar["motor"].upper())
    if placar["razao"]:
        print("  " + placar["razao"])
    for sonda in placar["sondas"]:
        print("  [%-10s] %-32s %s"
              % (sonda["resultado"], sonda["sonda"], sonda["razao"]))
    if placar.get("garantia"):
        print("  a trava de escrita é garantida por: %s" % placar["garantia"])
        print("  a cobrança deste motor é: %s" % placar["cobranca"])
    print("Veredito: %s" % placar["veredito"])
    if placar["veredito"] == FALHOU:
        print("  motor reprovado não entra no cadastro: quem o chamar não "
              "sabe o que ele garante.")
        return 1
    if placar["veredito"] == NAO_MEDIU:
        print("  motor NÃO MEDIDO não é motor aprovado: ele entra no cadastro "
              "marcado assim, e a sessão avisa ao usá-lo.")
        return 2
    if placar["veredito"] == ATENCAO:
        print("  motor aprovado COM RESSALVA: o cadastro leva a ressalva "
              "junto, porque quem o chamar precisa dela.")
        return 0
    return 0


CORPO_DO_DUBLE = '''import json
import sys
from pathlib import Path

argumentos = sys.argv[1:]
if "--version" in argumentos:
    print("duble de motor 1.0")
    raise SystemExit(0)
pedido = " ".join(argumentos)
if not sys.stdin.isatty():
    pedido += " " + sys.stdin.read()
if "--prompt-file" in argumentos:
    pedido += " " + Path(argumentos[argumentos.index("--prompt-file") + 1]
                         ).read_text(encoding="utf-8")
pasta = Path(".")
for indice, argumento in enumerate(argumentos):
    if argumento == "-C" and indice + 1 < len(argumentos):
        pasta = Path(argumentos[indice + 1])
if "--json" in argumentos:
    sys.stdout.reconfigure(encoding="utf-8")

    def evento(tipo, item=None):
        print(json.dumps({"type": tipo, "item": item} if item
                         else {"type": tipo}, ensure_ascii=False),
              flush=True)
    evento("thread.started")
    with open("chamadas.txt", "a", encoding="utf-8") as registro:
        registro.write("codex\\n")
    if "sem credito" in pedido:
        print(json.dumps({"type": "error",
                          "message": "You've hit your usage limit."}),
              flush=True)
        print("ERROR: usage limit reached", file=sys.stderr)
        raise SystemExit(1)
    if "mostre os argumentos" in pedido:
        evento("item.completed", {"type": "agent_message",
                                  "text": "ARGV " + " ".join(argumentos)})
        evento("turn.completed")
        raise SystemExit(0)
    if "fique mudo" in pedido:
        evento("turn.completed")
        raise SystemExit(0)
    evento("item.completed", {"type": "agent_message",
                              "text": "PARECER INTEIRO \\u2713: "
                                      + "achado " * 40})
    evento("item.completed", {"type": "command_execution",
                              "command": "echo oi"})
    if "trunque" in pedido:
        print('{"type": "item.completed", "item": {"type": "agent_mess',
              flush=True)
        evento("turn.completed")
        raise SystemExit(0)
    if "falhe o turno" in pedido:
        evento("turn.failed")
        evento("turn.completed")
        raise SystemExit(0)
    if "falhe por capacidade" in pedido:
        print(json.dumps({"type": "turn.failed", "error": {
            "message": "Selected model is at capacity"}}), flush=True)
        raise SystemExit(1)
    if "nao feche o turno" in pedido:
        raise SystemExit(0)
    if "saia com erro" in pedido:
        evento("turn.completed")
        raise SystemExit(7)
    if "forma estranha" in pedido:
        evento("item.completed", "inesperado")
        print("[1, 2]", flush=True)
    if "separador" in pedido:
        evento("item.completed", {"type": "agent_message",
                                  "text": "antes\\u2028DEPOIS DO SEPARADOR"})
    if "gere filho" in pedido:
        import subprocess
        import time
        subprocess.Popen([sys.executable, "-c",
                          "import time, pathlib; time.sleep(6); "
                          "pathlib.Path('filho-sobreviveu.txt')"
                          ".write_text('vivo')"], cwd=str(pasta))
        time.sleep(40)
    if "demore" in pedido:
        import time
        time.sleep(30)
    evento("item.completed", {"type": "agent_message",
                              "text": "os arquivos continuam intactos"})
    evento("turn.completed")
    raise SystemExit(0)
if "mostre os argumentos" in pedido:
    print("ARGV " + " ".join(argumentos))
    raise SystemExit(0)
if "recuse a ferramenta" in pedido:
    print("parecer parcial, sem a ferramenta")
    print("warning: rejected a tool call", file=sys.stderr)
    raise SystemExit(0)
if "tentativa.txt" in pedido:
    if ESCREVE:
        (pasta / "tentativa.txt").write_text("oi", encoding="utf-8")
        print("criei o arquivo")
        raise SystemExit(0)
    print("warning: recusei a escrita", file=sys.stderr)
    raise SystemExit(1 if AVISA else 0)
alvo = pasta / "alvo.txt"
cor = None
if alvo.exists():
    cor = alvo.read_text(encoding="utf-8").strip().rstrip(".").split()[-1]
print(json.dumps({"cor": cor}))
raise SystemExit(0)
'''


def motor_duble(pasta: Path, escreve: bool, avisa_a_falha: bool) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / "duble.py"
    arquivo.write_text(
        CORPO_DO_DUBLE
        .replace("ESCREVE", "True" if escreve else "False")
        .replace("AVISA", "True" if avisa_a_falha else "False"),
        encoding="utf-8")
    return arquivo


def testar() -> int:
    falhas = []
    with tempfile.TemporaryDirectory(prefix="bancada-motores-") as bruta:
        pasta = Path(bruta)

        honesto = motor_duble(pasta / "honesto", escreve=False,
                              avisa_a_falha=True)
        placar = sondar("codex", binario=str(honesto))
        if placar["veredito"] != PASSOU:
            falhas.append("motor honesto devia passar nas cinco sondas e não "
                          "passou: %s" % placar["veredito"])
        if len(placar["sondas"]) != 5:
            falhas.append("o placar devia trazer as cinco sondas, veio com %d"
                          % len(placar["sondas"]))

        vazado = motor_duble(pasta / "vazado", escreve=True,
                             avisa_a_falha=True)
        placar = sondar("codex", binario=str(vazado))
        if placar["veredito"] != FALHOU:
            falhas.append("motor que escreve com a trava ligada devia ser "
                          "REPROVADO e não foi")
        trava = [s for s in placar["sondas"] if s["sonda"] == SONDA_TRAVA]
        if not trava or trava[0]["resultado"] != FALHOU:
            falhas.append("a sonda da trava devia acusar o motor que escreveu")

        mudo = motor_duble(pasta / "mudo", escreve=False,
                           avisa_a_falha=False)
        placar = sondar("codex", binario=str(mudo))
        aviso = [s for s in placar["sondas"] if s["sonda"] == SONDA_FALHA]
        if not aviso or aviso[0]["resultado"] != ATENCAO:
            falhas.append("motor que sai zero com a tarefa não cumprida devia "
                          "sair com RESSALVA, não reprovado: é o que os dois "
                          "motores reais fazem")
        if placar["veredito"] != ATENCAO:
            falhas.append("ressalva não reprova motor: o veredito devia ser "
                          "atenção e veio %s" % placar["veredito"])

        ausente = sondar("codex", binario=str(pasta / "nao-existe"))
        if ausente["veredito"] != NAO_MEDIU:
            falhas.append("binário ausente não é motor reprovado, é motor NÃO "
                          "MEDIDO: veio %s" % ausente["veredito"])

        barato = sondar("codex", binario=str(honesto), gastar=False)
        gastam = [s for s in barato["sondas"]
                  if s["resultado"] != NAO_MEDIU
                  and s["sonda"] != SONDA_RESPONDE]
        if gastam:
            falhas.append("sem gastar, só a sonda que não custa crédito roda; "
                          "rodaram também: %s" % [s["sonda"] for s in gastam])

        if sondar("motor-que-ninguem-cadastrou")["veredito"] != NAO_MEDIU:
            falhas.append("motor sem receita devia sair como não medido")

        sem_bandeira_de_pasta = sondar("devin", binario=str(honesto))
        if sem_bandeira_de_pasta["veredito"] not in (PASSOU, ATENCAO):
            falhas.append("motor SEM bandeira de pasta tem de receber a pasta "
                          "como diretório do subprocesso, senão lê o lugar "
                          "errado: veio %s"
                          % sem_bandeira_de_pasta["veredito"])

        atalho = pasta / "atalho.cmd"
        atalho.write_text("@echo oi\n", encoding="utf-8")
        montado = comando_do_binario(str(atalho))
        if len(montado) < 2 or str(atalho) not in montado:
            falhas.append("atalho .cmd do Windows não roda sozinho pelo "
                          "subprocesso: tem de ir pelo interpretador de "
                          "comandos, e veio %s" % montado)

        cadastro = pasta / "executor.json"
        cadastro.write_text(json.dumps({"issues": {"repositorio": "algum"}}),
                            encoding="utf-8")
        cadastrar("codex", cadastro, binario=str(honesto), hoje="2026-09-19")
        guardado = json.loads(cadastro.read_text(encoding="utf-8"))
        if "issues" not in guardado:
            falhas.append("cadastrar motor apagou o resto do arquivo local: "
                          "ele carrega issue, branch e vizinho")
        linha = (guardado.get(CHAVE_DOS_MOTORES) or {}).get("codex", {})
        for campo in ("papeis", "garantia_de_escrita", "cobranca",
                      "provado_em", "veredito"):
            if campo not in linha:
                falhas.append("o cadastro tem de declarar %s e não declarou"
                              % campo)
        if linha.get("provado_em") != "2026-09-19":
            falhas.append("a data da prova é o que diz se o cadastro envelheceu")

        cadastrar("codex", cadastro, binario=str(pasta / "nao-existe"),
                  hoje="2026-09-19")
        ausente = json.loads(cadastro.read_text(encoding="utf-8"))
        if ausente[CHAVE_DOS_MOTORES]["codex"]["veredito"] != NAO_MEDIU:
            falhas.append("motor que não respondeu entra no cadastro como NÃO "
                          "MEDIDO, nunca como aprovado")

        sessoes = pasta / "sessoes" / "2026" / "09" / "19"
        sessoes.mkdir(parents=True)
        (sessoes / "rollout-teste.jsonl").write_text(json.dumps(
            {"type": "event_msg", "payload": {"type": "token_count",
             "rate_limits": {"primary": {"used_percent": 7.5,
                                         "resets_at": 1790427809}}}}),
            encoding="utf-8")
        limite = credito_do_motor(receita_do_motor("codex"), sessoes.parents[2])
        if limite.get("usado_por_cento") != 7.5:
            falhas.append("o limite do motor de assinatura se lê do arquivo de "
                          "sessão, sem gastar chamada: veio %s" % limite)
        (sessoes / "rollout-zz-sem-limite.jsonl").write_text(json.dumps(
            {"type": "event_msg", "payload": {"type": "task_started"}}),
            encoding="utf-8")
        depois_da_falha = credito_do_motor(receita_do_motor("codex"),
                                           sessoes.parents[2])
        if depois_da_falha.get("usado_por_cento") != 7.5:
            falhas.append("sessão mais nova SEM limite, como a de um despacho "
                          "recusado antes da chamada, não apaga o limite lido "
                          "na anterior: veio %s" % depois_da_falha)

        sem_fonte = credito_do_motor(receita_do_motor("devin"), pasta)
        if sem_fonte.get("usado_por_cento") is not None:
            falhas.append("motor sem fonte local de saldo tem de dizer que não "
                          "sabe, em vez de inventar número")

        parecer = despachar("codex", "revise o commit", pasta,
                            binario=str(honesto))
        if len(parecer["falas"]) != 2:
            falhas.append("o despacho devolve TODAS as falas do motor, e o "
                          "dublê falou duas vezes: vieram %d"
                          % len(parecer["falas"]))
        if not any("PARECER INTEIRO" in fala for fala in parecer["falas"]):
            falhas.append("a fala do MEIO é o parecer; quem guarda só a "
                          "última entrega a resposta ao gancho de parada")
        if parecer["veredito"] != PASSOU:
            falhas.append("despacho com fala devia passar: veio %s"
                          % parecer["veredito"])

        mudo_no_despacho = despachar("codex", "fique mudo", pasta,
                                     binario=str(honesto))
        if mudo_no_despacho["veredito"] != NAO_MEDIU:
            falhas.append("motor que sai zero sem fala nenhuma é despacho NÃO "
                          "MEDIDO, nunca parecer vazio: veio %s"
                          % mudo_no_despacho["veredito"])

        sem_motor = despachar("codex", "revise", pasta,
                              binario=str(pasta / "nao-existe"))
        if sem_motor["veredito"] != NAO_MEDIU or sem_motor["falas"]:
            falhas.append("binário ausente no despacho é NÃO MEDIDO com a "
                          "razão dita: veio %s" % sem_motor["veredito"])

        lento = despachar("codex", "demore", pasta, binario=str(honesto),
                          teto=3)
        if lento["veredito"] != NAO_MEDIU:
            falhas.append("despacho que estoura o teto é NÃO MEDIDO: veio %s"
                          % lento["veredito"])
        if not any("PARECER INTEIRO" in fala for fala in lento["falas"]):
            falhas.append("o que o motor disse ANTES de estourar o teto fica "
                          "no resultado, em vez de sumir com o processo")

        truncado = despachar("codex", "trunque", pasta, binario=str(honesto))
        if truncado["veredito"] != NAO_MEDIU or not truncado["falas"]:
            falhas.append("fluxo que acaba em linha partida, sem o turno "
                          "fechar, é parecer INCOMPLETO: não medido, com as "
                          "falas que chegaram. Veio %s com %d fala(s)"
                          % (truncado["veredito"], len(truncado["falas"])))

        turno_caido = despachar("codex", "falhe o turno", pasta,
                                binario=str(honesto))
        if turno_caido["veredito"] != NAO_MEDIU or not turno_caido["falas"]:
            falhas.append("turno que o motor declara falhado não passa só "
                          "porque houve uma fala antes: veio %s"
                          % turno_caido["veredito"])

        try:
            estranho = despachar("codex", "forma estranha", pasta,
                                 binario=str(honesto))
            if estranho["veredito"] != PASSOU or len(estranho["falas"]) != 2:
                falhas.append("evento de forma inesperada se ignora, e as "
                              "falas em volta dele chegam: veio %s com %d"
                              % (estranho["veredito"], len(estranho["falas"])))
        except AttributeError as falha:
            falhas.append("evento de forma inesperada derrubou o despacho "
                          "inteiro, com as falas já colhidas: %s" % falha)

        separado = despachar("codex", "separador", pasta,
                             binario=str(honesto))
        if not any("DEPOIS DO SEPARADOR" in fala
                   for fala in separado["falas"]):
            falhas.append("separador de linha Unicode DENTRO de uma fala não "
                          "parte o evento: a fala tem de chegar inteira")

        for modo in ("nao feche o turno", "saia com erro"):
            incompleto = despachar("codex", modo, pasta, binario=str(honesto))
            if incompleto["veredito"] != NAO_MEDIU or not incompleto["falas"]:
                falhas.append("parecer incompleto por %r tem de sair não "
                              "medido com as falas que chegaram: veio %s"
                              % (modo, incompleto["veredito"]))

        partida = time.monotonic()
        com_filho = despachar("codex", "gere filho", pasta,
                              binario=str(honesto), teto=2)
        gasto = time.monotonic() - partida
        if com_filho["veredito"] != NAO_MEDIU or gasto > 20:
            falhas.append("teto estourado encerra a ÁRVORE de processos: "
                          "filho que segura os canais não pode prender o "
                          "retorno. Veio %s em %.1f s"
                          % (com_filho["veredito"], gasto))
        time.sleep(max(0.0, 9 - (time.monotonic() - partida)))
        if (pasta / "filho-sobreviveu.txt").exists():
            falhas.append("o filho do motor SOBREVIVEU ao teto e escreveu "
                          "depois dele: retorno rápido não prova árvore "
                          "encerrada")

        encerrador_de_verdade = globals()["encerrar_a_arvore"]
        globals()["encerrar_a_arvore"] = lambda processo: (
            processo.kill(), False)[1]
        try:
            sem_encerrador = despachar("codex", "demore", pasta,
                                       binario=str(honesto), teto=2)
        finally:
            globals()["encerrar_a_arvore"] = encerrador_de_verdade
        if "NÃO foi encerrada" not in sem_encerrador["razao"]:
            falhas.append("quando a árvore de processos não se encerra, a "
                          "razão do despacho DIZ isso: processo solto lendo "
                          "a árvore é o que a regra de despacho proíbe")

        class ProcessoQueQuebraNaConversa:
            pid = 0
            returncode = None
            morto = False

            def communicate(self, *_, **__):
                raise OSError("canal quebrado")

            def kill(self):
                self.morto = True

        abrir_de_verdade = subprocess.Popen
        quebrado = ProcessoQueQuebraNaConversa()
        subprocess.Popen = lambda *_, **__: quebrado
        globals()["encerrar_a_arvore"] = lambda processo: (
            processo.kill(), True)[1]
        try:
            conversa = rodar(receita_do_motor("codex", str(honesto)),
                             ["--version"], pasta, "")
        except OSError:
            conversa = None
        finally:
            subprocess.Popen = abrir_de_verdade
            globals()["encerrar_a_arvore"] = encerrador_de_verdade
        if conversa is None or conversa["respondeu"] or not quebrado.morto:
            falhas.append("falha de E/S DURANTE a conversa com o motor vira "
                          "não respondeu, com o processo encerrado: a "
                          "exceção não pode escapar da sonda")

        que_sai_com_erro = pasta / "parcial.py"
        que_sai_com_erro.write_text(
            "print('resposta parcial')\nraise SystemExit(7)\n",
            encoding="utf-8")
        sem_eventos = despachar("devin", "saia com erro sem eventos", pasta,
                                binario=str(que_sai_com_erro))
        if sem_eventos["veredito"] != NAO_MEDIU or not sem_eventos["falas"]:
            falhas.append("motor sem fluxo de eventos que sai com erro não "
                          "passa só porque escreveu alguma coisa: veio %s"
                          % sem_eventos["veredito"])

        quem_despacha = subprocess.Popen(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, %r); import motores; "
             "print(motores.despachar('devin', 'revise', motores.Path(%r), "
             "binario=%r, teto=20)['veredito'])"
             % (str(Path(__file__).resolve().parent), str(pasta),
                str(honesto))],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
            errors="replace")
        com_a_entrada_aberta = quem_despacha.stdout.read().strip()
        quem_despacha.stdin.close()
        quem_despacha.wait()
        if com_a_entrada_aberta != PASSOU:
            falhas.append("motor que não recebe o pedido pela entrada não "
                          "herda a entrada de quem despacha, que pode nunca "
                          "fechar: veio %r" % com_a_entrada_aberta)

        recusou = despachar("devin", "recuse a ferramenta", pasta,
                            binario=str(honesto))
        if (recusou["veredito"] == PASSOU or not recusou["falas"]
                or "INCOMPLETO" not in recusou["razao"]):
            falhas.append("motor que recusa uma ferramenta (%r no canal de "
                          "erro) e sai zero dá parecer INCOMPLETO: veio %s"
                          % (RECUSA_DE_FERRAMENTA, recusou["veredito"]))

        sem_capacidade = despachar("codex", "falhe por capacidade", pasta,
                                   binario=str(honesto))
        if "Selected model is at capacity" not in sem_capacidade["razao"]:
            falhas.append("turno falhado diz o motivo que o motor deu, para "
                          "separar congestionamento de defeito: veio %r"
                          % sem_capacidade["razao"])

        binarios = {nome: RECEITAS[nome]["binario"] for nome in RECEITAS}
        RECEITAS["codex"]["binario"] = str(pasta / "codex-que-nao-existe")
        RECEITAS["devin"]["binario"] = str(honesto)
        try:
            sem_codex = despachar("crítico", "revise", pasta)
        finally:
            for nome, binario_de_verdade in binarios.items():
                RECEITAS[nome]["binario"] = binario_de_verdade
        if (sem_codex["motor"] != "devin" or sem_codex["veredito"] != PASSOU
                or "não está instalado" not in sem_codex.get("escolha", "")):
            falhas.append("sem o codex na máquina, o crítico vai ao devin e a "
                          "escolha diz por quê: veio %s, %s, %r"
                          % (sem_codex["motor"], sem_codex["veredito"],
                             sem_codex.get("escolha", "")))

        repositorio = pasta / "repositorio-do-diff"
        repositorio.mkdir()
        (repositorio / "a.txt").write_text("LINHA_DO_DIFF\n", encoding="utf-8")
        for comando in (["init", "-q"], ["add", "a.txt"],
                        ["-c", "user.name=t", "-c", "user.email=t@t", "-c",
                         "commit.gpgsign=false", "commit", "-qm", "um"]):
            subprocess.run(["git", "-C", str(repositorio)] + comando,
                           capture_output=True, timeout=60)
        com_diff, sem_falha = pedido_com_o_diff("revise", repositorio, "HEAD")
        if (sem_falha or not com_diff.startswith("revise")
                or "+LINHA_DO_DIFF" not in com_diff):
            falhas.append("--commit junta ao pedido o diff tirado com git "
                          "show: veio %r" % (sem_falha or com_diff[-200:]))
        if not pedido_com_o_diff("revise", repositorio, "--output=x")[1]:
            falhas.append("commit que começa com hífen viraria opção do git: "
                          "é recusado antes de rodar")
        for intervalo in ("HEAD..HEAD", "^HEAD"):
            if not pedido_com_o_diff("revise", repositorio, intervalo)[1]:
                falhas.append("--commit aceita um commit, não um "
                              "intervalo: %s volta vazio e não pode "
                              "passar" % intervalo)
        assinatura = ["-c", "user.name=t", "-c", "user.email=t@t", "-c",
                      "commit.gpgsign=false"]
        subprocess.run(["git", "-C", str(repositorio), "checkout", "-q", "-b",
                        "lado"], capture_output=True, timeout=60)
        (repositorio / "b.txt").write_text("LINHA_DA_MESCLA\n",
                                           encoding="utf-8")
        for comando in (["add", "b.txt"],
                        assinatura + ["commit", "-qm", "lado"],
                        ["checkout", "-q", "-"]):
            subprocess.run(["git", "-C", str(repositorio)] + comando,
                           capture_output=True, timeout=60)
        (repositorio / "c.txt").write_text("outra\n", encoding="utf-8")
        for comando in (["add", "c.txt"],
                        assinatura + ["commit", "-qm", "principal"],
                        assinatura + ["merge", "-q", "--no-ff", "-m",
                                      "mescla", "lado"]):
            subprocess.run(["git", "-C", str(repositorio)] + comando,
                           capture_output=True, timeout=60)
        da_mescla, falha_da_mescla = pedido_com_o_diff(
            "revise", repositorio, "HEAD")
        if falha_da_mescla or "+LINHA_DA_MESCLA" not in da_mescla:
            falhas.append("--commit de uma mescla traz o diff contra o "
                          "primeiro pai, não só o cabeçalho: veio %r"
                          % (falha_da_mescla or da_mescla[-200:]))
        if not pedido_com_o_diff("revise", repositorio, "abc1234")[1]:
            falhas.append("commit que não existe não vira pedido sem diff, "
                          "calado")

        receita_de_verdade = RECEITAS["codex"]["despacho"]
        RECEITAS["codex"]["despacho"] = receita_de_verdade + [
            "--dangerously-bypass-approvals-and-sandbox"]
        try:
            aberto = despachar("codex", "revise", pasta, binario=str(honesto))
        finally:
            RECEITAS["codex"]["despacho"] = receita_de_verdade
        if aberto["veredito"] != FALHOU or aberto["falas"]:
            falhas.append("o DESPACHO recusa receita que abre a escrita sem "
                          "chamar o motor: provar só o ajudante deixa a "
                          "chamada sair do despacho sem ninguém notar")

        atalho_de_motor = pasta / "motor.cmd"
        atalho_de_motor.write_text("@echo %*\n", encoding="utf-8")
        injecao = '" & echo MARCA_INJETADA & rem "'

        def marca_rodou(parecer: dict) -> bool:
            return any(linha.strip() == "MARCA_INJETADA"
                       for fala in parecer["falas"]
                       for linha in fala.splitlines())

        por_arquivo = despachar("devin", injecao, pasta,
                                binario=str(atalho_de_motor))
        if not por_arquivo["falas"] or marca_rodou(por_arquivo) or any(
                "MARCA_INJETADA" in fala for fala in por_arquivo["falas"]):
            falhas.append("o pedido ao devin vai por arquivo e não chega à "
                          "linha de comando do atalho: chegou %s"
                          % por_arquivo["falas"])
        temporaria_de_verdade = tempfile.tempdir
        com_e_comercial = pasta / "tmp&echo MARCA_DO_CAMINHO&rem"
        com_e_comercial.mkdir()
        tempfile.tempdir = str(com_e_comercial)
        try:
            pelo_caminho = despachar("devin", "revise", pasta,
                                     binario=str(atalho_de_motor))
        finally:
            tempfile.tempdir = temporaria_de_verdade
        if any(linha.strip() == "MARCA_DO_CAMINHO"
               for fala in pelo_caminho["falas"]
               for linha in fala.splitlines()) \
                or pelo_caminho["veredito"] == PASSOU:
            falhas.append("pasta temporária com & no caminho não passa "
                          "pelo interpretador de comandos: o despacho "
                          "recusa antes de chamar o atalho")
        receita_por_arquivo = RECEITAS["devin"]["despacho"]
        RECEITAS["devin"]["despacho"] = RECEITAS["devin"]["sem_cabeca"]
        try:
            injetado = despachar("devin", injecao, pasta,
                                 binario=str(atalho_de_motor))
        finally:
            RECEITAS["devin"]["despacho"] = receita_por_arquivo
        if injetado["veredito"] == PASSOU or marca_rodou(injetado):
            falhas.append("pedido que vai como ARGUMENTO por um atalho do "
                          "interpretador de comandos executa o que o texto "
                          "mandar: esse par não se despacha")

        pedido_em_arquivo = pasta / "pedido.txt"
        pedido_em_arquivo.write_text("revise", encoding="utf-8")
        ambiente_sem_utf8 = dict(os.environ, PYTHONUTF8="0",
                                 PYTHONIOENCODING="cp1252")
        pela_linha = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()),
             BANDEIRA_DE_DESPACHO, "codex", BANDEIRA_DO_PROMPT,
             str(pedido_em_arquivo), BANDEIRA_DA_PASTA, str(pasta),
             BANDEIRA_DO_BINARIO, str(honesto)],
            capture_output=True, env=ambiente_sem_utf8, timeout=120)
        if (pela_linha.returncode != 0
                or "✓" not in pela_linha.stdout.decode("utf-8",
                                                            "replace")):
            falhas.append("parecer com símbolo fora da página de código da "
                          "máquina tem de sair inteiro, em UTF-8: saiu %s"
                          % pela_linha.returncode)

        for proibida in ("--dangerously-bypass-approvals-and-sandbox",
                         "danger-full-access", "workspace-write",
                         "--approve-for-me", "--add-dir", "dangerous",
                         "accept-edits", "smart"):
            if not argumento_que_abre_a_escrita(["exec", "-s", proibida]):
                falhas.append("receita de despacho com %s tem de ser recusada"
                              % proibida)
        for nome in RECEITAS:
            if argumento_que_abre_a_escrita(RECEITAS[nome]["despacho"]):
                falhas.append("a receita de despacho do %s é somente leitura "
                              "e não pode ser recusada pela própria guarda"
                              % nome)

        if motores_do_papel("crítico")[0] != ["codex", "devin"]:
            falhas.append("o crítico se ordena pela cobrança: o codex antes, "
                          "e o devin quando o codex não serve")
        if motores_do_papel("pesquisa")[0] != ["devin"]:
            falhas.append("papel que um motor só declara resolve nesse motor")
        if motores_do_papel("codex")[:2] != (["codex"], ""):
            falhas.append("nome de motor vale como está, e sem papel")
        if motores_do_papel("tarefa somente leitura")[0] != ["codex", "devin"]:
            falhas.append("papel de dois motores se ordena pela cobrança: "
                          "assinatura antes de pré-pago, porque estourar a "
                          "assinatura custa espera e o pré-pago custa dinheiro")
        sem_acento = motores_do_papel("critico")
        if sem_acento[0] or "quis dizer 'crítico'" not in sem_acento[2]:
            falhas.append("papel digitado sem acento não resolve calado, mas "
                          "a recusa sugere o papel declarado que casa: disse "
                          "%r" % sem_acento[2])
        com_caixa = motores_do_papel("Critico")[2]
        if "quis dizer 'crítico'" not in com_caixa:
            falhas.append("papel digitado com maiúscula e sem acento também "
                          "recebe a sugestão: disse %r" % com_caixa)
        desconhecido = motores_do_papel("revisor")[2]
        if "pesquisa" not in desconhecido or "quis dizer" in desconhecido:
            falhas.append("papel que ninguém declara lista os PAPÉIS "
                          "conhecidos, sem sugerir nenhum: disse %r"
                          % desconhecido)
        dois = despachar("tarefa somente leitura", "revise", pasta,
                         binario=str(honesto))
        if (dois["motor"] != "codex" or "codex" not in dois.get("escolha", "")
                or "devin" not in dois.get("escolha", "")):
            falhas.append("papel que dois motores declaram não se escolhe "
                          "calado: a escolha diz o motor e nomeia os dois")

        chamadas = pasta / "chamadas.txt"

        def contar_chamadas() -> int:
            try:
                return len(chamadas.read_text(encoding="utf-8").splitlines())
            except OSError:
                return 0

        def argumentos_que_chegaram(parecer: dict) -> list:
            for fala in parecer["falas"]:
                if fala.startswith("ARGV "):
                    return fala.split()[1:]
            return []

        def modelo_que_chegou(parecer: dict) -> str:
            chegaram = argumentos_que_chegaram(parecer)
            if "-m" not in chegaram[:-1]:
                return ""
            return chegaram[chegaram.index("-m") + 1]

        padrao = despachar("codex", "mostre os argumentos", pasta,
                           binario=str(honesto))
        if not argumentos_que_chegaram(padrao) or modelo_que_chegou(padrao):
            falhas.append("sem modelo declarado vale o padrão do motor: o "
                          "despacho não passa -m. Chegou %s"
                          % argumentos_que_chegaram(padrao))
        pedido_com_modelo = despachar("codex", "mostre os argumentos", pasta,
                                      binario=str(honesto), modelo="modelo-9")
        if modelo_que_chegou(pedido_com_modelo) != "modelo-9":
            falhas.append("--modelo chega ao codex exec como -m: chegou %s"
                          % argumentos_que_chegaram(pedido_com_modelo))
        cadastro_com_modelo = {CHAVE_DOS_MOTORES: {"codex": {
            CHAVE_DO_MODELO_POR_PAPEL: {"crítico": "modelo-do-papel"}}}}
        do_papel = despachar("crítico", "mostre os argumentos", pasta,
                             binario=str(honesto),
                             cadastro=cadastro_com_modelo)
        if modelo_que_chegou(do_papel) != "modelo-do-papel":
            falhas.append("o cadastro declara o modelo POR PAPEL, e o despacho "
                          "pelo papel o usa: chegou %s"
                          % argumentos_que_chegaram(do_papel))
        por_cima = despachar("crítico", "mostre os argumentos", pasta,
                             binario=str(honesto),
                             cadastro=cadastro_com_modelo, modelo="modelo-9")
        if modelo_que_chegou(por_cima) != "modelo-9":
            falhas.append("o --modelo de quem chama vence o do cadastro")
        pelo_nome = despachar("codex", "mostre os argumentos", pasta,
                              binario=str(honesto),
                              cadastro=cadastro_com_modelo)
        if modelo_que_chegou(pelo_nome):
            falhas.append("despacho pelo NOME não tem papel, e por isso não "
                          "herda o modelo de papel nenhum")
        antes = contar_chamadas()
        torto = despachar("codex", "mostre os argumentos", pasta,
                          binario=str(honesto), modelo="x & calc")
        if torto["veredito"] != NAO_MEDIU or contar_chamadas() != antes:
            falhas.append("modelo sem forma de nome é recusado ANTES de chamar "
                          "o motor: o atalho do Windows passaria o texto pelo "
                          "interpretador de comandos")
        no_devin = argumentos_que_chegaram(despachar(
            "devin", "mostre os argumentos", pasta, binario=str(honesto),
            modelo="modelo-9"))
        if ("--model" not in no_devin[:-1]
                or no_devin[no_devin.index("--model") + 1] != "modelo-9"):
            falhas.append("--modelo chega ao devin como --model: chegou %s"
                          % no_devin)
        if "--prompt-file" not in no_devin or "mostre" in no_devin:
            falhas.append("o pedido vai ao devin por --prompt-file, nunca "
                          "como argumento: chegou %s" % no_devin)
        sem_modelo = RECEITAS["devin"]["bandeira_do_modelo"]
        RECEITAS["devin"]["bandeira_do_modelo"] = ""
        try:
            sem_bandeira = despachar("devin", "revise", pasta,
                                     binario=str(honesto), modelo="modelo-9")
        finally:
            RECEITAS["devin"]["bandeira_do_modelo"] = sem_modelo
        if sem_bandeira["veredito"] != NAO_MEDIU or sem_bandeira["falas"]:
            falhas.append("motor sem bandeira de modelo provada recusa "
                          "--modelo, em vez de ignorá-lo calado")
        pedido_de_argumentos = pasta / "pedido-argumentos.txt"
        pedido_de_argumentos.write_text("mostre os argumentos",
                                        encoding="utf-8")
        sem_sessao = {nome: valor for nome, valor in os.environ.items()
                      if nome != VARIAVEL_DA_SESSAO}
        pela_linha_com_modelo = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()),
             BANDEIRA_DE_DESPACHO, "codex", BANDEIRA_DO_PROMPT,
             str(pedido_de_argumentos), BANDEIRA_DA_PASTA, str(pasta),
             BANDEIRA_DO_BINARIO, str(honesto), BANDEIRA_DO_MODELO,
             "modelo-9"],
            capture_output=True, env=sem_sessao, timeout=120)
        if "-m modelo-9" not in pela_linha_com_modelo.stdout.decode(
                "utf-8", "replace"):
            falhas.append("a linha de comando aceita %s e o repassa: saiu %s"
                          % (BANDEIRA_DO_MODELO,
                             pela_linha_com_modelo.returncode))

        declarado = json.loads(cadastro.read_text(encoding="utf-8"))
        declarado[CHAVE_DOS_MOTORES]["codex"][CHAVE_DO_MODELO_POR_PAPEL] = {
            "crítico": "modelo-do-papel"}
        cadastro.write_text(json.dumps(declarado, ensure_ascii=False),
                            encoding="utf-8")
        cadastrar("codex", cadastro, binario=str(honesto), hoje="2026-09-21",
                  gastar=False)
        relido = json.loads(cadastro.read_text(encoding="utf-8"))
        if relido[CHAVE_DOS_MOTORES]["codex"].get(
                CHAVE_DO_MODELO_POR_PAPEL) != {"crítico": "modelo-do-papel"}:
            falhas.append("sondar de novo não apaga o modelo que o dono "
                          "declarou por papel")

        estado = pasta / "estado-da-sessao.json"
        esgotou = despachar("codex", "sem credito", pasta,
                            binario=str(honesto), caminho_do_estado=estado)
        marcado = ler_o_cadastro(estado).get("codex") or {}
        if esgotou["veredito"] != NAO_MEDIU or marcado.get("marca") != ESGOTADO:
            falhas.append("motor que responde falta de crédito fica ESGOTADO "
                          "no estado da sessão: veio %s e %s"
                          % (esgotou["veredito"], marcado))
        antes = contar_chamadas()
        de_novo = despachar("codex", "revise", pasta, binario=str(honesto),
                            caminho_do_estado=estado)
        if (contar_chamadas() != antes or de_novo["veredito"] != NAO_MEDIU
                or ESGOTADO.upper() not in de_novo["razao"]):
            falhas.append("motor esgotado não é tentado de novo na mesma "
                          "sessão, nem pelo nome")
        caiu = despachar("tarefa somente leitura", "revise", pasta,
                         binario=str(honesto), caminho_do_estado=estado)
        if caiu["motor"] != "devin" or caiu["veredito"] != PASSOU:
            falhas.append("com o motor do papel esgotado, o despacho cai para "
                          "outro motor do mesmo papel: veio %s, %s"
                          % (caiu["motor"], caiu["veredito"]))
        critico_no_devin = despachar("crítico", "revise", pasta,
                                     binario=str(honesto),
                                     caminho_do_estado=estado)
        if (critico_no_devin["motor"] != "devin"
                or critico_no_devin["veredito"] != PASSOU):
            falhas.append("com o codex esgotado, o crítico cai para o devin: "
                          "veio %s, %s" % (critico_no_devin["motor"],
                                           critico_no_devin["veredito"]))
        marcar_esgotado(estado, ler_o_cadastro(estado), "devin", "bancada")
        antes = contar_chamadas()
        sozinho = despachar("crítico", "revise", pasta, binario=str(honesto),
                            caminho_do_estado=estado)
        if (sozinho["veredito"] != NAO_MEDIU
                or AVISO_DE_SEGUIR_SOZINHO not in sozinho["razao"]
                or contar_chamadas() != antes):
            falhas.append("sem motor livre para o papel, o despacho não chama "
                          "ninguém e manda avisar o dono e seguir sozinho")
        limpo = pasta / "estado-limpo.json"
        no_meio = despachar("tarefa somente leitura", "sem credito", pasta,
                            binario=str(honesto), caminho_do_estado=limpo)
        if (no_meio["motor"] != "devin" or no_meio["veredito"] != PASSOU
                or (ler_o_cadastro(limpo).get("codex") or {}).get("marca")
                != ESGOTADO):
            falhas.append("motor que esgota NO MEIO do despacho pelo papel "
                          "fica marcado, e o mesmo despacho cai para o próximo")
        desconfiado = pasta / "estado-suspeito.json"
        suspeito = despachar("tarefa somente leitura", "fique mudo", pasta,
                             binario=str(honesto),
                             caminho_do_estado=desconfiado)
        if suspeito["motor"] != "devin" or suspeito["veredito"] != PASSOU:
            falhas.append("falha que não se sabe interpretar deixa o motor "
                          "suspeito e cai para o próximo: veio %s, %s"
                          % (suspeito["motor"], suspeito["veredito"]))
        if ler_o_cadastro(desconfiado).get("codex"):
            falhas.append("suspeito vale só para o despacho: falha passageira "
                          "não desliga o motor pelo resto da sessão")

        if (caminho_do_estado_da_sessao("") is not None
                or caminho_do_estado_da_sessao("../fora") is not None):
            falhas.append("sem identificador de sessão, ou com um que não é "
                          "nome de arquivo, o estado não se grava")
        if caminho_do_estado_da_sessao("abc-123") is None:
            falhas.append("com a sessão, o estado mora na pasta temporária")
        erro_com_a_mensagem_dentro = json.dumps({
            "type": "error", "status": 400,
            "error": {"type": "invalid_request_error",
                      "message": "The 'x' model is not supported."}})
        if leitura_dos_eventos(erro_com_a_mensagem_dentro)["erros"] != [
                "The 'x' model is not supported."]:
            falhas.append("o erro do Codex traz a mensagem DENTRO de error, "
                          "e a leitura tem de achá-la")
        estado_torto = pasta / "estado-torto.json"
        estado_torto.write_text(json.dumps({"codex": "isto não é objeto"}),
                                encoding="utf-8")
        if despachar("codex", "revise", pasta, binario=str(honesto),
                     caminho_do_estado=estado_torto)["veredito"] != PASSOU:
            falhas.append("estado da sessão torto não derruba nem bloqueia o "
                          "despacho")

    total = 91
    if falhas:
        for linha in falhas:
            print("  " + linha)
        print("FALHOU: %d de %d casos — bancada de motores auxiliares"
              % (len(falhas), total))
        return 1
    print("OK: %d casos — bancada de motores auxiliares" % total)
    return 0


def raiz_do_projeto() -> Path:
    declarada = os.environ.get("CLAUDE_PROJECT_DIR")
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[2]


def imprimir_o_credito(nome: str, limite: dict) -> int:
    print("CRÉDITO DO MOTOR %s" % nome.upper())
    if limite["usado_por_cento"] is None:
        print("  desconhecido — %s" % limite["razao"])
        return 2
    print("  %.1f%% da janela usados (%s)"
          % (limite["usado_por_cento"], limite["razao"]))
    if limite["reseta_em"]:
        quando = datetime.datetime.fromtimestamp(limite["reseta_em"])
        print("  a janela reseta em %s" % quando.strftime("%d/%m/%Y %H:%M"))
    return 0


def imprimir_o_cadastro(caminho: Path) -> int:
    motores = ler_o_cadastro(caminho).get(CHAVE_DOS_MOTORES) or {}
    if not motores:
        print("Nenhum motor cadastrado em %s." % caminho)
        print("  cadastre com: --cadastrar <motor>")
        return 2
    print("MOTORES CADASTRADOS em %s" % caminho)
    for nome, linha in sorted(motores.items()):
        print("  %-8s %-10s papéis: %s" % (nome, linha.get("veredito", "?"),
                                           ", ".join(linha.get("papeis", []))))
        print("           escrita: %s | cobrança: %s | provado em %s"
              % (linha.get("garantia_de_escrita", "?"),
                 linha.get("cobranca", "?"), linha.get("provado_em", "?")))
        for ressalva in linha.get("ressalvas", []):
            print("           ressalva: %s" % ressalva)
        for papel, modelo in sorted((linha.get(CHAVE_DO_MODELO_POR_PAPEL)
                                     or {}).items()):
            print("           modelo do papel %s: %s" % (papel, modelo))
    estado = caminho_do_estado_da_sessao()
    for nome, marca in sorted(ler_o_cadastro(estado).items()
                              if estado else []):
        if isinstance(marca, dict) and marca.get("marca") == ESGOTADO:
            print("  nesta sessão: %s ESGOTADO desde %s — apague %s para "
                  "tentar de novo" % (nome, marca.get("desde", "?"), estado))
    return 0


def pedido_com_o_diff(prompt: str, repositorio: Path, commit: str) -> tuple:
    if not MOLDE_DE_COMMIT.match(commit):
        return prompt, ("o commit %r não tem forma de hash nem de nome de "
                        "ref: nada foi despachado" % commit)
    try:
        feito = subprocess.run(
            ["git", "-C", str(repositorio), "show", "--no-color",
             "--diff-merges=first-parent", commit, "--"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=TETO_DO_GIT_SHOW)
    except (OSError, subprocess.SubprocessError) as falha:
        return prompt, "o git show de %s não rodou (%s: %s)" % (
            commit, type(falha).__name__, falha)
    if feito.returncode != 0:
        return prompt, ("o git show de %s saiu %d em %s, o repositório de "
                        "onde se despacha, e não o do %s: %s" % (
                            commit, feito.returncode, repositorio,
                            BANDEIRA_DA_PASTA, feito.stderr.strip()[-300:]))
    if MARCA_DE_DIFF not in feito.stdout:
        return prompt, ("o git show de %s não trouxe diff nenhum: commit "
                        "vazio não tem o que revisar" % commit)
    return prompt + CABECALHO_DO_DIFF.format(commit=commit) + feito.stdout, ""


def despachar_pela_linha_de_comando(posto) -> int:
    if not posto.prompt:
        print("despacho sem pedido: diga o arquivo com %s"
              % BANDEIRA_DO_PROMPT, file=sys.stderr)
        return 2
    try:
        prompt = Path(posto.prompt).read_text(encoding="utf-8")
    except OSError as falha:
        print("o arquivo do pedido não foi lido (%s: %s)"
              % (type(falha).__name__, falha), file=sys.stderr)
        return 2
    pasta = Path(posto.cwd) if posto.cwd else raiz_do_projeto()
    if posto.commit:
        prompt, falha = pedido_com_o_diff(prompt, Path.cwd(), posto.commit)
        if falha:
            print(falha, file=sys.stderr)
            return 2
    return imprimir_o_despacho(
        despachar(posto.despachar, prompt, pasta, posto.binario, posto.teto,
                  modelo=posto.modelo,
                  cadastro=ler_o_cadastro(raiz_do_projeto()
                                          / ARQUIVO_DO_CADASTRO),
                  caminho_do_estado=caminho_do_estado_da_sessao()))


def main() -> int:
    leitor = argparse.ArgumentParser(description=DESCRICAO_DA_CLI)
    leitor.add_argument(BANDEIRA_DO_MOTOR, metavar="MOTOR",
                        help="sonda o motor e imprime o placar: "
                             + ", ".join(RECEITAS))
    leitor.add_argument(BANDEIRA_DE_CADASTRO, metavar="MOTOR",
                        help="sonda e grava o resultado no cadastro local")
    leitor.add_argument(BANDEIRA_DO_CREDITO, metavar="MOTOR",
                        help="diz quanto do limite já foi usado, sem gastar "
                             "chamada")
    leitor.add_argument(BANDEIRA_DE_LISTA, action="store_true",
                        help="mostra os motores já cadastrados")
    leitor.add_argument(BANDEIRA_DO_BINARIO, default="",
                        help="caminho do executável, quando não estiver no PATH")
    leitor.add_argument(BANDEIRA_SEM_GASTAR, action="store_true",
                        help="roda só a sonda que não consome crédito")
    leitor.add_argument(BANDEIRA_DE_TESTE, action="store_true",
                        help="roda o autoteste com motores dublês")
    leitor.add_argument(BANDEIRA_DE_DESPACHO, metavar="MOTOR_OU_PAPEL",
                        help="despacha o pedido em somente leitura e devolve "
                             "TODAS as falas do motor, não só a última")
    leitor.add_argument(BANDEIRA_DO_PROMPT, metavar="ARQUIVO",
                        help="arquivo com o pedido do despacho")
    leitor.add_argument(BANDEIRA_DA_PASTA, metavar="PASTA", default="",
                        help="a pasta que o motor lê; sem ela, a raiz")
    leitor.add_argument(BANDEIRA_DO_TETO, type=int, default=TETO_DO_DESPACHO,
                        help="segundos até desistir do despacho")
    leitor.add_argument(BANDEIRA_DO_MODELO, metavar="MODELO", default="",
                        help="o modelo do despacho; sem ele vale o que o "
                             "cadastro declara para o papel, e sem os dois, "
                             "o padrão do motor")
    leitor.add_argument(BANDEIRA_DO_COMMIT, metavar="HASH", default="",
                        help="junta ao pedido o diff do commit, tirado com "
                             "git show no repositório de onde se despacha")
    posto = leitor.parse_args()
    if posto.despachar:
        return despachar_pela_linha_de_comando(posto)
    cadastro = raiz_do_projeto() / ARQUIVO_DO_CADASTRO
    if posto.listar:
        return imprimir_o_cadastro(cadastro)
    if posto.credito:
        return imprimir_o_credito(posto.credito,
                                  credito_do_motor(
                                      receita_do_motor(posto.credito)))
    if posto.cadastrar:
        placar = cadastrar(posto.cadastrar, cadastro, posto.binario,
                           gastar=not posto.sem_gastar)
        if not placar:
            print("motor sem receita: a bancada conhece %s"
                  % ", ".join(RECEITAS))
            return 2
        saida = imprimir_o_placar(placar)
        print("  cadastrado em %s — o arquivo é local e não entra em git."
              % cadastro)
        return saida
    if not posto.sondar:
        leitor.print_help()
        return 1
    return imprimir_o_placar(sondar(posto.sondar, posto.binario,
                                    not posto.sem_gastar))


if __name__ == "__main__":
    for canal in (sys.stdin, sys.stdout, sys.stderr):
        if not getattr(canal, "closed", True) and hasattr(canal, "reconfigure"):
            canal.reconfigure(encoding="utf-8", errors="replace")
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
