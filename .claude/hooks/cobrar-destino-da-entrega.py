import re
import json
import re
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
SAIDA_DO_INSTRUMENTO_NAO_MEDIDO = 2
COMANDO_DA_SUJEIRA = ["git", "status", "--porcelain"]
COMANDO_DO_QUE_A_PRINCIPAL_NAO_TEM = [
    "git", "log", "--oneline", "--no-decorate", "{}..{}"]
COMANDO_DO_QUE_ESTA_SESSAO_ACRESCENTOU = [
    "git", "log", "--oneline", "--no-decorate", "--since=@{2}", "{0}..{1}"]
COMANDO_DO_PEDIDO_ABERTO = [
    "gh", "pr", "list", "--base", "{0}", "--head", "{1}", "--state", "open",
    "--json", "number,author,reviewRequests,latestReviews"]
CHAVE_DOS_PROJETOS = "projetos"
CHAVE_DO_REPOSITORIO = "repositorio"
CHAVE_DO_REVISOR = "revisor"
CAMPO_DO_AUTOR = "author"
CHAVE_DO_SOMENTE_LEITURA = "somente_leitura"
CHAVE_DAS_AUTORIZACOES = "autorizacoes"
CHAVE_DAS_ISSUES = "issues"
COMANDO_DO_CORPO_DA_ISSUE = [
    "gh", "issue", "view", "{0}", "--repo", "{1}", "--json", "body,state"]
CAMPO_DO_CORPO = "body"
CAMPO_DA_SITUACAO = "state"
SITUACAO_ABERTA = "OPEN"
CAIXA_EM_BRANCO = "- [ ]"
CAIXA_MARCADA = ("- [x]", "- [X]")
MARCA_DA_ISSUE_NA_BRANCH = re.compile(r"(?:^|/)issue/(\d+)(?:-|$)")
MARCA_DA_ISSUE_NO_COMMIT = re.compile(r"\(issue (\d+)\)")
COMANDO_DAS_MENSAGENS = ["git", "log", "--format=%s", "{0}..HEAD"]
TETO_DE_CRITERIOS_MOSTRADOS = 3
CHAVE_DO_PUSH = "push"
COMANDO_DA_INTEGRACAO_NO_REMOTO = ["git", "ls-remote", "--heads", "origin", "{}"]
COMANDO_DE_BUSCA_DA_INTEGRACAO = ["git", "fetch", "--quiet", "origin", "{}"]
COMANDO_DO_QUE_A_INTEGRACAO_NAO_TEM = [
    "git", "log", "--oneline", "--no-decorate", "{}..HEAD"]
ESTE_REPOSITORIO = "."
CAMPO_DOS_SOLICITADOS = "reviewRequests"
CAMPO_DAS_REVISOES = "latestReviews"
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
COMANDO_DA_RAIZ_DO_REPOSITORIO = ["git", "rev-parse", "--show-toplevel"]
COMANDO_DO_QUE_NAO_ESTA_EM_REMOTO_NENHUM = [
    "git", "log", "--oneline", "--no-decorate", "HEAD", "--not", "--remotes"]
CHAVE_DO_TRANSCRITO = "transcript_path"
CHAVE_DA_SESSAO = "session_id"
PASTA_DOS_TRANSCRITOS = ".claude/projects"
SEPARADORES_QUE_VIRAM_HIFEN_NO_NOME_DA_PASTA = (":", "/", "\\", ".")
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
MARCA_NO_AMBIENTE = "ATLAS_SO_LEITURA"
VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

DITO_DA_SESSAO_DE_PESQUISA = (
    "Sessão de pesquisa: a regra 16 não cobra destino aqui, porque esta "
    "sessão não entrega em disco — o modo somente leitura está posto "
    "({}), e a cerca recusou qualquer escrita no repositório.\n"
    "O destino dela é a ISSUE: antes de fechar, o que a sessão apurou vira "
    "corpo ou comentário lá. O que não estiver na issue não existe.")

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
COBRA_SOBRA_NAO_MEDIDO = (
    "Não deu para medir se há commit fora da branch de entrega — `{} {}` "
    "respondeu que NÃO MEDIU, porque {}. Sem a medição isto é 'não medido', "
    "nunca 'não há': confira à mão antes de encerrar."
)
RAZAO_DE_NAO_MEDIR = []
MOTIVO_TEMPO_ESGOTADO = "o teto de {} s esgotou antes de a resposta chegar"
MOTIVO_NAO_SUBIU = "o processo não subiu ({})"
MOTIVO_O_INSTRUMENTO_DISSE = (
    "o próprio instrumento saiu com o código de não-medido")
MOTIVO_NAO_DITO = "nada ficou registrado sobre a causa"
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
COBRA_CRITERIO_EM_BRANCO = (
    "A issue {} tem {} critério(s) de pronto EM BRANCO, e o trabalho já está "
    "na {}:\n{}\n"
    "Critério que ninguém conferiu não vira pronto por mescla: caixa marcada "
    "não fecha issue, critério conferido fecha. Rode o comando de cada um, "
    "cole a saída na issue e marque; ou diga em uma linha por que ele sai do "
    "escopo. Se o pedido de incorporação carrega o verbo que FECHA a issue, "
    "tire-o: o fechamento é ato de quem conferiu."
)
COBRA_CRITERIO_NAO_MEDIDO = (
    "A issue {} não se deixou ler ({}), então os critérios de pronto dela não "
    "foram conferidos — e não conferido não é cumprido. Rode "
    "`gh issue view {} --repo {}` você mesmo antes de dar por entregue."
)
RELATA_CRITERIO_CUMPRIDO = (
    "A issue {} tem os {} critério(s) de pronto marcados — o destino do "
    "trabalho está declarado nela."
)
COBRA_PEDIDO_NAO_MEDIDO = (
    "A integração {!r} está {} commit(s) à frente de {!r}, e não deu para "
    "medir se existe pedido de incorporação aberto entre elas — o `gh` não "
    "respondeu. Sem a medição isto é 'não medido', nunca 'não existe': "
    "confira à mão antes de encerrar."
)
COBRA_PEDIDO_SEM_REVISOR = (
    "O pedido de incorporação de {0!r} para {1!r} está aberto, mas o "
    "revisor configurado {2!r} não foi solicitado nem revisou "
    "(`gh pr list --base {1} --head {0} --json "
    "reviewRequests,latestReviews`).\n"
    "Pedido sem revisor pedido é entrega parada na mesa de ninguém: solicite "
    "com `gh api -X POST repos/{{owner}}/{{repo}}/pulls/<n>/requested_reviewers "
    "-f \"reviewers[]={2}\"` (o `gh pr edit --add-reviewer` tropeça em "
    "repositório com projetos clássicos), ou diga em uma linha por que fica "
    "assim."
)
COBRA_REVISAO_NAO_MEDIDA = (
    "O pedido de incorporação de {0!r} para {1!r} está aberto e há "
    "revisor configurado ({2!r}), mas não deu para medir se ele foi "
    "solicitado — o `gh` não devolveu os campos de revisão. Sem a medição "
    "isto é 'não medido', nunca 'solicitado': confira à mão antes de "
    "encerrar."
)
RELATA_REVISOR_QUE_E_O_AUTOR = (
    "Para saber, não para resolver: o revisor configurado ({!r}) é quem "
    "abriu o pedido, e o GitHub recusa pedir revisão ao próprio autor "
    "(HTTP 422). Por isso a cobrança de revisor cala aqui — pedir o "
    "impossível a cada parada ensina a sessão a ignorar a cobrança inteira. "
    "O pedido já está na mesa de quem decide; se você quer outro par de "
    "olhos, o caminho é abrir o pedido por outra conta ou nomear outro "
    "revisor no cadastro do projeto.")
RELATA_HERDADO = (
    "Para saber, não para resolver: a integração {!r} já estava {} commit(s) "
    "à frente de {!r} quando esta sessão abriu, e não há pedido de "
    "incorporação aberto entre elas:\n{}\n"
    "Nada disso é obra desta sessão, então ela não é cobrada — quem encerra "
    "uma dívida é quem a fez. Fica dito porque estado sem destino não passa "
    "calado."
)
COBRA_VIZINHO_SEM_DESTINO = (
    "O repositório vizinho {} foi tocado nesta sessão e ficou sem destino:\n{}\n"
    "A regra 16 vale por repositório tocado, não só por este: fechar um "
    "inteiro dá a sensação de ter fechado tudo, e é assim que o outro fica "
    "para trás. Dê a cada linha acima o destino que ela pede, ou descarte "
    "dizendo a razão em uma linha."
)
LINHA_DO_VIZINHO_SUJO = "  {} arquivo(s) fora de commit:\n{}"
LINHA_DO_VIZINHO_SEM_REMOTO = (
    "  {} commit(s) que não estão em remoto nenhum "
    "(`git log HEAD --not --remotes`):\n{}")
LINHA_DO_VIZINHO_NAO_MEDIDO = (
    "  não deu para medir os commits sem remoto — o git não respondeu; "
    "confira à mão, porque não medido nunca é zero")
LINHA_DO_VIZINHO_FORA_DA_INTEGRACAO = (
    "  {0} commit(s) da branch {1!r} que não estão em {2} "
    "(`git log {2}..HEAD`):\n{3}\n"
    "  aqui a sessão pode empurrar, e onde ela pode empurrar a entrega é a "
    "MESCLA na integração declarada no cadastro: branch de trabalho "
    "empurrada é sincronização, não entrega. Da branch de trabalho para a "
    "integração não se abre pedido de incorporação — o pedido é o caminho "
    "da integração para a branch por incorporação, e o do vizinho somente "
    "leitura. `git -C {4} switch {5} && git -C {4} merge --no-ff {1} && "
    "git -C {4} push origin {5}`")
LINHA_DO_VIZINHO_SEM_PUSH = (
    "  {0} commit(s) da branch {1!r} que não estão em {2} "
    "(`git log {2}..HEAD`):\n{3}\n"
    "  o cadastro do projeto NÃO autoriza push aqui (`autorizacoes.push`), "
    "e omissão nega: a entrega é do dono, não desta sessão. Diga a ele o "
    "que está commitado e onde, e pare — empurrar mesmo assim é passar por "
    "cima da autorização que o cadastro declara")
LINHA_DO_VIZINHO_SEM_PEDIDO = (
    "  {0} commit(s) da branch {1!r} que não estão em {2}, e NENHUM pedido "
    "de incorporação aberto de {1!r} para {3!r}:\n{4}\n"
    "  vizinho somente leitura é território de terceiro: a entrega é por "
    "pedido de incorporação, e ele só se abre com autorização EXPRESSA do "
    "dono, uma por vez. Pergunte a ele primeiro; com o sim, `gh pr create "
    "-R <dono>/<repo> --base {3} --head {1}`. Sem o sim, diga a ele o que "
    "está pendente e pare")
LINHA_DO_VIZINHO_PEDIDO_NAO_MEDIDO = (
    "  {0} commit(s) da branch {1!r} que não estão em {2}, e não deu para "
    "medir se há pedido de incorporação aberto — o `gh` não respondeu. Não "
    "medido nunca é 'aberto': confira com `gh pr list -R <dono>/<repo> "
    "--base {3} --head {1} --state open` antes de encerrar")
LINHA_DO_VIZINHO_SEM_A_INTEGRACAO = (
    "  a integração {0!r} que o cadastro declara para este vizinho NÃO "
    "existe no remoto dele (`git ls-remote --heads origin {0}` veio vazio). "
    "Sem ela não há para onde entregar, e o nome não se adivinha: declare a "
    "certa em `nucleo/executor.json`, no `branches.integracao` do projeto "
    "deste vizinho — a do topo é a DESTE repositório, e só serve de reserva "
    "quando por acaso coincide")
LINHA_DO_VIZINHO_INTEGRACAO_NAO_MEDIDA = (
    "  não deu para medir a integração {0!r} do cadastro — o git não "
    "respondeu (`git ls-remote --heads origin {0}`). Não medido nunca é "
    "'entregue': confira à mão antes de encerrar")
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


def responde_sem_aparar(comando: list, raiz: Path, tempo: int):
    try:
        pronto = subprocess.run(comando, cwd=raiz, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=tempo)
    except subprocess.TimeoutExpired:
        RAZAO_DE_NAO_MEDIR.append(MOTIVO_TEMPO_ESGOTADO.format(tempo))
        return NAO_MEDIDO
    except (OSError, subprocess.SubprocessError) as falha:
        RAZAO_DE_NAO_MEDIR.append(
            MOTIVO_NAO_SUBIU.format(type(falha).__name__))
        return NAO_MEDIDO
    return pronto.returncode, pronto.stdout or ""


def responde(comando: list, raiz: Path, tempo: int):
    resposta = responde_sem_aparar(comando, raiz, tempo)
    if resposta is NAO_MEDIDO:
        return NAO_MEDIDO
    return resposta[0], resposta[1].strip()


def porque_nao_mediu() -> str:
    return RAZAO_DE_NAO_MEDIR[-1] if RAZAO_DE_NAO_MEDIR else MOTIVO_NAO_DITO


def a_camada_julga(linha: str) -> bool:
    caminho = linha[3:].strip().strip('"')
    return not caminho.lower().endswith(EXTENSOES_QUE_A_CAMADA_NAO_JULGA)


def linhas_da_arvore_suja(raiz: Path) -> list:
    return [l for l in _toda_a_sujeira(raiz) if a_camada_julga(l)]


def linhas_que_a_camada_nao_julga(raiz: Path) -> list:
    return [l for l in _toda_a_sujeira(raiz) if not a_camada_julga(l)]


def _toda_a_sujeira(raiz: Path) -> list:
    resposta = responde_sem_aparar(COMANDO_DA_SUJEIRA, raiz, TEMPO_DO_GIT)
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


def pasta_dos_transcritos(raiz: Path, lar: Path) -> Path:
    nome = str(raiz)
    for separador in SEPARADORES_QUE_VIRAM_HIFEN_NO_NOME_DA_PASTA:
        nome = nome.replace(separador, "-")
    return lar / PASTA_DOS_TRANSCRITOS / nome


def sujeira_desta_sessao_e_herdada(raiz: Path, abertura, entrada=None,
                                   agora=None, lar=None) -> tuple:
    suja = linhas_da_arvore_suja(raiz)
    herdada = [l for l in suja
               if modificado_antes_da_abertura(raiz, l, abertura)]
    minha = [l for l in suja if l not in herdada]
    if entrada is None:
        return minha, herdada
    lar = Path.home() if lar is None else lar
    pasta = pasta_dos_transcritos(raiz, lar)
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


def sobra_fora_da_branch_de_entrega(raiz: Path):
    if not (raiz / INSTRUMENTO_DA_ENTREGA).is_file():
        return ""
    resposta = responde(
        [sys.executable, INSTRUMENTO_DA_ENTREGA, BANDEIRA_DA_ENTREGA],
        raiz, TEMPO_DO_GIT)
    if resposta is NAO_MEDIDO:
        return NAO_MEDIDO
    codigo, dito = resposta
    if codigo == SAIDA_DO_INSTRUMENTO_NAO_MEDIDO:
        RAZAO_DE_NAO_MEDIR.append(MOTIVO_O_INSTRUMENTO_DISSE)
        return NAO_MEDIDO
    if codigo == 0:
        return ""
    return dito


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


def repositorio_das_issues(raiz: Path) -> str:
    try:
        dado = json.loads((raiz / ARQUIVO_EXECUTOR).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    issues = dado.get(CHAVE_DAS_ISSUES) if isinstance(dado, dict) else None
    if not isinstance(issues, dict):
        return ""
    onde = issues.get(CHAVE_DO_REPOSITORIO)
    return onde.strip() if isinstance(onde, str) else ""


def numero_da_issue_do_trabalho(raiz: Path, branch: str, principal: str):
    achou = MARCA_DA_ISSUE_NA_BRANCH.search(branch or "")
    if achou:
        return achou.group(1)
    if not principal:
        return ""
    comando = [parte.format(principal) for parte in COMANDO_DAS_MENSAGENS]
    resposta = responde(comando, raiz, TEMPO_DO_GIT)
    if resposta is NAO_MEDIDO or resposta[0] != 0:
        return ""
    numeros = MARCA_DA_ISSUE_NO_COMMIT.findall(resposta[1] or "")
    return numeros[0] if numeros else ""


def criterios_do_que_o_gh_respondeu(resposta):
    if resposta is NAO_MEDIDO or resposta[0] != 0:
        return NAO_MEDIDO
    try:
        dado = json.loads(resposta[1] or "{}")
    except ValueError:
        return NAO_MEDIDO
    if not isinstance(dado, dict) or dado.get(CAMPO_DA_SITUACAO) is None:
        return NAO_MEDIDO
    corpo = dado.get(CAMPO_DO_CORPO) or ""
    linhas = [l.strip() for l in corpo.splitlines()]
    return {
        "aberta": dado.get(CAMPO_DA_SITUACAO) == SITUACAO_ABERTA,
        "em_branco": [l for l in linhas if l.startswith(CAIXA_EM_BRANCO)],
        "marcados": len([l for l in linhas
                         if l.startswith(CAIXA_MARCADA)]),
    }


def criterios_da_issue(raiz: Path, numero: str, onde: str):
    comando = [parte.format(numero, onde)
               for parte in COMANDO_DO_CORPO_DA_ISSUE]
    return criterios_do_que_o_gh_respondeu(
        responde(comando, raiz, TEMPO_DA_REDE))


def criterio_do_trabalho(raiz: Path, branch: str, principal: str,
                         entregue: bool):
    if not entregue:
        return {}
    onde = repositorio_das_issues(raiz)
    numero = numero_da_issue_do_trabalho(raiz, branch, principal)
    if not onde or not numero:
        return {}
    lido = criterios_da_issue(raiz, numero, onde)
    if lido is NAO_MEDIDO:
        return {"issue": numero, "onde": onde, "criterios": NAO_MEDIDO}
    return {"issue": numero, "onde": onde, "criterios": lido}


def pedidos_abertos(raiz: Path, principal: str, integracao: str):
    comando = [parte.format(principal, integracao)
               for parte in COMANDO_DO_PEDIDO_ABERTO]
    resposta = responde(comando, raiz, TEMPO_DA_REDE)
    if resposta is NAO_MEDIDO or resposta[0] != 0:
        return NAO_MEDIDO
    try:
        pedidos = json.loads(resposta[1] or "[]")
    except ValueError:
        return NAO_MEDIDO
    return pedidos if isinstance(pedidos, list) else NAO_MEDIDO


def ha_pedido_de_incorporacao_aberto(pedidos):
    return NAO_MEDIDO if pedidos is NAO_MEDIDO else bool(pedidos)


def revisor_deste_repositorio(raiz: Path) -> str:
    try:
        dado = json.loads((raiz / ARQUIVO_EXECUTOR).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    projetos = dado.get(CHAVE_DOS_PROJETOS) if isinstance(dado, dict) else None
    if not isinstance(projetos, dict):
        return ""
    for projeto in projetos.values():
        if not isinstance(projeto, dict):
            continue
        if projeto.get(CHAVE_DO_REPOSITORIO) in (ESTE_REPOSITORIO, raiz.name):
            nome = projeto.get(CHAVE_DO_REVISOR)
            return nome.strip() if isinstance(nome, str) else ""
    return ""


def quem_esta_no_pedido(pedido: dict) -> set:
    nomes = set()
    for solicitado in pedido.get(CAMPO_DOS_SOLICITADOS) or []:
        if isinstance(solicitado, dict):
            nomes.add(solicitado.get("login") or solicitado.get("slug") or "")
    for revisao in pedido.get(CAMPO_DAS_REVISOES) or []:
        if isinstance(revisao, dict):
            nomes.add((revisao.get("author") or {}).get("login") or "")
    return {nome.lower() for nome in nomes if nome}


def o_revisor_e_o_autor(pedidos, revisor: str) -> bool:
    if pedidos is NAO_MEDIDO or not pedidos or not revisor:
        return False
    autores = {(pedido.get(CAMPO_DO_AUTOR) or {}).get("login", "").lower()
               for pedido in pedidos if isinstance(pedido, dict)}
    autores.discard("")
    return bool(autores) and autores == {revisor.lower()}


def revisao_do_pedido(pedidos, revisor: str):
    if pedidos is NAO_MEDIDO or not pedidos or not revisor:
        return NAO_MEDIDO
    medidos = [pedido for pedido in pedidos if isinstance(pedido, dict)
               and (CAMPO_DOS_SOLICITADOS in pedido
                    or CAMPO_DAS_REVISOES in pedido)]
    if not medidos:
        return NAO_MEDIDO
    return any(revisor.lower() in quem_esta_no_pedido(pedido)
               for pedido in medidos)


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
                          adiante: list, pedidos):
    aberto = ha_pedido_de_incorporacao_aberto(pedidos)
    if aberto is True:
        return True
    if pedido_mesclado_que_ja_contem(raiz, principal, integracao, adiante):
        return True
    return aberto


def raiz_git_da_pasta(pasta: Path):
    while not pasta.is_dir():
        if pasta.parent == pasta:
            return None
        pasta = pasta.parent
    resposta = responde(COMANDO_DA_RAIZ_DO_REPOSITORIO, pasta, TEMPO_DO_GIT)
    if resposta is NAO_MEDIDO or resposta[0] != 0 or not resposta[1]:
        return None
    return Path(resposta[1]).resolve()


def repositorios_tocados(escritos: set, raiz: Path) -> list:
    principal = raiz.resolve()
    pastas = {(raiz / caminho).parent for caminho in escritos}
    raizes = {achada for achada in map(raiz_git_da_pasta, pastas)
              if achada and achada != principal}
    return sorted(raizes)


def push_autorizado(projeto: dict, vizinho: Path) -> bool:
    do_projeto = projeto.get(CHAVE_DAS_AUTORIZACOES)
    if isinstance(do_projeto, dict) and CHAVE_DO_PUSH in do_projeto:
        return bool(do_projeto[CHAVE_DO_PUSH])
    try:
        do_alvo = json.loads(
            (vizinho / ARQUIVO_CONFIGURACAO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    declarado = (do_alvo.get(CHAVE_DAS_AUTORIZACOES)
                 if isinstance(do_alvo, dict) else None)
    if not isinstance(declarado, dict):
        return False
    return bool(declarado.get(CHAVE_DO_PUSH))


def cadastro_do_vizinho(raiz: Path, vizinho: Path) -> dict:
    sem_cadastro = {"integracao": "", "somente_leitura": False,
                    "pode_empurrar": False}
    try:
        dado = json.loads((raiz / ARQUIVO_EXECUTOR).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return sem_cadastro
    if not isinstance(dado, dict):
        return sem_cadastro
    projetos = dado.get(CHAVE_DOS_PROJETOS)
    projeto = next((p for p in (projetos.values() if isinstance(projetos, dict) else [])
                    if isinstance(p, dict)
                    and p.get(CHAVE_DO_REPOSITORIO) == vizinho.name), None)
    if projeto is None:
        return sem_cadastro
    do_topo = dado.get(CHAVE_DAS_BRANCHES)
    do_projeto = projeto.get(CHAVE_DAS_BRANCHES)
    integracao = ((do_projeto.get(CHAVE_DA_INTEGRACAO)
                   if isinstance(do_projeto, dict) else None)
                  or (do_topo.get(CHAVE_DA_INTEGRACAO)
                      if isinstance(do_topo, dict) else None))
    return {"integracao": str(integracao).strip() if integracao else "",
            "somente_leitura": bool(projeto.get(CHAVE_DO_SOMENTE_LEITURA)),
            "pode_empurrar": push_autorizado(projeto, vizinho)}


SEM_A_INTEGRACAO = "sem-a-integracao"


def integracao_existe_no_vizinho(vizinho: Path, integracao: str):
    resposta = responde(
        [parte.format(integracao) for parte in COMANDO_DA_INTEGRACAO_NO_REMOTO],
        vizinho, TEMPO_DA_REDE)
    if resposta is NAO_MEDIDO or resposta[0] != 0:
        return NAO_MEDIDO
    return bool(resposta[1].strip())


def commits_fora_da_integracao(vizinho: Path, integracao: str):
    if not integracao:
        return []
    existe = integracao_existe_no_vizinho(vizinho, integracao)
    if existe is NAO_MEDIDO:
        return NAO_MEDIDO
    if not existe:
        return SEM_A_INTEGRACAO
    responde([parte.format(integracao) for parte in COMANDO_DE_BUSCA_DA_INTEGRACAO],
             vizinho, TEMPO_DA_REDE)
    espelho = ESPELHO_NO_REMOTO.format(integracao)
    resposta = responde(
        [parte.format(espelho) for parte in COMANDO_DO_QUE_A_INTEGRACAO_NAO_TEM],
        vizinho, TEMPO_DO_GIT)
    if resposta is NAO_MEDIDO or resposta[0] != 0:
        return NAO_MEDIDO
    return [l for l in resposta[1].split("\n") if l.strip()]


def medir_vizinho(vizinho: Path, abertura, raiz: Path) -> dict:
    suja, _ = sujeira_desta_sessao_e_herdada(vizinho, abertura)
    resposta = responde(COMANDO_DO_QUE_NAO_ESTA_EM_REMOTO_NENHUM, vizinho,
                        TEMPO_DO_GIT)
    if resposta is NAO_MEDIDO or resposta[0] != 0:
        sem_remoto = NAO_MEDIDO
    else:
        sem_remoto = [l for l in resposta[1].split("\n") if l.strip()]
    cadastro = cadastro_do_vizinho(raiz, vizinho)
    branch = resposta_limpa(COMANDO_DA_BRANCH_DA_ARVORE, vizinho, TEMPO_DO_GIT)
    integracao = cadastro["integracao"]
    fora = ([] if not integracao or branch == integracao
            else commits_fora_da_integracao(vizinho, integracao))
    pedido = NAO_MEDIDO
    if cadastro["somente_leitura"] and isinstance(fora, list) and fora:
        pedido = ha_pedido_de_incorporacao_aberto(
            pedidos_abertos(vizinho, integracao, branch))
    return {"raiz": str(vizinho), "suja": suja, "sem_remoto": sem_remoto,
            "branch": branch, "integracao": integracao,
            "somente_leitura": cadastro["somente_leitura"],
            "pode_empurrar": cadastro["pode_empurrar"],
            "fora_da_integracao": fora, "pedido": pedido}


def nada_a_entregar(medido: dict) -> bool:
    return not medido["suja"] and medido["sem_remoto"] == []


def vizinho_sem_destino(medido: dict) -> bool:
    if medido["suja"] or medido["sem_remoto"] is NAO_MEDIDO or medido["sem_remoto"]:
        return True
    fora = medido.get("fora_da_integracao")
    if fora == SEM_A_INTEGRACAO and medido.get("somente_leitura") \
            and nada_a_entregar(medido):
        return False
    if fora is NAO_MEDIDO or fora == SEM_A_INTEGRACAO:
        return True
    if not fora:
        return False
    return not (medido.get("somente_leitura") and medido.get("pedido") is True)


def vizinhos_sem_destino(raiz: Path, abertura, entrada) -> list:
    if not isinstance(entrada, dict):
        return []
    escritos = arquivos_que_esta_sessao_escreveu(
        entrada.get(CHAVE_DO_TRANSCRITO), raiz)
    medidos = [medir_vizinho(vizinho, abertura, raiz)
               for vizinho in repositorios_tocados(escritos, raiz)]
    return [m for m in medidos if vizinho_sem_destino(m)]


def medir(raiz: Path, abertura=None, entrada=None) -> dict:
    suja, herdada = sujeira_desta_sessao_e_herdada(raiz, abertura, entrada)
    nao_julgada = linhas_que_a_camada_nao_julga(raiz)
    vizinhos = vizinhos_sem_destino(raiz, abertura, entrada)
    etapa = etapa_em_curso()
    if etapa:
        branch = resposta_limpa(COMANDO_DA_BRANCH_DA_ARVORE, raiz, TEMPO_DO_GIT)
        return {
            "etapa": etapa,
            "suja": suja,
            "herdada": herdada,
            "nao_julgada": nao_julgada,
            "vizinhos": vizinhos,
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
            "nao_julgada": nao_julgada, "vizinhos": vizinhos,
            "sobra": sobra_fora_da_branch_de_entrega(raiz),
            "principal": principal, "integracao": integracao,
            "adiante": NAO_MEDIDO, "herdados": [], "pedido": NAO_MEDIDO,
        }
    desta = (commits_desta_sessao(raiz, principal, integracao, abertura, tudo)
             if tudo else [])
    do_criterio = criterio_do_trabalho(
        raiz, resposta_limpa(COMANDO_DA_BRANCH_DA_ARVORE, raiz, TEMPO_DO_GIT),
        principal, bool(desta))
    pedidos = (pedidos_abertos(raiz, principal, integracao)
               if tudo else NAO_MEDIDO)
    revisor = revisor_deste_repositorio(raiz)
    pedido_aberto = ha_pedido_de_incorporacao_aberto(pedidos) is True
    return {
        "etapa": "",
        "suja": suja,
        "herdada": herdada,
        "nao_julgada": nao_julgada,
        "vizinhos": vizinhos,
        "sobra": sobra_fora_da_branch_de_entrega(raiz),
        "principal": principal,
        "integracao": integracao,
        "adiante": desta,
        "criterio": do_criterio,
        "herdados": [l for l in tudo if l not in desta],
        "pedido": (_ha_destino_declarado(raiz, principal, integracao, tudo,
                                         pedidos)
                   if tudo else NAO_MEDIDO),
        "pedido_aberto": pedido_aberto,
        "revisor": revisor,
        "revisao": (revisao_do_pedido(pedidos, revisor)
                    if pedido_aberto and revisor else NAO_MEDIDO),
        "revisor_e_o_autor": o_revisor_e_o_autor(pedidos, revisor),
    }


def primeiras_linhas(linhas: list) -> str:
    return "\n".join(f"  {l}" for l in linhas[:TETO_DE_LINHAS])


def linhas_do_vizinho(vizinho: dict) -> list:
    linhas = []
    if vizinho["suja"]:
        linhas.append(LINHA_DO_VIZINHO_SUJO.format(
            len(vizinho["suja"]), primeiras_linhas(vizinho["suja"])))
    if vizinho["sem_remoto"] is NAO_MEDIDO:
        linhas.append(LINHA_DO_VIZINHO_NAO_MEDIDO)
    elif vizinho["sem_remoto"]:
        linhas.append(LINHA_DO_VIZINHO_SEM_REMOTO.format(
            len(vizinho["sem_remoto"]),
            primeiras_linhas(vizinho["sem_remoto"])))
    fora = vizinho.get("fora_da_integracao")
    integracao = vizinho.get("integracao") or ""
    espelho = ESPELHO_NO_REMOTO.format(integracao)
    branch = vizinho.get("branch")
    if fora is NAO_MEDIDO:
        linhas.append(LINHA_DO_VIZINHO_INTEGRACAO_NAO_MEDIDA.format(integracao))
    elif fora == SEM_A_INTEGRACAO:
        linhas.append(LINHA_DO_VIZINHO_SEM_A_INTEGRACAO.format(integracao))
    elif not fora:
        pass
    elif not vizinho.get("somente_leitura"):
        molde = (LINHA_DO_VIZINHO_FORA_DA_INTEGRACAO
                 if vizinho.get("pode_empurrar") else LINHA_DO_VIZINHO_SEM_PUSH)
        linhas.append(molde.format(
            len(fora), branch, espelho, primeiras_linhas(fora),
            vizinho.get("raiz"), integracao))
    elif vizinho.get("pedido") is NAO_MEDIDO:
        linhas.append(LINHA_DO_VIZINHO_PEDIDO_NAO_MEDIDO.format(
            len(fora), branch, espelho, integracao))
    elif vizinho.get("pedido") is False:
        linhas.append(LINHA_DO_VIZINHO_SEM_PEDIDO.format(
            len(fora), branch, espelho, integracao, primeiras_linhas(fora)))
    return linhas


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
    for vizinho in estado.get("vizinhos") or []:
        cobradas.append(COBRA_VIZINHO_SEM_DESTINO.format(
            vizinho["raiz"], "\n".join(linhas_do_vizinho(vizinho))))
    if estado.get("etapa"):
        if estado.get("duravel") is NAO_MEDIDO:
            cobradas.append(COBRA_DURAVEL_NAO_MEDIDO.format(
                estado.get("branch")))
        elif not estado["duravel"]:
            cobradas.append(COBRA_FORA_DO_REPOSITORIO_DURAVEL.format(
                estado.get("branch")))
        return cobradas
    if estado.get("sobra", "") is NAO_MEDIDO:
        cobradas.append(COBRA_SOBRA_NAO_MEDIDO.format(
            INSTRUMENTO_DA_ENTREGA, BANDEIRA_DA_ENTREGA, porque_nao_mediu()))
    elif estado.get("sobra"):
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
        elif (estado.get("pedido_aberto") and estado.get("revisor")
                and not estado.get("revisor_e_o_autor")):
            if estado.get("revisao") is False:
                cobradas.append(COBRA_PEDIDO_SEM_REVISOR.format(
                    estado.get("integracao"), estado.get("principal"),
                    estado.get("revisor")))
            elif estado.get("revisao") is NAO_MEDIDO:
                cobradas.append(COBRA_REVISAO_NAO_MEDIDA.format(
                    estado.get("integracao"), estado.get("principal"),
                    estado.get("revisor")))
    cobradas += cobranca_do_criterio(estado)
    return cobradas


def cobranca_do_criterio(estado: dict) -> list:
    do_criterio = estado.get("criterio") or {}
    if "criterios" not in do_criterio:
        return []
    lido = do_criterio["criterios"]
    if lido is NAO_MEDIDO:
        return [COBRA_CRITERIO_NAO_MEDIDO.format(
            do_criterio["issue"], porque_nao_mediu(), do_criterio["issue"],
            do_criterio["onde"])]
    if not lido.get("em_branco"):
        return []
    return [COBRA_CRITERIO_EM_BRANCO.format(
        do_criterio["issue"], len(lido["em_branco"]),
        estado.get("integracao"),
        primeiras_linhas(lido["em_branco"][:TETO_DE_CRITERIOS_MOSTRADOS]))]


def relato(estado: dict) -> list:
    dito = []
    if estado.get("pedido_aberto") and estado.get("revisor_e_o_autor"):
        dito.append(RELATA_REVISOR_QUE_E_O_AUTOR.format(
            estado.get("revisor")))
    do_criterio = estado.get("criterio") or {}
    lido = do_criterio.get("criterios")
    if isinstance(lido, dict) and lido.get("marcados") \
            and not lido.get("em_branco"):
        dito.append(RELATA_CRITERIO_CUMPRIDO.format(
            do_criterio["issue"], lido["marcados"]))
    herdados = estado.get("herdados")
    if herdados and estado.get("pedido") is not True:
        dito.append(RELATA_HERDADO.format(
            estado.get("integracao"), len(herdados), estado.get("principal"),
            primeiras_linhas(herdados)))
    return dito


def o_modo_esta_posto(ambiente) -> bool:
    return bool((ambiente or {}).get(MARCA_NO_AMBIENTE))


def decisao(entrada: dict, raiz: Path, ambiente=None):
    if entrada.get("stop_hook_active"):
        return "", ""
    if o_modo_esta_posto(os.environ if ambiente is None else ambiente):
        return "", DITO_DA_SESSAO_DE_PESQUISA.format(MARCA_NO_AMBIENTE)
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
    ("pedido aberto sem o revisor configurado solicitado",
     com(adiante=["abc1234 trabalho"], pedido=True, pedido_aberto=True,
         revisor="conta-x", revisao=False)),
    ("pedido aberto com revisor configurado e a revisão nem medida",
     com(adiante=["abc1234 trabalho"], pedido=True, pedido_aberto=True,
         revisor="conta-x", revisao=NAO_MEDIDO)),
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

    "O pedido de incorporação de 'homolog' para 'main' está aberto, mas o "
    "revisor configurado 'conta-x' não foi solicitado nem revisou "
    "(`gh pr list --base main --head homolog --json "
    "reviewRequests,latestReviews`).\n"
    "Pedido sem revisor pedido é entrega parada na mesa de ninguém: solicite "
    "com `gh api -X POST repos/{owner}/{repo}/pulls/<n>/requested_reviewers "
    "-f \"reviewers[]=conta-x\"` (o `gh pr edit --add-reviewer` tropeça em "
    "repositório com projetos clássicos), ou diga em uma linha por que fica "
    "assim.",

    "O pedido de incorporação de 'homolog' para 'main' está aberto e há "
    "revisor configurado ('conta-x'), mas não deu para medir se ele foi "
    "solicitado — o `gh` não devolveu os campos de revisão. Sem a medição "
    "isto é 'não medido', nunca 'solicitado': confira à mão antes de "
    "encerrar.",
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
    ("pedido aberto e o revisor configurado já solicitado ou já revisou",
     com(adiante=["abc1234 trabalho"], pedido=True, pedido_aberto=True,
         revisor="conta-x", revisao=True)),
    ("pedido aberto sem revisor configurado: ambiente que não cobra revisão",
     com(adiante=["abc1234 trabalho"], pedido=True, pedido_aberto=True,
         revisor="", revisao=False)),
    ("destino por pedido já mesclado, sem pedido aberto: nada de revisão a "
     "cobrar", com(adiante=["abc1234 trabalho"], pedido=True,
                   pedido_aberto=False, revisor="conta-x",
                   revisao=NAO_MEDIDO)),
]

MARCA_DA_SUJEIRA = "?? "
ARQUIVO_DE_MENTIRA = "solto.txt"
FEITO_DE_MENTIRA = "feito.txt"
ORIGEM_DE_MENTIRA = "origem"
TRABALHO_DE_MENTIRA = "arvore"
BRANCH_DE_MENTIRA = "issue/999-prova"
ENTRADA_DE_PARADA = "{}"
INSTRUMENTO_DE_MENTIRA_QUE_ACUSA = """import sys
sys.stdout.write(" ".join(sys.argv))
sys.exit(1)
"""
INSTRUMENTO_DE_MENTIRA_CALADO = """import sys
sys.exit(0)
"""
INSTRUMENTO_DE_MENTIRA_QUE_NAO_MEDIU = """import sys
sys.stdout.write("Branch entregue por podar: NAO MEDIDO")
sys.exit(2)
"""


def git_de_mentira(arvore: Path, *argumentos) -> None:
    subprocess.run(["git", *argumentos], cwd=arvore, check=True,
                   capture_output=True)


def trabalho_de_mentira_com_repositorio_duravel(pasta: Path) -> Path:
    origem, arvore = pasta / ORIGEM_DE_MENTIRA, pasta / TRABALHO_DE_MENTIRA
    origem.mkdir()
    arvore.mkdir()
    git_de_mentira(origem, "init", "-q", "--bare")
    git_de_mentira(origem, "config", "core.longpaths", "true")
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
        input=ENTRADA_DE_PARADA, capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=ambiente)
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
    lar_de_prova = Path("Z:/lar") if os.sep == "\\" else Path("/lar")
    calculada = pasta_dos_transcritos(Path("D:/um/dois"), lar_de_prova)
    caso("a pasta de transcritos troca dois-pontos E separador por hifen, "
         "como a ferramenta grava — o nome esperado e literal, para o caso "
         "nao concordar com o defeito que ele deveria pegar",
         calculada.name == "D--um-dois")
    caso("a pasta de transcritos nasce sob o lar: com a letra de drive "
         "colada o pathlib a trataria como relativa e descartaria o lar",
         calculada.parent == lar_de_prova / PASTA_DOS_TRANSCRITOS)
    caso("o ponto do caminho tambem vira hifen — medido numa arvore de "
         "trabalho sob pasta oculta, que a ferramenta gravou com hifen "
         "no lugar do ponto",
         pasta_dos_transcritos(Path("D:/um/.dois"),
                               lar_de_prova).name == "D--um--dois")
    with tempfile.TemporaryDirectory(prefix="cobra-vizinha-") as pasta:
        base = Path(pasta)
        raiz_falsa = Path("Z:/repo") if os.sep == "\\" else Path("/repo")
        lar = base / "lar"
        transcritos = pasta_dos_transcritos(raiz_falsa, lar)
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
    with tempfile.TemporaryDirectory(prefix="cobrar-destino-duble-") as tmp:
        duble = Path(tmp).resolve()
        instrumento = duble / INSTRUMENTO_DA_ENTREGA
        instrumento.parent.mkdir(parents=True, exist_ok=True)
        instrumento.write_text(INSTRUMENTO_DE_MENTIRA_QUE_ACUSA,
                               encoding="utf-8")
        caso("a segunda condição chama o instrumento no caminho e com a "
             "bandeira declarados, e devolve o texto dele",
             sobra_fora_da_branch_de_entrega(duble)
             == f"{INSTRUMENTO_DA_ENTREGA} {BANDEIRA_DA_ENTREGA}")
        instrumento.write_text(INSTRUMENTO_DE_MENTIRA_CALADO,
                               encoding="utf-8")
        caso("instrumento que sai zero não vira cobrança",
             sobra_fora_da_branch_de_entrega(duble) == "")
        instrumento.write_text(INSTRUMENTO_DE_MENTIRA_QUE_NAO_MEDIU,
                               encoding="utf-8")
        caso("instrumento que sai pelo código de NÃO MEDIDO não vira texto "
             "de acusação — antes qualquer saída diferente de zero virava "
             "commit fora da branch",
             sobra_fora_da_branch_de_entrega(duble) is NAO_MEDIDO)
        instrumento.unlink()
        caso("sem o instrumento no disco a segunda condição cala, em vez "
             "de estourar",
             sobra_fora_da_branch_de_entrega(duble) == "")

    nao_medida = "".join(cobrancas(com(sobra=NAO_MEDIDO)))
    caso("sobra não medida cobra dizendo que NÃO MEDIU, e não acusa commit "
         "que ninguém viu",
         "não medido" in nao_medida
         and COBRA_SOBRA_DA_BRANCH[:24] not in nao_medida)
    RAZAO_DE_NAO_MEDIR.clear()
    caso("sem razão registrada a cobrança confessa que não sabe a causa, "
         "em vez de calar sobre ela",
         MOTIVO_NAO_DITO in "".join(cobrancas(com(sobra=NAO_MEDIDO))))
    RAZAO_DE_NAO_MEDIR.append(MOTIVO_TEMPO_ESGOTADO.format(15))
    caso("teto de tempo esgotado aparece na cobrança com o número do teto — "
         "medido: rede lenta e instrumento quebrado davam a MESMA cobrança "
         "muda, e a causa levou um dia para aparecer",
         "15 s" in "".join(cobrancas(com(sobra=NAO_MEDIDO))))
    RAZAO_DE_NAO_MEDIR.clear()
    caso("parada que já é laço de gancho cala",
         decisao({"stop_hook_active": True}, daqui) == ("", ""))
    montado = [parte.format("principal-x", "integracao-y")
               for parte in COMANDO_DO_PEDIDO_ABERTO]
    caso("a consulta do pedido pergunta pela integração, não pela principal "
         "duas vezes",
         montado[montado.index("--base") + 1] == "principal-x"
         and montado[montado.index("--head") + 1] == "integracao-y")
    solicitado = [{"number": 1,
                   "reviewRequests": [{"__typename": "User",
                                       "login": "Conta-X"}],
                   "latestReviews": []}]
    revisado = [{"number": 1, "reviewRequests": [],
                 "latestReviews": [{"author": {"login": "conta-x"},
                                    "state": "APPROVED"}]}]
    ninguem = [{"number": 1, "reviewRequests": [], "latestReviews": []}]
    caso("revisor solicitado conta como revisão pedida, sem olhar maiúscula",
         revisao_do_pedido(solicitado, "conta-x") is True)
    caso("revisor que já revisou conta mesmo depois de a solicitação sumir",
         revisao_do_pedido(revisado, "conta-x") is True)
    caso("pedido aberto sem o revisor em lugar nenhum é revisão não pedida",
         revisao_do_pedido(ninguem, "conta-x") is False)
    caso("gh que não devolve os campos de revisão é não medido, nunca falso",
         revisao_do_pedido([{"number": 1}], "conta-x") is NAO_MEDIDO)
    caso("time solicitado como revisor é reconhecido pelo slug",
         revisao_do_pedido([{"number": 1, "reviewRequests": [
             {"__typename": "Team", "slug": "conta-x"}]}], "conta-x") is True)
    caso("sem pedido aberto ou sem revisor não há o que medir",
         revisao_do_pedido([], "conta-x") is NAO_MEDIDO
         and revisao_do_pedido(ninguem, "") is NAO_MEDIDO)
    do_proprio_autor = [{"number": 1, "author": {"login": "Conta-X"},
                         "reviewRequests": [], "latestReviews": []}]
    de_outro = [{"number": 1, "author": {"login": "outra-conta"},
                 "reviewRequests": [], "latestReviews": []}]
    caso("quando o revisor configurado é quem abriu o pedido, o gancho sabe "
         "— o GitHub recusa pedir revisão ao autor com 422, e cobrar o "
         "impossível a cada parada ensina a ignorar a cobrança inteira",
         o_revisor_e_o_autor(do_proprio_autor, "conta-x") is True)
    caso("pedido aberto por outra conta continua cobrando revisor",
         o_revisor_e_o_autor(de_outro, "conta-x") is False)
    caso("sem o campo do autor não se inventa isenção — gh que não devolve "
         "o autor deixa a cobrança de pé",
         o_revisor_e_o_autor(ninguem, "conta-x") is False)
    caso("basta um pedido de outra conta para a isenção cair",
         o_revisor_e_o_autor(do_proprio_autor + de_outro, "conta-x") is False)
    caso("a cobrança de revisor CALA quando o autor é o revisor, e o motivo "
         "fica dito no relato em vez de sumir calado",
         not any("revisor configurado" in linha and "não foi solicitado"
                 in linha
                 for linha in cobrancas({"adiante": ["a"], "pedido": True,
                                         "pedido_aberto": True,
                                         "revisor": "conta-x",
                                         "revisao": False,
                                         "revisor_e_o_autor": True}))
         and any("422" in linha
                 for linha in relato({"pedido_aberto": True,
                                      "revisor": "conta-x",
                                      "revisor_e_o_autor": True})))
    caso("pedido aberto é o que a lista do gh traz; lista vazia é não",
         ha_pedido_de_incorporacao_aberto(ninguem) is True
         and ha_pedido_de_incorporacao_aberto([]) is False
         and ha_pedido_de_incorporacao_aberto(NAO_MEDIDO) is NAO_MEDIDO)
    with tempfile.TemporaryDirectory(prefix="cobrar-destino-revisor-") as tmp:
        raiz_com_revisor = Path(tmp)
        caso("sem configuração local, não há revisor e a cobrança cala",
             revisor_deste_repositorio(raiz_com_revisor) == "")
        (raiz_com_revisor / ARQUIVO_CONFIGURACAO).parent.mkdir(parents=True)
        (raiz_com_revisor / ARQUIVO_EXECUTOR).write_text(json.dumps({
            "projetos": {"vizinho": {"repositorio": "outro",
                                     "revisor": "conta-do-vizinho"},
                         "eu": {"repositorio": ".", "revisor": " conta-x "}}}),
            encoding="utf-8")
        caso("o revisor vem do projeto que é este repositório, não do vizinho",
             revisor_deste_repositorio(raiz_com_revisor) == "conta-x")
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
        git_de_mentira(origem, "config", "core.longpaths", "true")
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

    limpo_e_somente_leitura = {
        "raiz": "projetos/vizinho", "suja": [], "sem_remoto": [],
        "branch": "main", "integracao": "homolog", "somente_leitura": True,
        "pode_empurrar": False, "fora_da_integracao": SEM_A_INTEGRACAO,
        "pedido": NAO_MEDIDO,
    }
    caso("vizinho SOMENTE LEITURA, com árvore limpa e nada por empurrar, não "
         "é cobrado por não ter a integração declarada: não há o que "
         "entregar, e o nome de uma branch onde nunca se escreve não é "
         "pendência — cobrança impossível de resolver ensina a ignorar a "
         "cobrança inteira",
         vizinho_sem_destino(limpo_e_somente_leitura) is False)
    caso("mas o mesmo vizinho COM árvore suja continua cobrado",
         vizinho_sem_destino(dict(limpo_e_somente_leitura,
                                  suja=[" M x.py"])) is True)
    caso("e com commit que não está em remoto nenhum, também",
         vizinho_sem_destino(dict(limpo_e_somente_leitura,
                                  sem_remoto=["abc1234 solto"])) is True)
    caso("vizinho onde SE ESCREVE segue cobrado pela integração que falta — "
         "ali o nome importa, porque é para lá que a entrega vai",
         vizinho_sem_destino(dict(limpo_e_somente_leitura,
                                  somente_leitura=False)) is True)

    with tempfile.TemporaryDirectory(prefix="cobrar-destino-arvore-") as tmp:
        base = Path(tmp).resolve()
        principal, ao_lado = base / "principal", base / "ao-lado"
        principal.mkdir()
        git_de_mentira(principal, "init", "-q", "-b", "main")
        git_de_mentira(principal, "config", "user.email", "prova@exemplo")
        git_de_mentira(principal, "config", "user.name", "Prova")
        (principal / "a.txt").write_text("um", encoding="utf-8")
        git_de_mentira(principal, "add", "-A")
        git_de_mentira(principal, "commit", "-qm", "raiz")
        git_de_mentira(principal, "worktree", "add", "-q", str(ao_lado),
                       "-b", "issue/914-medido-de-dentro")
        caso("a bancada monta uma ÁRVORE DE TRABALHO de verdade, onde o .git "
             "é ARQUIVO e não pasta — a casa roda com várias, e nenhuma "
             "fixture exercitava esse terreno",
             (ao_lado / ".git").is_file()
             and not (ao_lado / ".git").is_dir())
        (ao_lado / "b.txt").write_text("dois", encoding="utf-8")
        git_de_mentira(ao_lado, "add", "-A")
        git_de_mentira(ao_lado, "commit", "-qm", "de dentro da árvore")
        (ao_lado / "sujo.txt").write_text("nao commitado", encoding="utf-8")
        minha, herdada = sujeira_desta_sessao_e_herdada(ao_lado, None)
        caso("medida de dentro da árvore de trabalho, a sujeira é a DELA — o "
             "git responde pela árvore em que o comando roda",
             any("sujo.txt" in linha for linha in minha) and herdada == [])
        caso("o número da issue sai do nome da branch da árvore de trabalho, "
             "não da branch da árvore principal",
             numero_da_issue_do_trabalho(
                 ao_lado, "issue/914-medido-de-dentro", "main") == "914")
        caso("e a árvore principal continua limpa e na branch dela: uma "
             "árvore não vê a sujeira da outra",
             sujeira_desta_sessao_e_herdada(principal, None) == ([], []))

    with tempfile.TemporaryDirectory(prefix="cobrar-destino-criterio-") as tmp:
        arvore = Path(tmp).resolve()
        git_de_mentira(arvore, "init", "-q", "-b", "main")
        git_de_mentira(arvore, "config", "user.email", "prova@exemplo")
        git_de_mentira(arvore, "config", "user.name", "Prova")
        git_de_mentira(arvore, "commit", "-q", "--allow-empty", "-m", "raiz")
        git_de_mentira(arvore, "checkout", "-q", "-b", "issue/142-o-assunto")
        caso("o número da issue sai do NOME da branch de trabalho",
             numero_da_issue_do_trabalho(arvore, "issue/142-o-assunto", "main")
             == "142")
        git_de_mentira(arvore, "checkout", "-q", "-b", "sem-numero-no-nome")
        git_de_mentira(arvore, "commit", "-q", "--allow-empty", "-m",
                       "O conserto que faltava (issue 77)")
        caso("sem número no nome da branch, ele sai da mensagem do commit — "
             "que é a convenção desta casa",
             numero_da_issue_do_trabalho(arvore, "sem-numero-no-nome", "main")
             == "77")
        caso("sem número em lugar nenhum, a cobrança não tem o que perguntar "
             "e CALA, em vez de chutar um número",
             numero_da_issue_do_trabalho(arvore, "outra-coisa", "") == "")

        (arvore / "nucleo").mkdir()
        (arvore / ARQUIVO_EXECUTOR).write_text(
            json.dumps({"issues": {"repositorio": "quem-instala/o-quadro"}}),
            encoding="utf-8")
        caso("o endereço do quadro sai do arquivo local, campo issues."
             "repositorio — nunca do remoto do repositório aberto",
             repositorio_das_issues(arvore) == "quem-instala/o-quadro")
        (arvore / ARQUIVO_EXECUTOR).write_text("{ isto nao e json",
                                               encoding="utf-8")
        caso("arquivo local ilegível não vira endereço inventado",
             repositorio_das_issues(arvore) == "")

    corpo_com_branco = ("## Pronto quando\n\n"
                        "- [x] o instrumento roda\n"
                        "- [ ] a bancada cobre o caso novo\n"
                        "- [ ] a receita cita o comando\n")
    corpo_marcado = ("## Pronto quando\n\n"
                     "- [x] o instrumento roda\n"
                     "- [X] a bancada cobre o caso novo\n")
    lido_com_branco = criterios_do_que_o_gh_respondeu(
        (0, json.dumps({"body": corpo_com_branco, "state": "OPEN"})))
    lido_marcado = criterios_do_que_o_gh_respondeu(
        (0, json.dumps({"body": corpo_marcado, "state": "OPEN"})))
    caso("a leitura conta caixa em branco e caixa marcada, e enxerga o x "
         "maiúsculo",
         lido_com_branco["em_branco"] and len(lido_com_branco["em_branco"]) == 2
         and lido_com_branco["marcados"] == 1
         and lido_marcado["em_branco"] == []
         and lido_marcado["marcados"] == 2)
    caso("issue que não se deixou ler é NÃO MEDIDO, nunca issue sem critério",
         criterios_do_que_o_gh_respondeu((1, "erro")) is NAO_MEDIDO
         and criterios_do_que_o_gh_respondeu((0, "isto nao e json"))
         is NAO_MEDIDO
         and criterios_do_que_o_gh_respondeu((0, "{}")) is NAO_MEDIDO
         and criterios_do_que_o_gh_respondeu(NAO_MEDIDO) is NAO_MEDIDO)

    def com_criterio(criterios):
        return {"integracao": "homolog", "adiante": ["abc1234 trabalho"],
                "criterio": {"issue": "142", "onde": "quem-instala/o-quadro",
                             "criterios": criterios}}

    cobradas = cobranca_do_criterio(com_criterio(lido_com_branco))
    caso("critério em branco com o trabalho entregue COBRA, diz quantos são e "
         "manda marcar com evidência ou dizer por que sai do escopo",
         len(cobradas) == 1 and "142" in cobradas[0]
         and "2 critério" in cobradas[0]
         and "a bancada cobre o caso novo" in cobradas[0])
    caso("a cobrança manda tirar o verbo que FECHA a issue do pedido de "
         "incorporação — é ali que o critério não conferido desaparece",
         "FECHA" in cobradas[0])
    caso("critério todo marcado não cobra nada",
         cobranca_do_criterio(com_criterio(lido_marcado)) == [])
    caso("critério todo marcado entra no RELATO, com a contagem",
         any("142" in linha and "2 critério" in linha
             for linha in relato(com_criterio(lido_marcado))))
    nao_medido = cobranca_do_criterio(com_criterio(NAO_MEDIDO))
    caso("issue ilegível COBRA dizendo que não conferiu, e não conferido não "
         "é cumprido — nem cala, nem inventa que está pronta",
         len(nao_medido) == 1 and "não se deixou ler" in nao_medido[0]
         and "gh issue view 142" in nao_medido[0])
    caso("sem issue no trabalho, a cobrança do critério cala",
         cobranca_do_criterio({"integracao": "homolog", "criterio": {}}) == []
         and cobranca_do_criterio({"integracao": "homolog"}) == [])
    caso("trabalho NÃO entregue não vai à rede nem cobra critério: a issue só "
         "se lê quando há commit da sessão na integração",
         criterio_do_trabalho(Path("."), "issue/1-x", "main", False) == {})

    with tempfile.TemporaryDirectory(prefix="cobrar-destino-porcelain-") as tmp:
        arvore = Path(tmp).resolve()
        git_de_mentira(arvore, "init", "-q")
        git_de_mentira(arvore, "config", "user.email", "prova@exemplo")
        git_de_mentira(arvore, "config", "user.name", "Prova")
        rastreado = arvore / "a.txt"
        rastreado.write_text("de antes", encoding="utf-8")
        git_de_mentira(arvore, "add", "-A")
        git_de_mentira(arvore, "commit", "-qm", "base")
        rastreado.write_text("mexido antes da sessão", encoding="utf-8")
        os.utime(rastreado, (1000, 1000))
        caso("a PRIMEIRA linha do porcelain guarda o espaço inicial — o strip "
             "da saída inteira o comia, ` M a.txt` virava `M a.txt`, o corte "
             "em [3:] perdia três letras do caminho e o stat não achava o "
             "arquivo",
             linhas_da_arvore_suja(arvore) == [" M a.txt"])
        caso("e o primeiro arquivo sujo, mais velho que a abertura, é herdado "
             "— antes era SEMPRE sujeira desta sessão, e o gancho mandava "
             "commitar ou apagar trabalho alheio",
             sujeira_desta_sessao_e_herdada(arvore, time.time() - 60)
             == ([], [" M a.txt"]))

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

    caso("sessão de pesquisa: com a marca no ambiente a cobrança CALA, "
         "porque não há destino em disco a cobrar",
         decisao({}, Path("."), {MARCA_NO_AMBIENTE: "1"})[0] == "")
    caso("e o silêncio vem explicado: a sessão é mandada para a issue",
         "ISSUE" in decisao({}, Path("."), {MARCA_NO_AMBIENTE: "1"})[1])
    caso("marca vazia não conta como posta, e a cobrança segue normal",
         not o_modo_esta_posto({MARCA_NO_AMBIENTE: ""}))
    caso("sem a marca, a árvore suja continua sendo cobrada",
         any("árvore está suja" in c for c in cobrancas(
             {**ARVORE_LIMPA, "suja": ["?? sujo.py"]})))

    with tempfile.TemporaryDirectory(prefix="cobrar-destino-vizinho-") as tmp:
        base = Path(tmp).resolve()
        principal, vizinho = base / "principal", base / "vizinho"
        for pasta in (principal, vizinho):
            pasta.mkdir()
            git_de_mentira(pasta, "init", "-q", "-b", "main")
            git_de_mentira(pasta, "config", "user.email", "prova@exemplo")
            git_de_mentira(pasta, "config", "user.name", "Prova")
        tocado = vizinho / FEITO_DE_MENTIRA
        tocado.write_text("feito no vizinho", encoding="utf-8")
        git_de_mentira(vizinho, "add", "-A")
        git_de_mentira(vizinho, "commit", "-qm", "trabalho no vizinho")
        transcrito = base / "sessao.jsonl"
        transcrito.write_text(json.dumps({"message": {"content": [
            {"type": "tool_use", "name": "Write",
             "input": {"file_path": str(tocado)}},
            {"type": "tool_use", "name": "Bash",
             "input": {"command": f"echo x > {base / 'fora-de-git.txt'}"}},
            {"type": "tool_use", "name": "Write",
             "input": {"file_path": str(principal / "meu.py")}}]}}) + "\n",
            encoding="utf-8")
        entrada_com_vizinho = {CHAVE_DA_SESSAO: "vizinha",
                               CHAVE_DO_TRANSCRITO: str(transcrito)}
        caso("os repositórios tocados nesta sessão saem do transcrito: o "
             "vizinho entra, a principal não, e caminho fora de git não estoura",
             repositorios_tocados(
                 arquivos_que_esta_sessao_escreveu(str(transcrito), principal),
                 principal) == [vizinho])
        cobradas = cobrancas(medir(principal, None, entrada_com_vizinho))
        caso("vizinho tocado nesta sessão com commit que não está em remoto "
             "nenhum é cobrado, pelo caminho dele",
             any(str(vizinho) in c and "remoto nenhum" in c for c in cobradas))
        origem = base / "origem"
        origem.mkdir()
        git_de_mentira(origem, "init", "-q", "--bare", "-b", "main")
        git_de_mentira(origem, "config", "core.longpaths", "true")
        git_de_mentira(vizinho, "remote", "add", "origin", str(origem))
        git_de_mentira(vizinho, "push", "-q", "-u", "origin", "main")
        caso("vizinho com tudo empurrado cala",
             not any(str(vizinho) in c for c in
                     cobrancas(medir(principal, None, entrada_com_vizinho))))
        tocado.write_text("mexido de novo", encoding="utf-8")
        caso("arquivo solto no vizinho também é cobrado, pelo caminho dele",
             any(str(vizinho) in c and "fora de commit" in c for c in
                 cobrancas(medir(principal, None, entrada_com_vizinho))))

        def o_que_cobra_do_vizinho():
            return [c for c in cobrancas(medir(principal, None, entrada_com_vizinho))
                    if str(vizinho) in c]

        def cadastrar(somente_leitura, integracao_do_projeto="homolog",
                      push=True):
            (principal / ARQUIVO_EXECUTOR).parent.mkdir(parents=True, exist_ok=True)
            projeto = {"repositorio": vizinho.name,
                       "somente_leitura": somente_leitura}
            if integracao_do_projeto:
                projeto["branches"] = {"integracao": integracao_do_projeto}
            if push is not None:
                projeto["autorizacoes"] = {"commit": True, "push": push}
            (principal / ARQUIVO_EXECUTOR).write_text(json.dumps({
                "branches": {"integracao": "develop"},
                "projetos": {"viz": projeto}}), encoding="utf-8")

        git_de_mentira(vizinho, "checkout", "-q", "--", FEITO_DE_MENTIRA)
        git_de_mentira(vizinho, "branch", "homolog")
        git_de_mentira(vizinho, "push", "-q", "origin", "homolog")
        git_de_mentira(vizinho, "checkout", "-q", "-b", BRANCH_DE_MENTIRA)
        git_de_mentira(vizinho, "commit", "-q", "--allow-empty", "-m", "na branch")
        git_de_mentira(vizinho, "push", "-q", "-u", "origin", BRANCH_DE_MENTIRA)
        caso("sem cadastro do vizinho, a branch empurrada cala: a camada não "
             "adivinha a integração de ninguém",
             o_que_cobra_do_vizinho() == [])
        cadastrar(False)
        caso("a integração do vizinho vem do cadastro do projeto; a do topo é reserva",
             cadastro_do_vizinho(principal, vizinho)["integracao"] == "homolog")
        cadastrar(False, integracao_do_projeto="")
        caso("projeto cadastrado sem branches herda a integração do topo",
             cadastro_do_vizinho(principal, vizinho)["integracao"] == "develop")
        cadastrar(False, push=None)
        caso("cadastro sem autorizações nega push, como manda a regra 9: "
             "omissão não é permissão",
             cadastro_do_vizinho(principal, vizinho)["pode_empurrar"] is False)
        cadastrar(False, push=False)
        caso("push negado no cadastro cobra avisando o dono, e NÃO manda "
             "mesclar onde a sessão não pode empurrar",
             any("NÃO autoriza push" in c and "MESCLA na integração" not in c
                 for c in o_que_cobra_do_vizinho()))
        cadastrar(False)
        caso("vizinho próprio com a branch de trabalho empurrada mas fora da "
             "integração do cadastro é cobrado: empurrar é sincronizar, "
             "entregar é mesclar — o caso de 07/09",
             any("MESCLA na integração" in c and BRANCH_DE_MENTIRA in c
                 for c in o_que_cobra_do_vizinho()))
        git_de_mentira(vizinho, "checkout", "-q", "homolog")
        git_de_mentira(vizinho, "merge", "-q", BRANCH_DE_MENTIRA)
        git_de_mentira(vizinho, "push", "-q", "origin", "homolog")
        git_de_mentira(vizinho, "checkout", "-q", BRANCH_DE_MENTIRA)
        caso("mesclado na integração e empurrado, o vizinho cala",
             o_que_cobra_do_vizinho() == [])
        git_de_mentira(vizinho, "commit", "-q", "--allow-empty", "-m", "mais")
        git_de_mentira(vizinho, "push", "-q", "origin", BRANCH_DE_MENTIRA)
        cadastrar(False, integracao_do_projeto="nao-existe-no-remoto")
        caso("integração declarada que não existe no remoto do vizinho manda "
             "declarar a certa no cadastro, e não vira 'entregue' nem "
             "'não medido'",
             any("NÃO" in c and "existe no remoto" in c
                 and "branches.integracao" in c
                 for c in o_que_cobra_do_vizinho()))
        cadastrar(True)

        def o_que_cobra_com_pedidos(pedidos):
            global pedidos_abertos
            guardada = pedidos_abertos
            pedidos_abertos = lambda *_: pedidos
            try:
                return o_que_cobra_do_vizinho()
            finally:
                pedidos_abertos = guardada

        caso("vizinho somente leitura fora da integração e sem pedido aberto é "
             "cobrado pelo pedido, não pela mescla",
             any("pedido de incorporação" in c and "MESCLA na integração" not in c
                 for c in o_que_cobra_com_pedidos([])))
        caso("vizinho somente leitura com pedido de incorporação aberto cala",
             o_que_cobra_com_pedidos([{"number": 1}]) == [])
        caso("gh mudo no vizinho somente leitura é não medido, nunca pedido aberto",
             any("não deu para medir" in c
                 for c in o_que_cobra_com_pedidos(NAO_MEDIDO)))

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
