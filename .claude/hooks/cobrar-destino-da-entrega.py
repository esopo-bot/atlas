import re
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ARQUIVO_CONFIGURACAO = "nucleo/configuracao.json"
CHAVE_POR_INCORPORACAO = "branches_por_incorporacao"
ARQUIVO_EXECUTOR = "nucleo/executor.json"
CHAVE_DAS_BRANCHES = "branches"
CHAVE_DA_INTEGRACAO = "integracao"

INSTRUMENTO_DA_ENTREGA = ".agents/camada/camada.py"
BANDEIRA_DA_ENTREGA = "--entrega"
COMANDO_DA_SUJEIRA = ["git", "status", "--porcelain"]
COMANDO_DO_QUE_A_PRINCIPAL_NAO_TEM = [
    "git", "log", "--oneline", "--no-decorate", "{}..{}"]
COMANDO_DO_QUE_ESTA_SESSAO_ACRESCENTOU = [
    "git", "log", "--oneline", "--no-decorate", "--since=@{2}", "{0}..{1}"]
COMANDO_DO_PEDIDO_ABERTO = [
    "gh", "pr", "list", "--base", "{0}", "--head", "{1}", "--state", "open",
    "--json", "number", "--jq", "length"]
COMANDO_DO_PEDIDO_MESCLADO = [
    "gh", "pr", "list", "--base", "{0}", "--head", "{1}", "--state", "merged",
    "--limit", "1", "--json", "mergeCommit", "--jq",
    ".[0].mergeCommit.oid // empty"]
COMANDO_DO_COMMIT_QUE_CONTEM = [
    "git", "merge-base", "--is-ancestor", "{0}", "{1}"]
EXTENSOES_QUE_A_CAMADA_NAO_JULGA = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".pdf",
    ".zip", ".tar", ".gz", ".xz", ".7z", ".mp3", ".mp4", ".wav", ".mov",
    ".sqlite", ".db", ".dump", ".bin", ".so", ".dll", ".exe", ".woff",
    ".woff2", ".ttf", ".otf")
COBRA_SUJEIRA_QUE_A_CAMADA_NAO_JULGA = (
    "Na árvore há {} arquivo(s) que a camada não sabe julgar, e eles NÃO "
    "impedem a entrega — ficam nomeados aqui porque nada sem destino passa "
    "calado:\n{}\n"
    "Commitá-los seria adotar o que talvez não seja seu; apagá-los é "
    "destrutivo, e destrutivo é do dono. Diga a ele, e siga.")
COMANDO_DA_BRANCH_DA_ARVORE = ["git", "branch", "--show-current"]
COMANDO_DO_COMMIT_DA_ARVORE = ["git", "rev-parse", "HEAD"]
COMANDO_DA_BRANCH_NO_DURAVEL = [
    "git", "ls-remote", "--heads", "origin", "{}"]
COMANDO_DE_BUSCA_NO_REMOTO = ["git", "fetch", "--quiet", "origin", "{}", "{}"]
CHAVE_DO_TRANSCRITO = "transcript_path"
CHAVE_DA_SESSAO = "session_id"
PASTA_DOS_TRANSCRITOS = ".claude/projects"
EXTENSAO_DO_TRANSCRITO = ".jsonl"
JANELA_DE_VIDA_EM_SEGUNDOS = 600
QUANTAS_SESSOES_NOMEADAS = 3
FERRAMENTAS_QUE_ESCREVEM = ("Write", "Edit", "NotebookEdit")
FERRAMENTAS_DE_SHELL = ("Bash", "PowerShell")
CAMPO_DO_COMANDO = "command"
VERBOS_QUE_MEXEM_EM_ARQUIVO = (
    "git mv", "git rm", "git checkout", "git restore", "sed -i", "mv ", "cp ",
    "rm ", "tee ", "touch ", "mkdir ", "rmdir ", ">>", ">")
CAMINHO_NO_COMANDO = re.compile(r"[\w./-]*[\w-]+\.[A-Za-z0-9]{1,6}")
CHAVE_DO_INSTANTE = "timestamp"
LINHAS_LIDAS_DO_TRANSCRITO = 200
MARCA_DE_UTC = "Z"
FUSO_UTC = "+00:00"
ESPELHO_NO_REMOTO = "origin/{}"
TEMPO_DO_GIT = 15
TEMPO_DA_REDE = 25

MARCA_DE_ETAPA_NO_AMBIENTE = "ENCADEADOR_ETAPA"
VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

EVENTO_DE_PARADA = "Stop"
DECISAO_DE_BLOQUEAR = "block"
BANDEIRA_DE_TESTE = "--testar"
NAO_MEDIDO = None
SILENCIO = 0
FALHA_ABERTA = 0
COBRANCA_ENTREGUE = 0
TETO_DE_LINHAS = 5

COBRA_SUJEIRA_HERDADA = (
    "Na árvore há {} arquivo(s) sujo(s) desde ANTES desta sessão abrir — "
    "sujeira herdada, de outra sessão ou do dono, e ela NÃO trava esta "
    "parada:\n{}\n"
    "Não commite nem apague o que não é seu: diga ao dono, e siga.")
COBRA_ARVORE_SUJA = (
    "A árvore está suja — {} arquivo(s) fora de commit nenhum:\n{}\n"
    "Trabalho que não entra em commit some com a pasta que o guardou, e "
    "ninguém fica sabendo que existiu. Ou vai, ou é descartado: commite na "
    "branch de trabalho, ou apague dizendo a razão em uma linha."
)
COBRA_SOBRA_DA_BRANCH = (
    "Há commit fora da branch de entrega. O que `{} {}` respondeu:\n{}\n"
    "Commit em branch que ninguém vai incorporar não existe para o resto do "
    "mundo, e some no dia em que a branch for podada."
)
COBRA_INTEGRACAO_SEM_PEDIDO = (
    "A integração {!r} está {} commit(s) à frente de {!r} e NÃO há pedido de "
    "incorporação aberto entre elas:\n{}\n"
    "Destino inclui o passo seguinte, não só a branch: se a promoção é por "
    "pedido de incorporação, ele fica ABERTO, não planejado para depois. "
    "Trabalho parado antes disso não chegou a lugar nenhum, só parece pronto."
)
COBRA_FORA_DO_REPOSITORIO_DURAVEL = (
    "A branch de trabalho {0!r} não chegou ao repositório durável: "
    "`git ls-remote --heads origin {0}` não devolveu o commit desta árvore.\n"
    "O que foi commitado existe só nesta árvore descartável e some com ela — "
    "empurre a branch antes de fechar a etapa."
)
COBRA_DURAVEL_NAO_MEDIDO = (
    "Não deu para medir se a branch de trabalho {!r} chegou ao repositório "
    "durável — o `git ls-remote` não respondeu. Sem a medição isto é 'não "
    "medido', nunca 'chegou': confira à mão antes de fechar a etapa."
)
COBRA_PEDIDO_NAO_MEDIDO = (
    "A integração {!r} está {} commit(s) à frente de {!r}, e não deu para "
    "medir se existe pedido de incorporação aberto entre elas — o `gh` não "
    "respondeu. Sem a medição isto é 'não medido', nunca 'não existe': "
    "confira à mão antes de encerrar."
)
RELATA_HERDADO = (
    "Para saber, não para resolver: a integração {!r} já estava {} commit(s) "
    "à frente de {!r} quando esta sessão abriu, e não há pedido de "
    "incorporação aberto entre elas:\n{}\n"
    "Nada disso é obra desta sessão, então ela não é cobrada — quem encerra "
    "uma dívida é quem a fez. Fica dito porque estado sem destino não passa "
    "calado."
)
ABERTURA_DA_COBRANCA = (
    "A regra 16 cobra destino antes de encerrar, e alguma coisa ficou sem:"
)
FECHAMENTO_DA_COBRANCA = (
    "Resolva o que está acima, ou diga em uma linha por que fica assim — "
    "esta cobrança sai uma vez por parada.\n"
    "Grave o aprendizado antes de encerrar — regra 4, a memória mora no "
    "disco, e cobrança que a próxima sessão repete não ensinou nada. A "
    "linha, em `conhecimento/`:\n"
    "    nada fica sem destino: ou vai para a branch de entrega com o "
    "passo seguinte aberto, ou é descartado com a razão dita em uma "
    "linha."
)

FALHA_DE_CASO = "  {}"
FALHA_COBROU_DE_MENOS = "COBRA [{}]: calou"
FALHA_COBROU_DE_MAIS = "CALA [{}]: cobrou — {}"
FALHA_COMPORTAMENTO = "COMPORTAMENTO [{}]"
RESUMO_FALHOU = "FALHOU: {} de {} casos"
RESUMO_OK = "OK: {} casos — {} cobram, {} calam, {} de comportamento"


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def branches_por_incorporacao(raiz: Path) -> set:
    try:
        dado = json.loads(
            (raiz / ARQUIVO_CONFIGURACAO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    declarado = (dado.get(CHAVE_POR_INCORPORACAO)
                 if isinstance(dado, dict) else None)
    if not isinstance(declarado, list):
        return set()
    return {str(nome).strip().lower() for nome in declarado if str(nome).strip()}


def branch_de_integracao(raiz: Path) -> str:
    try:
        dado = json.loads((raiz / ARQUIVO_EXECUTOR).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    branches = dado.get(CHAVE_DAS_BRANCHES) if isinstance(dado, dict) else None
    if not isinstance(branches, dict):
        return ""
    declarada = branches.get(CHAVE_DA_INTEGRACAO)
    return str(declarada).strip() if declarada else ""


def responde(comando: list, raiz: Path, tempo: int):
    try:
        pronto = subprocess.run(comando, cwd=raiz, capture_output=True,
                                text=True, timeout=tempo)
    except (OSError, subprocess.SubprocessError):
        return NAO_MEDIDO
    return pronto.returncode, (pronto.stdout or "").strip()


def a_camada_julga(linha: str) -> bool:
    caminho = linha[3:].strip().strip('"')
    return not caminho.lower().endswith(EXTENSOES_QUE_A_CAMADA_NAO_JULGA)


def linhas_da_arvore_suja(raiz: Path) -> list:
    return [l for l in _toda_a_sujeira(raiz) if a_camada_julga(l)]


def linhas_que_a_camada_nao_julga(raiz: Path) -> list:
    return [l for l in _toda_a_sujeira(raiz) if not a_camada_julga(l)]


def _toda_a_sujeira(raiz: Path) -> list:
    resposta = responde(COMANDO_DA_SUJEIRA, raiz, TEMPO_DO_GIT)
    if resposta is NAO_MEDIDO or resposta[0] != 0:
        return []
    return [l for l in resposta[1].split("\n") if l.strip()]


def abertura_da_sessao(entrada: dict):
    caminho = entrada.get(CHAVE_DO_TRANSCRITO) if isinstance(entrada, dict) else None
    if not caminho:
        return None
    try:
        with open(caminho, encoding="utf-8") as transcrito:
            for _, linha in zip(range(LINHAS_LIDAS_DO_TRANSCRITO), transcrito):
                instante = _instante_da_linha(linha)
                if instante is not None:
                    return instante
    except OSError:
        return None
    return None


def _instante_da_linha(linha: str):
    try:
        dado = json.loads(linha)
    except ValueError:
        return None
    marcado = dado.get(CHAVE_DO_INSTANTE) if isinstance(dado, dict) else None
    if not isinstance(marcado, str):
        return None
    try:
        return datetime.fromisoformat(
            marcado.replace(MARCA_DE_UTC, FUSO_UTC)).timestamp()
    except ValueError:
        return None


def modificado_antes_da_abertura(raiz: Path, linha: str, abertura) -> bool:
    if abertura is None:
        return False
    caminho = raiz / linha[3:].strip().strip('"')
    try:
        return caminho.stat().st_mtime < abertura
    except OSError:
        return False


def sessoes_vivas_ao_lado(pasta: Path, minha: str, agora: float) -> list:
    if not pasta.is_dir():
        return []
    vivas = []
    for transcrito in pasta.glob(f"*{EXTENSAO_DO_TRANSCRITO}"):
        if transcrito.stem == minha:
            continue
        try:
            idade = agora - transcrito.stat().st_mtime
        except OSError:
            continue
        if 0 <= idade <= JANELA_DE_VIDA_EM_SEGUNDOS:
            vivas.append((idade, transcrito.stem))
    return sorted(vivas)[:QUANTAS_SESSOES_NOMEADAS]


def arquivos_que_esta_sessao_escreveu(caminho, raiz: Path) -> set:
    escritos = set()
    if not caminho:
        return escritos
    try:
        with open(caminho, encoding="utf-8") as transcrito:
            for linha in transcrito:
                try:
                    dado = json.loads(linha)
                except ValueError:
                    continue
                corpo = (dado.get("message") or {}).get("content")
                for bloco in corpo if isinstance(corpo, list) else []:
                    if not isinstance(bloco, dict):
                        continue
                    if bloco.get("name") in FERRAMENTAS_QUE_ESCREVEM:
                        alvo = (bloco.get("input") or {}).get("file_path")
                        if alvo:
                            escritos.add(str(alvo))
                    elif bloco.get("name") in FERRAMENTAS_DE_SHELL:
                        escritos |= caminhos_que_o_shell_mexeu(
                            (bloco.get("input") or {}).get(CAMPO_DO_COMANDO),
                            raiz)
    except OSError:
        return escritos
    return escritos


def caminhos_que_o_shell_mexeu(comando, raiz: Path) -> set:
    if not isinstance(comando, str) or not comando:
        return set()
    if not any(v in comando for v in VERBOS_QUE_MEXEM_EM_ARQUIVO):
        return set()
    achados = set()
    for pedaco in CAMINHO_NO_COMANDO.findall(comando):
        limpo = pedaco.strip("'\"")
        if not limpo or limpo.startswith("-"):
            continue
        achados.add(str((raiz / limpo).resolve()))
        achados.add(str(raiz / limpo))
    return achados


def _o_caminho_da_linha(raiz: Path, linha: str) -> str:
    return str(raiz / linha[3:].strip().strip('"'))


def sujeira_desta_sessao_e_herdada(raiz: Path, abertura, entrada=None,
                                   agora=None, lar=None) -> tuple:
    suja = linhas_da_arvore_suja(raiz)
    herdada = [l for l in suja
               if modificado_antes_da_abertura(raiz, l, abertura)]
    minha = [l for l in suja if l not in herdada]
    if entrada is None:
        return minha, herdada
    lar = Path.home() if lar is None else lar
    pasta = lar / PASTA_DOS_TRANSCRITOS / str(raiz).replace(os.sep, "-")
    agora = time.time() if agora is None else agora
    vizinha = sessoes_vivas_ao_lado(
        pasta, str(entrada.get(CHAVE_DA_SESSAO) or ""), agora)
    if not vizinha:
        return minha, herdada
    escritos = arquivos_que_esta_sessao_escreveu(
        entrada.get(CHAVE_DO_TRANSCRITO), raiz)
    if not escritos:
        return minha, herdada
    alheia = [l for l in minha if _o_caminho_da_linha(raiz, l) not in escritos]
    return [l for l in minha if l not in alheia], herdada + alheia


def pedido_mesclado_que_ja_contem(raiz: Path, principal: str,
                                  integracao: str, adiante: list) -> bool:
    montado = [parte.format(principal, integracao)
               for parte in COMANDO_DO_PEDIDO_MESCLADO]
    resposta = responde(montado, raiz, TEMPO_DA_REDE)
    if resposta is NAO_MEDIDO or resposta[0] != 0 or not resposta[1]:
        return False
    mescla = resposta[1].split()[0]
    for linha in adiante:
        commit = linha.split()[0] if linha.split() else ""
        if not commit:
            continue
        verificado = responde(
            [p.format(commit, mescla) for p in COMANDO_DO_COMMIT_QUE_CONTEM],
            raiz, TEMPO_DO_GIT)
        if verificado is NAO_MEDIDO or verificado[0] != 0:
            return False
    return True


def sobra_fora_da_branch_de_entrega(raiz: Path) -> str:
    if not (raiz / INSTRUMENTO_DA_ENTREGA).is_file():
        return ""
    resposta = responde(
        [sys.executable, INSTRUMENTO_DA_ENTREGA, BANDEIRA_DA_ENTREGA],
        raiz, TEMPO_DO_GIT)
    if resposta is NAO_MEDIDO or resposta[0] == 0:
        return ""
    return resposta[1]


def commits_da_integracao_fora_da_principal(raiz: Path, principal: str,
                                            integracao: str):
    if not principal or not integracao:
        return NAO_MEDIDO
    responde([parte.format(principal, integracao)
              for parte in COMANDO_DE_BUSCA_NO_REMOTO], raiz, TEMPO_DA_REDE)
    comando = [parte.format(ESPELHO_NO_REMOTO.format(principal),
                            ESPELHO_NO_REMOTO.format(integracao))
               for parte in COMANDO_DO_QUE_A_PRINCIPAL_NAO_TEM]
    resposta = responde(comando, raiz, TEMPO_DO_GIT)
    if resposta is NAO_MEDIDO or resposta[0] != 0:
        return NAO_MEDIDO
    return [l for l in resposta[1].split("\n") if l.strip()]


def commits_desta_sessao(raiz: Path, principal: str, integracao: str,
                         abertura, adiante: list) -> list:
    if abertura is None or not adiante:
        return list(adiante)
    comando = [parte.format(ESPELHO_NO_REMOTO.format(principal),
                            ESPELHO_NO_REMOTO.format(integracao),
                            int(abertura))
               for parte in COMANDO_DO_QUE_ESTA_SESSAO_ACRESCENTOU]
    resposta = responde(comando, raiz, TEMPO_DO_GIT)
    if resposta is NAO_MEDIDO or resposta[0] != 0:
        return list(adiante)
    return [l for l in resposta[1].split("\n") if l.strip()]


def ha_pedido_de_incorporacao_aberto(raiz: Path, principal: str,
                                     integracao: str):
    comando = [parte.format(principal, integracao)
               for parte in COMANDO_DO_PEDIDO_ABERTO]
    resposta = responde(comando, raiz, TEMPO_DA_REDE)
    if resposta is NAO_MEDIDO or resposta[0] != 0:
        return NAO_MEDIDO
    try:
        return int(resposta[1]) > 0
    except ValueError:
        return NAO_MEDIDO


def resposta_limpa(comando: list, raiz: Path, tempo: int) -> str:
    resposta = responde(comando, raiz, tempo)
    if resposta is NAO_MEDIDO or resposta[0] != 0:
        return ""
    return resposta[1]


def chegou_ao_repositorio_duravel(raiz: Path, branch: str):
    if not branch:
        return NAO_MEDIDO
    aqui = resposta_limpa(COMANDO_DO_COMMIT_DA_ARVORE, raiz, TEMPO_DO_GIT)
    comando = [parte.format(branch) for parte in COMANDO_DA_BRANCH_NO_DURAVEL]
    resposta = responde(comando, raiz, TEMPO_DA_REDE)
    if not aqui or resposta is NAO_MEDIDO or resposta[0] != 0:
        return NAO_MEDIDO
    la = resposta[1].split()
    return bool(la) and la[0] == aqui


def etapa_em_curso() -> str:
    return os.environ.get(MARCA_DE_ETAPA_NO_AMBIENTE, "").strip()


def _ha_destino_declarado(raiz: Path, principal: str, integracao: str,
                          adiante: list):
    aberto = ha_pedido_de_incorporacao_aberto(raiz, principal, integracao)
    if aberto is True:
        return True
    if pedido_mesclado_que_ja_contem(raiz, principal, integracao, adiante):
        return True
    return aberto


def medir(raiz: Path, abertura=None, entrada=None) -> dict:
    suja, herdada = sujeira_desta_sessao_e_herdada(raiz, abertura, entrada)
    nao_julgada = linhas_que_a_camada_nao_julga(raiz)
    etapa = etapa_em_curso()
    if etapa:
        branch = resposta_limpa(COMANDO_DA_BRANCH_DA_ARVORE, raiz, TEMPO_DO_GIT)
        return {
            "etapa": etapa,
            "suja": suja,
            "herdada": herdada,
            "nao_julgada": nao_julgada,
            "branch": branch,
            "duravel": chegou_ao_repositorio_duravel(raiz, branch),
        }
    principal = sorted(branches_por_incorporacao(raiz))
    principal = principal[0] if principal else ""
    integracao = branch_de_integracao(raiz)
    tudo = commits_da_integracao_fora_da_principal(
        raiz, principal, integracao)
    if tudo is NAO_MEDIDO:
        return {
            "etapa": "", "suja": suja, "herdada": herdada,
            "nao_julgada": nao_julgada,
            "sobra": sobra_fora_da_branch_de_entrega(raiz),
            "principal": principal, "integracao": integracao,
            "adiante": NAO_MEDIDO, "herdados": [], "pedido": NAO_MEDIDO,
        }
    desta = (commits_desta_sessao(raiz, principal, integracao, abertura, tudo)
             if tudo else [])
    return {
        "etapa": "",
        "suja": suja,
        "herdada": herdada,
        "nao_julgada": nao_julgada,
        "sobra": sobra_fora_da_branch_de_entrega(raiz),
        "principal": principal,
        "integracao": integracao,
        "adiante": desta,
        "herdados": [l for l in tudo if l not in desta],
        "pedido": (_ha_destino_declarado(raiz, principal, integracao, tudo)
                   if tudo else NAO_MEDIDO),
    }


def primeiras_linhas(linhas: list) -> str:
    return "\n".join(f"  {l}" for l in linhas[:TETO_DE_LINHAS])


def cobrancas(estado: dict) -> list:
    cobradas = []
    if estado.get("suja"):
        cobradas.append(COBRA_ARVORE_SUJA.format(
            len(estado["suja"]), primeiras_linhas(estado["suja"])))
    if estado.get("herdada"):
        cobradas.append(COBRA_SUJEIRA_HERDADA.format(
            len(estado["herdada"]), primeiras_linhas(estado["herdada"])))
    if estado.get("nao_julgada"):
        cobradas.append(COBRA_SUJEIRA_QUE_A_CAMADA_NAO_JULGA.format(
            len(estado["nao_julgada"]),
            primeiras_linhas(estado["nao_julgada"])))
    if estado.get("etapa"):
        if estado.get("duravel") is NAO_MEDIDO:
            cobradas.append(COBRA_DURAVEL_NAO_MEDIDO.format(
                estado.get("branch")))
        elif not estado["duravel"]:
            cobradas.append(COBRA_FORA_DO_REPOSITORIO_DURAVEL.format(
                estado.get("branch")))
        return cobradas
    if estado.get("sobra"):
        cobradas.append(COBRA_SOBRA_DA_BRANCH.format(
            INSTRUMENTO_DA_ENTREGA, BANDEIRA_DA_ENTREGA, estado["sobra"]))
    adiante = estado.get("adiante")
    if adiante:
        if estado.get("pedido") is False:
            cobradas.append(COBRA_INTEGRACAO_SEM_PEDIDO.format(
                estado.get("integracao"), len(adiante),
                estado.get("principal"), primeiras_linhas(adiante)))
        elif estado.get("pedido") is NAO_MEDIDO:
            cobradas.append(COBRA_PEDIDO_NAO_MEDIDO.format(
                estado.get("integracao"), len(adiante),
                estado.get("principal")))
    return cobradas


def relato(estado: dict) -> list:
    herdados = estado.get("herdados")
    if not herdados or estado.get("pedido") is True:
        return []
    return [RELATA_HERDADO.format(estado.get("integracao"), len(herdados),
                                  estado.get("principal"),
                                  primeiras_linhas(herdados))]


def decisao(entrada: dict, raiz: Path):
    if entrada.get("stop_hook_active"):
        return "", ""
    estado = medir(raiz, abertura_da_sessao(entrada), entrada)
    cobradas = cobrancas(estado)
    if not cobradas:
        return "", "\n\n".join(relato(estado))
    return "\n\n".join(
        [ABERTURA_DA_COBRANCA, *cobradas, FECHAMENTO_DA_COBRANCA]), ""


def main() -> int:
    try:
        entrada = json.load(sys.stdin)
        if not isinstance(entrada, dict):
            return SILENCIO
        motivo, dito = decisao(entrada, raiz_do_projeto_nunca_o_cwd())
        if not motivo:
            if dito:
                print(json.dumps({"systemMessage": dito},
                                 ensure_ascii=False))
            return SILENCIO
    except Exception:
        return FALHA_ABERTA

    print(json.dumps({"decision": DECISAO_DE_BLOQUEAR, "reason": motivo,
                      "hookSpecificOutput": {
                          "hookEventName": EVENTO_DE_PARADA}},
                     ensure_ascii=False))
    return COBRANCA_ENTREGUE


ARVORE_LIMPA = {"etapa": "", "suja": [], "sobra": "", "principal": "main",
                "integracao": "homolog", "adiante": [], "herdados": [],
                "pedido": NAO_MEDIDO}
DENTRO_DA_ETAPA = {"etapa": "trabalhar", "suja": [],
                   "branch": "issue/1-algo", "duravel": True}


def com(**mudanca) -> dict:
    return {**ARVORE_LIMPA, **mudanca}


def na_etapa(**mudanca) -> dict:
    return {**DENTRO_DA_ETAPA, **mudanca}


COBRA_FORA_DA_ETAPA = [
    ("árvore suja", com(suja=["?? novo.py"])),
    ("commit fora da branch de entrega",
     com(sobra="1 commit(s) em issue/1-algo que NÃO estão em origin/homolog")),
    ("integração à frente da principal sem pedido de incorporação aberto",
     com(adiante=["abc1234 trabalho"], pedido=False)),
    ("integração à frente e o pedido nem medido",
     com(adiante=["abc1234 trabalho"], pedido=NAO_MEDIDO)),
]

FORA_DA_ETAPA_PALAVRA_POR_PALAVRA = [
    "A árvore está suja — 1 arquivo(s) fora de commit nenhum:\n"
    "  ?? novo.py\n"
    "Trabalho que não entra em commit some com a pasta que o guardou, e "
    "ninguém fica sabendo que existiu. Ou vai, ou é descartado: commite na "
    "branch de trabalho, ou apague dizendo a razão em uma linha.",

    "Há commit fora da branch de entrega. O que "
    "`.agents/camada/camada.py --entrega` respondeu:\n"
    "1 commit(s) em issue/1-algo que NÃO estão em origin/homolog\n"
    "Commit em branch que ninguém vai incorporar não existe para o resto do "
    "mundo, e some no dia em que a branch for podada.",

    "A integração 'homolog' está 1 commit(s) à frente de 'main' e NÃO há "
    "pedido de incorporação aberto entre elas:\n"
    "  abc1234 trabalho\n"
    "Destino inclui o passo seguinte, não só a branch: se a promoção é por "
    "pedido de incorporação, ele fica ABERTO, não planejado para depois. "
    "Trabalho parado antes disso não chegou a lugar nenhum, só parece pronto.",

    "A integração 'homolog' está 1 commit(s) à frente de 'main', e não deu "
    "para medir se existe pedido de incorporação aberto entre elas — o `gh` "
    "não respondeu. Sem a medição isto é 'não medido', nunca 'não existe': "
    "confira à mão antes de encerrar.",
]

COBRA_DENTRO_DA_ETAPA = [
    ("dentro da execução, a árvore suja volta a falar",
     na_etapa(suja=["?? novo.py"])),
    ("dentro da execução, a branch de trabalho não chegou ao repositório "
     "durável", na_etapa(duravel=False)),
    ("dentro da execução, o repositório durável nem foi medido",
     na_etapa(duravel=NAO_MEDIDO)),
]

COBRA = COBRA_FORA_DA_ETAPA + COBRA_DENTRO_DA_ETAPA

CALA = [
    ("tudo em ordem", ARVORE_LIMPA),
    ("integração à frente, mas com pedido de incorporação aberto",
     com(adiante=["abc1234 trabalho"], pedido=True)),
    ("pedido não medido, mas a integração não está à frente",
     com(adiante=[], pedido=NAO_MEDIDO)),
    ("dentro da execução, a branch de trabalho já está no repositório "
     "durável, no mesmo commit", DENTRO_DA_ETAPA),
]

MARCA_DA_SUJEIRA = "?? "
ARQUIVO_DE_MENTIRA = "solto.txt"
FEITO_DE_MENTIRA = "feito.txt"
ORIGEM_DE_MENTIRA = "origem"
TRABALHO_DE_MENTIRA = "arvore"
BRANCH_DE_MENTIRA = "issue/999-prova"
ENTRADA_DE_PARADA = "{}"


def git_de_mentira(arvore: Path, *argumentos) -> None:
    subprocess.run(["git", *argumentos], cwd=arvore, check=True,
                   capture_output=True)


def trabalho_de_mentira_com_repositorio_duravel(pasta: Path) -> Path:
    origem, arvore = pasta / ORIGEM_DE_MENTIRA, pasta / TRABALHO_DE_MENTIRA
    origem.mkdir()
    arvore.mkdir()
    git_de_mentira(origem, "init", "-q", "--bare")
    git_de_mentira(arvore, "init", "-q", "-b", BRANCH_DE_MENTIRA)
    git_de_mentira(arvore, "config", "user.email", "prova@exemplo")
    git_de_mentira(arvore, "config", "user.name", "Prova")
    git_de_mentira(arvore, "remote", "add", "origin", str(origem))
    (arvore / FEITO_DE_MENTIRA).write_text("feito", encoding="utf-8")
    git_de_mentira(arvore, "add", "-A")
    git_de_mentira(arvore, "commit", "-qm", "trabalho")
    return arvore


def o_que_o_gancho_responde(arvore: Path, etapa: str) -> str:
    ambiente = {**os.environ, VARIAVEL_DA_RAIZ_DO_PROJETO: str(arvore)}
    if etapa:
        ambiente[MARCA_DE_ETAPA_NO_AMBIENTE] = etapa
    else:
        ambiente.pop(MARCA_DE_ETAPA_NO_AMBIENTE, None)
    pronto = subprocess.run(
        [sys.executable, str(Path(__file__).resolve())],
        input=ENTRADA_DE_PARADA, capture_output=True, text=True, env=ambiente)
    return pronto.stdout.strip()


def motivo_do_gancho(arvore: Path, etapa: str) -> str:
    respondeu = o_que_o_gancho_responde(arvore, etapa)
    if not respondeu:
        return ""
    dito = json.loads(respondeu)
    if dito.get("decision") != DECISAO_DE_BLOQUEAR:
        return ""
    return dito.get("reason", "")


def testar() -> int:
    import tempfile
    falhas, comportamento = [], []

    for rotulo, estado in COBRA:
        if not cobrancas(estado):
            falhas.append(FALHA_COBROU_DE_MENOS.format(rotulo))
    for rotulo, estado in CALA:
        if cobradas := cobrancas(estado):
            falhas.append(FALHA_COBROU_DE_MAIS.format(rotulo, cobradas[0]))

    def caso(rotulo, condicao):
        comportamento.append((rotulo, bool(condicao)))

    raiz_de_prova = Path("/tmp/atlas-prova")
    caso("renomear por `git mv` conta como escrita DESTA sessao — antes o "
         "gancho so via Write e Edit, chamava o proprio trabalho de herdado "
         "e mandava a sessao abandona-lo",
         str(raiz_de_prova / "b.md") in caminhos_que_o_shell_mexeu(
             "git mv a.md b.md", raiz_de_prova))
    caso("editar por `sed -i` tambem conta",
         str(raiz_de_prova / "x.py") in caminhos_que_o_shell_mexeu(
             "sed -i 's/a/b/' x.py", raiz_de_prova))
    caso("redirecionar para arquivo tambem conta",
         str(raiz_de_prova / "saida.json") in caminhos_que_o_shell_mexeu(
             "echo oi > saida.json", raiz_de_prova))
    caso("comando que so LE nao vira escrita — senao toda varredura marcaria "
         "o repositorio inteiro como escrito por esta sessao",
         caminhos_que_o_shell_mexeu("grep -rn coisa arquivo.py",
                                    raiz_de_prova) == set())
    caso("comando vazio ou que nao e texto nao estoura",
         caminhos_que_o_shell_mexeu(None, raiz_de_prova) == set()
         and caminhos_que_o_shell_mexeu("", raiz_de_prova) == set())

    caso("commit que a sessão NAO fez nao vira cobranca dela: sessao de "
         "estudo encontra a integracao a frente e nao e dona disso",
         not cobrancas(com(adiante=[], herdados=["abc1234 de ontem"],
                           pedido=False)))
    caso("e o que ela encontrou continua dito, sem mandar resolver",
         any("ontem" in linha for linha in
             relato(com(adiante=[], herdados=["abc1234 de ontem"],
                        pedido=False))))
    caso("commit desta sessao continua cobrado",
         cobrancas(com(adiante=["abc1234 agora"], pedido=False)))
    caso("comparacao nao medida nao derruba o gancho inteiro: sem origin, "
         "sem rede ou em clone novo ele ainda cobra a arvore suja",
         cobrancas(com(adiante=NAO_MEDIDO, suja=["?? novo.py"])))
    with tempfile.TemporaryDirectory(prefix="cobra-vizinha-") as pasta:
        base = Path(pasta)
        raiz_falsa = base / "repo"
        (raiz_falsa / "sub").mkdir(parents=True)
        (raiz_falsa / "meu.py").write_text("x", encoding="utf-8")
        (raiz_falsa / "alheio.py").write_text("y", encoding="utf-8")
        lar = base / "lar"
        transcritos = lar / PASTA_DOS_TRANSCRITOS / str(raiz_falsa).replace(os.sep, "-")
        transcritos.mkdir(parents=True)
        agora = 1000.0
        meu_transcrito = transcritos / "minha.jsonl"
        meu_transcrito.write_text(json.dumps({"message": {"content": [
            {"type": "tool_use", "name": "Write",
             "input": {"file_path": str(raiz_falsa / "meu.py")}}]}}) + "\n",
            encoding="utf-8")
        os.utime(meu_transcrito, (agora, agora))
        entrada_falsa = {CHAVE_DA_SESSAO: "minha",
                         CHAVE_DO_TRANSCRITO: str(meu_transcrito)}
        sujas = [" M meu.py", " M alheio.py"]

        def _com(vizinha_viva):
            if vizinha_viva:
                outra = transcritos / "outra.jsonl"
                outra.write_text("x", encoding="utf-8")
                os.utime(outra, (agora - 60, agora - 60))
            else:
                alvo = transcritos / "outra.jsonl"
                if alvo.exists():
                    alvo.unlink()
            global linhas_da_arvore_suja
            guardada = linhas_da_arvore_suja
            linhas_da_arvore_suja = lambda _: list(sujas)
            try:
                return sujeira_desta_sessao_e_herdada(
                    raiz_falsa, None, entrada_falsa, agora, lar)
            finally:
                linhas_da_arvore_suja = guardada

        minha, herdada = _com(vizinha_viva=False)
        caso("sozinho na pasta, a cobranca segue como sempre: a sujeira "
             "toda e desta sessao",
             len(minha) == 2 and herdada == [])

        minha, herdada = _com(vizinha_viva=True)
        caso("com outra sessao viva, so e cobrado o arquivo que ESTA sessao "
             "escreveu — o que ela nunca tocou vira herdado",
             minha == [" M meu.py"] and herdada == [" M alheio.py"])

    with tempfile.TemporaryDirectory(prefix="cobra-sem-git-") as sozinho:
        caso("e medir() sobrevive a pasta sem git nenhum, em vez de estourar "
             "e calar o gancho por dentro do except",
             isinstance(medir(Path(sozinho), None), dict))

    da_sobra = "".join(cobrancas(COBRA_FORA_DA_ETAPA[1][1]))
    caso("a cobrança da segunda condição nomeia o instrumento que já existe",
         INSTRUMENTO_DA_ENTREGA in da_sobra and BANDEIRA_DA_ENTREGA in da_sobra)
    caso("as três condições cobram juntas quando as três falham",
         len(cobrancas(com(suja=["?? x"], sobra="sobra",
                           adiante=["abc x"], pedido=False))) == 3)

    with tempfile.TemporaryDirectory(prefix="cobrar-destino-") as tmp:
        arvore = Path(tmp).resolve()
        git_de_mentira(arvore, "init", "-q")
        caso("árvore sem nada solto não tem linha de sujeira",
             linhas_da_arvore_suja(arvore) == [])
        (arvore / ARQUIVO_DE_MENTIRA).write_text("solto", encoding="utf-8")
        caso("arquivo solto vira linha de sujeira medida no git",
             any(l.startswith(MARCA_DA_SUJEIRA)
                 for l in linhas_da_arvore_suja(arvore)))

    daqui = raiz_do_projeto_nunca_o_cwd()
    direto = subprocess.run(
        [sys.executable, INSTRUMENTO_DA_ENTREGA, BANDEIRA_DA_ENTREGA],
        cwd=daqui, capture_output=True, text=True)
    caso("a segunda condição chama o instrumento, e concorda com ele",
         bool(sobra_fora_da_branch_de_entrega(daqui))
         == (direto.returncode != 0))
    caso("parada que já é laço de gancho cala",
         decisao({"stop_hook_active": True}, daqui) == ("", ""))
    montado = [parte.format("principal-x", "integracao-y")
               for parte in COMANDO_DO_PEDIDO_ABERTO]
    caso("a consulta do pedido pergunta pela integração, não pela principal "
         "duas vezes",
         montado[montado.index("--base") + 1] == "principal-x"
         and montado[montado.index("--head") + 1] == "integracao-y")
    for (rotulo, estado), palavra_por_palavra in zip(
            COBRA_FORA_DA_ETAPA, FORA_DA_ETAPA_PALAVRA_POR_PALAVRA):
        caso("sem a marca de etapa, a cobrança de hoje sai palavra por "
             f"palavra: {rotulo}",
             cobrancas(estado) == [palavra_por_palavra])
    dentro_com_integracao_adiante = cobrancas(
        na_etapa(duravel=False, adiante=["abc1234 trabalho"], pedido=False))
    caso("com a marca de etapa, o motivo nunca cita pedido de incorporação — "
         "nem quando a integração está à frente da principal",
         "pedido de incorporação" not in "".join(
             dentro_com_integracao_adiante))

    with tempfile.TemporaryDirectory(prefix="cobrar-destino-etapa-") as tmp:
        arvore = trabalho_de_mentira_com_repositorio_duravel(
            Path(tmp).resolve())
        (arvore / ARQUIVO_DE_MENTIRA).write_text("solto", encoding="utf-8")
        caso("com a marca de etapa e a árvore suja, o gancho responde block e "
             "o motivo cita a árvore suja",
             "A árvore está suja" in motivo_do_gancho(arvore, "trabalhar"))
        (arvore / ARQUIVO_DE_MENTIRA).unlink()
        caso("com a marca de etapa, árvore limpa e um commit na branch de "
             "trabalho não empurrado, o gancho responde block e o motivo cita "
             "o repositório durável",
             "repositório durável"
             in motivo_do_gancho(arvore, "trabalhar"))
        git_de_mentira(arvore, "push", "-q", "origin", BRANCH_DE_MENTIRA)
        caso("com a marca de etapa, árvore limpa e a branch de trabalho já "
             "empurrada no mesmo commit, o gancho fica em silêncio",
             o_que_o_gancho_responde(arvore, "trabalhar") == "")
        caso("a branch de trabalho empurrada no mesmo commit chegou ao "
             "repositório durável",
             chegou_ao_repositorio_duravel(arvore, BRANCH_DE_MENTIRA) is True)
        git_de_mentira(arvore, "commit", "-q", "--allow-empty", "-m", "mais")
        caso("commit depois do empurrão não está no repositório durável",
             chegou_ao_repositorio_duravel(arvore, BRANCH_DE_MENTIRA) is False)
        git_de_mentira(arvore, "remote", "remove", "origin")
        caso("sem repositório durável para perguntar, a chegada é não medida, "
             "nunca chegou",
             chegou_ao_repositorio_duravel(arvore, BRANCH_DE_MENTIRA)
             is NAO_MEDIDO)

    with tempfile.TemporaryDirectory(prefix="cobrar-destino-regua-") as tmp:
        base = Path(tmp).resolve()
        origem, quieta, outra = base / "origem", base / "quieta", base / "outra"
        origem.mkdir()
        git_de_mentira(origem, "init", "-q", "--bare", "-b", "main")
        git_de_mentira(base, "clone", "-q", str(origem), str(outra))
        git_de_mentira(outra, "config", "user.email", "prova@exemplo")
        git_de_mentira(outra, "config", "user.name", "Prova")
        git_de_mentira(outra, "commit", "-q", "--allow-empty", "-m", "raiz")
        git_de_mentira(outra, "push", "-q", "-u", "origin", "main")
        git_de_mentira(outra, "checkout", "-q", "-b", "homolog")
        git_de_mentira(outra, "push", "-q", "-u", "origin", "homolog")
        git_de_mentira(base, "clone", "-q", str(origem), str(quieta))
        git_de_mentira(outra, "commit", "-q", "--allow-empty", "-m", "trabalho")
        git_de_mentira(outra, "push", "-q", "origin", "homolog")
        git_de_mentira(quieta, "fetch", "-q", "origin", "homolog")
        git_de_mentira(outra, "checkout", "-q", "main")
        git_de_mentira(outra, "merge", "-q", "homolog")
        git_de_mentira(outra, "push", "-q", "origin", "main")
        caso("a régua busca o remoto antes de medir: integração já mesclada na "
             "principal lá fora não vira acusação por ref local velha",
             commits_da_integracao_fora_da_principal(quieta, "main", "homolog")
             == [])

    with tempfile.TemporaryDirectory(prefix="cobrar-destino-herdada-") as tmp:
        import time
        from datetime import timezone
        arvore = Path(tmp).resolve()
        git_de_mentira(arvore, "init", "-q")
        velho, novo = arvore / "velho.txt", arvore / "novo.txt"
        velho.write_text("de antes", encoding="utf-8")
        os.utime(velho, (1000, 1000))
        novo.write_text("de agora", encoding="utf-8")
        suja, herdada = sujeira_desta_sessao_e_herdada(arvore, time.time() - 60)
        caso("sujeira anterior à abertura da sessão é herdada, e só a desta "
             "sessão trava",
             suja == ["?? novo.txt"] and herdada == ["?? velho.txt"])
        caso("sem abertura medida, toda sujeira é desta sessão",
             sujeira_desta_sessao_e_herdada(arvore, None)[1] == [])
        transcrito = arvore / "transcrito.jsonl"
        transcrito.write_text(
            '{"type": "sem-instante"}\n'
            '{"type": "com", "timestamp": "2026-09-01T20:28:57.754Z"}\n',
            encoding="utf-8")
        caso("a abertura da sessão sai do primeiro timestamp do transcript",
             abertura_da_sessao({"transcript_path": str(transcrito)})
             == datetime(2026, 9, 1, 20, 28, 57, 754000,
                         tzinfo=timezone.utc).timestamp())
        caso("a cobrança da herdada nomeia o arquivo e diz que não trava",
             "NÃO trava" in "".join(cobrancas(
                 {**ARVORE_LIMPA, "herdada": ["?? velho.txt"]})))

    caso("arquivo que a camada JULGA continua barrando: código solto trava",
         any("árvore está suja" in c
             for c in cobrancas({**ARVORE_LIMPA, "suja": ["?? sujo.py"],
                                 "nao_julgada": []})))
    caso("arquivo que a camada NÃO julga avisa e NÃO trava: imagem solta "
         "não impede a entrega",
         (lambda c: not any("árvore está suja" in x for x in c)
          and any("não sabe julgar" in x for x in c))(
             cobrancas({**ARVORE_LIMPA, "suja": [],
                        "nao_julgada": ["?? foto.png"]})))
    caso("a classificação olha a extensão do caminho, não a linha inteira",
         a_camada_julga("?? app/servico.py")
         and not a_camada_julga("?? docs/diagrama.PNG"))
    caso("a cobrança nomeia a regra 16 e manda gravar o aprendizado em "
         "conhecimento/, com a linha concreta",
         "regra 16" in ABERTURA_DA_COBRANCA
         and "regra 4" in FECHAMENTO_DA_COBRANCA
         and "`conhecimento/`" in FECHAMENTO_DA_COBRANCA
         and "nada fica sem destino" in FECHAMENTO_DA_COBRANCA)

    falhas += [FALHA_COMPORTAMENTO.format(rotulo)
               for rotulo, passou in comportamento if not passou]
    for falha in falhas:
        print(FALHA_DE_CASO.format(falha))
    total = len(COBRA) + len(CALA) + len(comportamento)
    if falhas:
        print(RESUMO_FALHOU.format(len(falhas), total))
        return 1
    print(RESUMO_OK.format(total, len(COBRA), len(CALA), len(comportamento)))
    return 0


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
