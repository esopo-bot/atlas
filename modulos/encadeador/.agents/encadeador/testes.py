import contextlib
import io
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from encadeador import (
    _ambiente_com_a_conta,
    _conta_do_remoto,
    _com_a_conta_no_git,
    CHAVE_DO_AJUDANTE_DE_CREDENCIAL,
    ARQUIVO_EXECUTOR, CLAUDE_QUE_PARA_NA_METADE, ESPERA_MAXIMA_S,
    ESTE_INSTRUMENTO, EXIT_COMPLETA, EXIT_ERRO_DE_USO_OU_AMBIENTE,
    EXIT_PAROU_NUM_PARA, EXIT_TESTE_CAIU, FALHA_DE_COMPORTAMENTO,
    FALHA_DE_RECUSA_COM_EXIT, FALHA_DE_RECUSA_PELO_MOTIVO_ERRADO, FALHOU,
    FALHOU_QUANTOS, FANTOCHE_OK, FOLGA_DO_TETO, FONTE_DO_DUBLE_DO_GH,
    LIMITE_DO_STDERR_NA_FALHA, MARCA_DO_MOTOR, PEDIDO_DE_FECHO, Path,
    RETOMADAS, SITUACOES, SONO_DO_TESTE_DE_ORFAO, TEMPO_DO_DUBLE,
    TESTE_OK, TETO_CONFIGURACAO, TETO_CURTO_DO_TESTE, TETO_DO_DUBLE,
    _EM_CURSO, _bateu_no_teto, _bloco_de_onde_esta, _cli, _cli_evidencia,
    _cli_verificar, _comando_sessao, _espera_do_limite, _evidencia,
    _porque_morreu, _prompt_da_sessao, _resumo_do_evento, _roteiro,
    avisos_do_alvo, carregar_executor, foto_das_etapas, gravar_estado,
    ler_estado, resumo_da_etapa, sem_caminho_de_maquina, validar_roteiro)


RECUSA = [
    ("ciclo no grafo", {"etapas": [
        {"nome": "a", "tipo": "codigo", "comando": "true", "depende": ["b"]},
        {"nome": "b", "tipo": "codigo", "comando": "true", "depende": ["a"]}]},
     "ciclo"),
    ("dependência fantasma", {"etapas": [
        {"nome": "a", "tipo": "codigo", "comando": "true",
         "depende": ["nao-existe"]}]}, "não existe no roteiro"),
    ("nome de etapa fora do contrato", {"etapas": [
        {"nome": "Alfa", "tipo": "codigo", "comando": "true"}]}, "não casa"),
    ("nome duplicado", {"etapas": [
        {"nome": "a", "tipo": "codigo", "comando": "true"},
        {"nome": "a", "tipo": "codigo", "comando": "true"}]}, "duplicado"),
    ("tipo desconhecido", {"etapas": [
        {"nome": "a", "tipo": "magia"}]}, "tipo desconhecido"),
    ("codigo sem comando", {"etapas": [
        {"nome": "a", "tipo": "codigo"}]}, "exige o campo comando"),
    ("sessao sem prompt", {"etapas": [
        {"nome": "a", "tipo": "sessao"}]}, "exige o campo prompt"),
    ("aprovacao-manual sem aprovacao", {"etapas": [
        {"nome": "a", "tipo": "aprovacao-manual"}]},
     "exige o campo aprovacao"),
    ("teto zero", {"teto": 0, "etapas": [
        {"nome": "a", "tipo": "codigo", "comando": "true"}]}, "teto"),
    ("raiz que não é objeto", [1, 2], "raiz"),
    ("teto booleano (bool é int em Python)", {"teto": True, "etapas": [
        {"nome": "a", "tipo": "codigo", "comando": "true"}]}, "teto"),
    ("depende como texto solto", {"etapas": [
        {"nome": "a", "tipo": "codigo", "comando": "true",
         "depende": "a"}]}, "lista de nomes"),
    ("comando como lista (o shell rodaria só o primeiro)", {"etapas": [
        {"nome": "a", "tipo": "codigo",
         "comando": ["touch um", "touch dois"]}]}, "exige o campo comando"),
    ("tempo-limite não numérico", {"etapas": [
        {"nome": "a", "tipo": "codigo", "comando": "true",
         "tempo-limite": "muito"}]}, "tempo-limite"),
    ("typo de campo apaga dependência em silêncio", {"etapas": [
        {"nome": "a", "tipo": "codigo", "comando": "true"},
        {"nome": "b", "tipo": "codigo", "comando": "true",
         "dependee": ["a"]}]}, "campo desconhecido"),
    ("ligada como texto (string é sempre verdadeira)", {"etapas": [
        {"nome": "a", "tipo": "codigo", "comando": "true",
         "ligada": "false"}]}, "booleano"),
    ("campo desconhecido na raiz do roteiro", {"tetos": 3, "etapas": [
        {"nome": "a", "tipo": "codigo", "comando": "true"}]},
     "campo desconhecido"),
]


class Bancada:
    def __init__(self, pasta):
        self.pasta = pasta
        self.evidencias = str(Path(pasta) / "evidencias")
        self.resultados = []
        self.caixa = Path(pasta) / "caixa-do-gh"
        self.ambiente = dict(os.environ)

    def caso(self, rotulo, condicao) -> None:
        self.resultados.append((rotulo, bool(condicao)))

    def configurar(self, destino, **troca):
        dado = {
            "modo": "completo",
            "issues": {"repositorio": "dono/repo", "conta_gh": "conta"},
            "projeto": {"url": "https://exemplo.invalido/quadro"},
            "branches": {"padrao_de_trabalho": "trabalho/<n>",
                         "base": "base", "integracao": "integracao"},
            "diretorios_so_codigo": [], "existe_arquivo_limpeza": False,
        }
        dado.update(troca)
        alvo = Path(destino) / ARQUIVO_EXECUTOR
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(json.dumps(dado, ensure_ascii=False), encoding="utf-8")
        return alvo

    def forjar_o_dublê(self) -> None:
        self.caixa.mkdir(exist_ok=True)
        dublê = Path(self.pasta) / "gh-dublê.py"
        dublê.write_text(
            FONTE_DO_DUBLE_DO_GH.format(caixa=repr(str(self.caixa))),
            encoding="utf-8")
        self.ambiente = dict(os.environ,
                             ENCADEADOR_GH=f"{sys.executable} {dublê}")

    def cli_dublê(self, argumentos):
        return subprocess.run(
            [sys.executable, str(ESTE_INSTRUMENTO)] + argumentos,
            capture_output=True, text=True, timeout=TEMPO_DO_DUBLE,
            env=self.ambiente)


def _sobre_a_conta_no_remoto(b) -> None:
    vazio = _ambiente_com_a_conta({}, base={})
    b.caso("sem conta declarada, o ambiente nao ganha configuracao de git",
           "GIT_CONFIG_COUNT" not in vazio)

    posto = {}
    _com_a_conta_no_git(posto)
    b.caso("com conta, o git recebe um credential.helper pelo ambiente",
           posto.get("GIT_CONFIG_COUNT") == "2"
           and posto.get("GIT_CONFIG_KEY_0") == CHAVE_DO_AJUDANTE_DE_CREDENCIAL)
    b.caso("o helper zera a cadeia antes de entrar — nenhum outro responde",
           posto.get("GIT_CONFIG_VALUE_0") == "")
    b.caso("o token nao aparece no ambiente: quem o le e o helper, na hora",
           all("gh" not in v or "auth" in v for v in posto.values()))

    b.caso("sem remoto declarado, vale a conta das issues",
           _conta_do_remoto({"issues": {"conta_gh": "das-issues"}})
           == "das-issues")
    b.caso("com remoto declarado, ele manda — o remoto nao e a fila de issues",
           _conta_do_remoto({"issues": {"conta_gh": "das-issues"},
                             "remoto": {"conta_gh": "do-remoto"}})
           == "do-remoto")
    b.caso("sem conta nenhuma declarada, nao se inventa uma",
           _conta_do_remoto({}) is None)

    ja_tinha = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "user.name",
                "GIT_CONFIG_VALUE_0": "alguem"}
    _com_a_conta_no_git(ja_tinha)
    b.caso("configuracao de git que ja existia no ambiente nao e atropelada",
           ja_tinha["GIT_CONFIG_KEY_0"] == "user.name"
           and ja_tinha["GIT_CONFIG_COUNT"] == "3")


def _sobre_a_configuracao(b) -> None:
    roteiro_seco = _roteiro(b.pasta, "m-seco.json", {"etapas": [
        {"nome": "unica", "tipo": "codigo", "comando": FANTOCHE_OK}]})
    resposta = _cli(["executar", "--roteiro", roteiro_seco, "--trabalho",
                     "t-sem-config", "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("sem executor.json o disparo recusa e nomeia o arquivo",
         resposta.returncode == 2 and ARQUIVO_EXECUTOR in resposta.stderr)
    b.caso("e nada foi materializado",
         not (Path(b.evidencias) / "t-sem-config").exists())
    resposta = _cli(["ensaio", "--roteiro", roteiro_seco, "--trabalho",
                     "t-sem-config", "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("o ensaio continua rodando SEM configuração (a promessa dele)",
         resposta.returncode == 0)

    molde = Path(b.pasta) / "molde-executor.json"
    molde.write_text(json.dumps({
        "modo": "completo",
        "issues": {"repositorio": "${DONO}/${REPO}", "conta_gh": "conta"},
        "projeto": {"url": "https://exemplo.invalido/quadro"},
        "branches": {"padrao_de_trabalho": "${PADRAO}", "base": "base",
                     "integracao": "integracao"}}), encoding="utf-8")
    resposta = _cli(["executar", "--roteiro", roteiro_seco, "--trabalho",
                     "t-molde", "--dir", b.evidencias, "--cwd", b.pasta,
                     "--configuracao", str(molde)])
    b.caso("campo ainda no molde recusa e NOMEIA o campo",
         resposta.returncode == 2
         and "branches.padrao_de_trabalho" in resposta.stderr)

    so_o_basico = Path(b.pasta) / "so-o-basico.json"
    so_o_basico.write_text(json.dumps({
        "modo": "completo",
        "branches": {"padrao_de_trabalho": "trabalho/<n>"}}), encoding="utf-8")
    _, faltas = carregar_executor(b.pasta, str(so_o_basico))
    b.caso("roteiro sem issue não exige repositório de issues nem integração",
         not faltas)
    _, faltas = carregar_executor(b.pasta, str(so_o_basico), {"issue": 7})
    b.caso("mas com issue declarada, o repositório de issues passa a ser exigido",
         any("issues.repositorio" in f for f in faltas))
    _, faltas = carregar_executor(b.pasta, str(so_o_basico), {"etapas": [
        {"nome": "a", "tipo": "codigo",
         "comando": "echo branches.integracao"}]})
    b.caso("e a integração é exigida quando alguma etapa a cita",
         any("branches.integracao" in f for f in faltas))

    so_issues = Path(b.pasta) / "so-issues.json"
    so_issues.write_text(json.dumps({
        "modo": "so-issues",
        "issues": {"repositorio": "dono/repo", "conta_gh": "conta"},
        "projeto": {"url": "https://exemplo.invalido/quadro"},
        "branches": {"padrao_de_trabalho": "t/<n>", "base": "base",
                     "integracao": "integracao"}}), encoding="utf-8")
    resposta = _cli(["executar", "--roteiro", roteiro_seco, "--trabalho",
                     "t-so-issues", "--dir", b.evidencias, "--cwd", b.pasta,
                     "--configuracao", str(so_issues)])
    b.caso("modo so-issues recusa executar, com o recado do modo",
         resposta.returncode == 2 and "so-issues" in resposta.stderr)

    b.caso("modo que não existe é recusado pelo nome",
         any("modo" in p for p in carregar_executor(
             b.pasta, str(b.configurar(Path(b.pasta) / "modo-torto",
                                    modo="quase")))[1]))
    b.caso("existe_arquivo_limpeza sem o script no disco recusa",
         any("limpeza" in p for p in carregar_executor(
             b.pasta, str(b.configurar(Path(b.pasta) / "limpeza",
                                    existe_arquivo_limpeza=True,
                                    arquivo_limpeza="nao-existe.py")))[1]))

    b.configurar(b.pasta)

    _EM_CURSO.clear()
    b.caso("sem trabalho em curso o bloco não aparece",
         _bloco_de_onde_esta() == "")


def _sobre_o_bloco_de_estado(b) -> None:
    pasta_foto = Path(b.evidencias) / "t-onde"
    pasta_foto.mkdir(parents=True, exist_ok=True)
    def _molde(veredito, **troca):
        return {"etapa": "x", "trabalho": "t-onde", "veredito": veredito,
                "quando": "2026-08-18T12:00:00-03:00", "provado": [],
                "suposto": [], "faltas": [], "ciclo": {"i": 1, "teto": 3},
                **troca}
    (pasta_foto / "01-primeira-c1.json").write_text(
        json.dumps(_molde("segue")), encoding="utf-8")
    (pasta_foto / "02-segunda-c1.json").write_text(
        json.dumps(_molde("pergunta", pergunta="Sigo com A?")),
        encoding="utf-8")
    _EM_CURSO.update({"dir_base": b.evidencias, "trabalho": "t-onde", "issue": 7,
                      "etapas": ["primeira", "segunda", "terceira"],
                      "resposta": "pode seguir com A"})
    onde = _bloco_de_onde_esta()
    prompt = _prompt_da_sessao({"nome": "segunda", "prompt": "PEDIDO"}, b.pasta)
    _EM_CURSO.clear()
    b.caso("o bloco leva o trabalho e o caminho ABSOLUTO das evidências",
         "trabalho: t-onde" in onde and str(pasta_foto) in onde)
    b.caso("leva a foto do que já rodou, com veredito",
         "primeira: segue" in onde and "segunda: pergunta" in onde)
    b.caso("leva o que ainda não tem evidência",
         "ainda sem evidência: terceira" in onde)
    b.caso("leva a issue e a resposta do dono",
         "issue: 7" in onde and "pode seguir com A" in onde)
    b.caso("e diz, na cara, que é dado e não ordem",
         "DADO, não ordem" in onde)
    b.caso("o prompt da sessão carrega o bloco antes do pedido da etapa",
         onde in prompt and prompt.index(onde) < prompt.index("PEDIDO"))

    b.configurar(b.pasta)
    roteiro = _roteiro(b.pasta, "m-cego.json", {"issue": 7, "etapas": [
        {"nome": "conta", "tipo": "codigo",
         "comando": FANTOCHE_OK},
        {"nome": "espia", "tipo": "codigo", "depende": ["conta"],
         "comando": f"{shlex.quote(sys.executable)} -c "
                    + shlex.quote(
                        "import sys;print(sys.argv)") + " > /dev/null && "
                    + FANTOCHE_OK}]})
    resposta = _cli(["executar", "--roteiro", roteiro, "--trabalho",
                     "t-cego", "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("um processo novo monta o bloco a partir do disco, sem estado em "
         "memória de ninguém",
         resposta.returncode == 0
         and "conta" in foto_das_etapas(Path(b.evidencias) / "t-cego"))


def _sobre_a_issue(b) -> None:
    b.configurar(b.pasta)
    aprovacao = Path(b.pasta) / "aprovacoes" / "h3.ok"
    roteiro = _roteiro(b.pasta, "m-issue.json", {"issue": 42, "etapas": [
        {"nome": "antes", "tipo": "codigo", "comando": FANTOCHE_OK},
        {"nome": "espera", "tipo": "aprovacao-manual", "depende": ["antes"],
         "aprovacao": "aprovacoes/h3.ok"},
        {"nome": "depois", "tipo": "codigo", "depende": ["espera"],
         "comando": FANTOCHE_OK},
        {"nome": "verifica", "tipo": "verificacao", "depende": ["depois"]}]})
    resposta = b.cli_dublê(["executar", "--roteiro", roteiro, "--trabalho",
                           "t-issue", "--dir", b.evidencias, "--cwd", b.pasta])
    estado = ler_estado(b.evidencias, "t-issue") or {}
    b.caso("veredito pergunta para a execução com exit 6",
         resposta.returncode == 6)
    b.caso("e o estado em disco diz aguardando-resposta, com a issue",
         estado.get("situacao") == "aguardando-resposta"
         and estado.get("issue") == 42)
    b.caso("a pergunta foi postada na issue, com a marca do motor",
         (b.caixa / "postado.md").exists()
         and MARCA_DO_MOTOR in (b.caixa / "postado.md").read_text())
    b.caso("o motor pediu o token da conta configurada, sem trocar a ativa",
         "auth token --user conta" in (b.caixa / "chamadas.txt").read_text())
    b.caso("o andamento diz onde a resposta é esperada",
         "aguardando resposta na issue 42" in b.cli_dublê(
             ["andamento", "--trabalho", "t-issue", "--dir", b.evidencias]).stdout)

    postado = (b.caixa / "postado.md").read_text()
    b.caso("cada etapa vira um comentário na issue, com o veredito",
         "`antes` — segue (1 de 4" in postado)
    b.caso("e o comentário diz o que foi testado, com o comando",
         "O que foi testado" in postado and "$ " in postado)
    resumo = resumo_da_etapa({"etapa": "x", "veredito": "para",
                              "provado": [{"afirmacao": "a", "comando": "b",
                                           "saida": "c"}],
                              "faltas": ["faltou d"], "proximo": "faça e"},
                             2, 5)
    b.caso("o resumo carrega faltas e o próximo de quem reprovou",
         "faltou d" in resumo and "faça e" in resumo and "2 de 5" in resumo)
    b.caso("etapa sem prova nenhuma é dita, não escondida",
         "Sem prova declarada" in resumo_da_etapa(
             {"etapa": "x", "veredito": "segue", "provado": []}, 1, 1))
    b.caso("prova longa é cortada — comentário que ninguém lê não registra",
         len(resumo_da_etapa({"etapa": "x", "veredito": "segue", "provado": [
             {"afirmacao": "a", "comando": "b", "saida": "z" * 5000}]}, 1, 1))
         < 1200)

    (b.caixa / "comentarios.json").write_text(json.dumps({"comments": [
        {"author": {"login": "conta"}, "body": f"pergunta {MARCA_DO_MOTOR}"}]}),
        encoding="utf-8")
    resposta = b.cli_dublê(["respostas", "--trabalho", "t-issue", "--dir",
                           b.evidencias, "--cwd", b.pasta])
    b.caso("comentário do próprio motor não conta como resposta",
         "ninguém respondeu" in resposta.stdout)
    (b.caixa / "comentarios.json").write_text(json.dumps({"comments": [
        {"author": {"login": "conta"}, "body": f"pergunta {MARCA_DO_MOTOR}"},
        {"author": {"login": "dono"}, "body": "pode seguir, aprove"}]}),
        encoding="utf-8")
    resposta = b.cli_dublê(["respostas", "--trabalho", "t-issue", "--dir",
                           b.evidencias, "--cwd", b.pasta])
    b.caso("comentário de outro autor é lido como resposta e gravado",
         "resposta de dono" in resposta.stdout
         and (ler_estado(b.evidencias, "t-issue") or {}).get("resposta")
         == "pode seguir, aprove")

    aprovacao.parent.mkdir(parents=True, exist_ok=True)
    aprovacao.write_text("ok", encoding="utf-8")
    antes_c1 = Path(b.evidencias) / "t-issue" / "01-antes-c1.json"
    marca_de_tempo = antes_c1.stat().st_mtime
    resposta = b.cli_dublê(["executar", "--roteiro", roteiro, "--trabalho",
                           "t-issue", "--dir", b.evidencias, "--cwd", b.pasta,
                           "--retomar"])
    b.caso("com --retomar a execução fecha depois da aprovação",
         resposta.returncode == 0)
    b.caso("e a etapa já provada não rodou de novo",
         "já provada" in resposta.stdout
         and antes_c1.stat().st_mtime == marca_de_tempo
         and not (Path(b.evidencias) / "t-issue" / "01-antes-c2.json").exists())
    b.caso("o desfecho também foi para a issue",
         "Execução completa" in (b.caixa / "postado.md").read_text())
    b.caso("nem o `proximo` de uma reprovação carrega caminho absoluto",
         "/home/" not in resumo_da_etapa(
             {"etapa": "x", "veredito": "para", "provado": [],
              "proximo": "Leia o log da verificação em `03-x-c1.log`, no "
                         "trabalho t: corrija cada acusação."}, 1, 1))
    b.caso("o encurtador troca caminho do repositório por relativo",
         sem_caminho_de_maquina("$ tail -n 1 /r/a/tmp/rec/v/04.log", "/r/a")
         == "$ tail -n 1 tmp/rec/v/04.log")
    b.caso("e o que está fora do repositório vira ~, nunca o nome de quem roda",
         sem_caminho_de_maquina(f"leia {Path.home()}/fora/z.log", "/r/a")
         == "leia ~/fora/z.log")
    b.caso("texto sem caminho nenhum atravessa intacto",
         sem_caminho_de_maquina("nada aqui", "/r/a") == "nada aqui")
    b.caso("e NENHUM comentário carrega caminho absoluto de máquina",
         "/home/" not in (b.caixa / "postado.md").read_text()
         and str(Path(b.evidencias).resolve()) not in
             (b.caixa / "postado.md").read_text())
    b.caso("e o estado terminal ficou gravado",
         (ler_estado(b.evidencias, "t-issue") or {}).get("situacao") == "completa")

    def _gravou(situacao):
        try:
            gravar_estado(b.evidencias, "t-situacao", situacao)
            return True
        except ValueError:
            return False

    b.caso("toda situação de SITUACOES é aceita por gravar_estado",
         all(_gravou(s) for s in SITUACOES))
    b.caso("situação fora de SITUACOES é recusada na fronteira",
         not _gravou("inventada"))

    roteiro = _roteiro(b.pasta, "m-sem-issue.json", {"etapas": [
        {"nome": "espera", "tipo": "aprovacao-manual",
         "aprovacao": "nao-existe.ok"}]})
    resposta = b.cli_dublê(["executar", "--roteiro", roteiro, "--trabalho",
                           "t-sem-issue", "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("sem issue declarada a execução para do mesmo jeito e confessa",
         resposta.returncode == 6 and "não postei" in resposta.stdout)

    b.caso("issue que não é inteiro é recusada na fronteira",
         any("issue precisa ser" in e for e in validar_roteiro(
             {"issue": "quarenta e dois", "etapas": [
                 {"nome": "a", "tipo": "codigo", "comando": "echo"}]},
             _evidencia.carregar_esquema())))

    avisos = avisos_do_alvo({}, {"etapas": [
        {"nome": "trabalha", "tipo": "codigo", "comando": "echo oi"},
        {"nome": "aprova", "tipo": "aprovacao-manual", "depende": ["trabalha"],
         "aprovacao": "a.ok"}]}, b.pasta)
    b.caso("aprovação manual sem commit antes vira aviso",
         any("depois de um commit" in a for a in avisos))
    b.caso("aprovação manual sem rodada do cético vira aviso",
         any("cético" in a for a in avisos))


def _sobre_a_janela_e_o_ensaio(b) -> None:
    contador = Path(b.pasta) / "contador.txt"
    contador.write_text("1\n", encoding="utf-8")

    def _fantoche(afirmacao, comando, saida):
        molde = {"veredito": "segue", "suposto": [], "faltas": [],
                 "etapa": "x", "trabalho": "x", "ciclo": {"i": 1, "teto": 1},
                 "quando": "2000-01-01T00:00:00Z",
                 "provado": [{"afirmacao": afirmacao, "comando": comando,
                              "saida": saida}]}
        return (f"{shlex.quote(sys.executable)} -c "
                + shlex.quote("import sys;sys.stdout.write("
                              + repr(json.dumps(molde, ensure_ascii=False))
                              + ")"))

    roteiro = _roteiro(b.pasta, "m-janela.json", {"etapas": [
        {"nome": "declara", "tipo": "codigo",
         "comando": _fantoche("o contador vale 1", "cat contador.txt", "1")},
        {"nome": "muda", "tipo": "codigo", "depende": ["declara"],
         "comando": "echo 2 > contador.txt && "
                    + _fantoche("o contador vale 2", "cat contador.txt", "2")},
        {"nome": "verifica", "tipo": "verificacao", "depende": ["muda"]},
    ]})
    resposta = _cli(["executar", "--roteiro", roteiro, "--trabalho",
                     "t-janela", "--dir", b.evidencias, "--cwd", b.pasta])
    trabalho_janela = Path(b.evidencias) / "t-janela"
    b.caso("etapa honesta não é acusada porque a seguinte mudou o mundo",
         resposta.returncode == 0)
    b.caso("a verificação da janela fica gravada ao lado de cada evidência",
         (trabalho_janela / "verificacoes" / "01-declara-c1.json").is_file())
    b.caso("e a etapa de verificação diz que agregou o da janela",
         "verificados na janela" in (
             trabalho_janela / "03-verifica-c1.log").read_text(
                 encoding="utf-8"))
    b.caso("contraprova: re-executada AGORA, a prova honesta seria acusada",
         _cli_verificar(trabalho_janela / "01-declara-c1.json",
                       b.pasta).returncode == 4)
    b.caso("a subpasta de verificações não vira ciclo novo",
         _evidencia.caminho_da_evidencia(b.evidencias, "t-janela", 1, "declara")[1] == 2)

    sentinela = Path(b.pasta) / "sentinela.txt"
    roteiro = _roteiro(b.pasta, "m-sentinela.json", {"etapas": [
        {"nome": "grava", "tipo": "codigo",
         "comando": f"touch {sentinela} && {FANTOCHE_OK}"},
        {"nome": "verifica", "tipo": "verificacao", "depende": ["grava"]},
    ]})
    resposta = _cli(["ensaio", "--roteiro", roteiro, "--trabalho",
                     "t-sentinela", "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("ensaio lista os dois estágios e sai 0",
         resposta.returncode == 0 and "estagio 1" in resposta.stdout
         and "estagio 2 [só]" in resposta.stdout)
    b.caso("ensaio não executa nada: a sentinela NÃO existe",
         not sentinela.exists())
    b.caso("ensaio não escreve evidência nenhum",
         not (Path(b.evidencias) / "t-sentinela").exists())

    resposta = _cli(["executar", "--roteiro", roteiro, "--trabalho",
                     "t-sentinela", "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("contraprova: sem ensaio a sentinela aparece e a execução completa",
         resposta.returncode == 0 and sentinela.exists()
         and (Path(b.evidencias) / "t-sentinela" / "01-grava-c1.json").exists()
         and (Path(b.evidencias) / "t-sentinela" / "02-verifica-c1.json").exists())


def _sobre_o_grafo(b) -> None:
    marca_a, marca_b = Path(b.pasta) / "marca-a", Path(b.pasta) / "marca-b"

    def espera(minha, outra):
        return (f"touch {minha} && for i in $(seq 1 50); do "
                f"[ -f {outra} ] && break; sleep 0.1; done; "
                f"[ -f {outra} ] && " + FANTOCHE_OK)

    roteiro = _roteiro(b.pasta, "m-fork.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo",
         "comando": espera(marca_a, marca_b)},
        {"nome": "bb", "tipo": "codigo",
         "comando": espera(marca_b, marca_a)},
        {"nome": "cc", "tipo": "codigo", "comando": FANTOCHE_OK,
         "depende": ["aa", "bb"]},
    ]})
    resposta = _cli(["executar", "--roteiro", roteiro, "--trabalho",
                     "t-fork", "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("fork real: as duas se veem rodando (encontro marcado) e o join vem",
         resposta.returncode == 0 and "fork de 2" in resposta.stdout
         and (Path(b.evidencias) / "t-fork" / "03-cc-c1.json").exists())

    roteiro = _roteiro(b.pasta, "m-solo.json", {"etapas": [
        {"nome": "verifica", "tipo": "verificacao"},
        {"nome": "aa", "tipo": "codigo", "comando": FANTOCHE_OK},
    ]})
    resposta = _cli(["ensaio", "--roteiro", roteiro, "--trabalho",
                     "t-solo", "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("verificação pronta junto ganha estágio próprio [só]",
         "estagio 1 [só]: 01-verifica" in resposta.stdout)

    roteiro = _roteiro(b.pasta, "m-skip.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo", "comando": FANTOCHE_OK},
        {"nome": "bb", "tipo": "codigo", "comando": FANTOCHE_OK,
         "ligada": False, "depende": ["aa"]},
        {"nome": "cc", "tipo": "codigo", "comando": FANTOCHE_OK,
         "depende": ["bb"]},
    ]})
    resposta = _cli(["executar", "--roteiro", roteiro, "--trabalho",
                     "t-skip", "--dir", b.evidencias, "--cwd", b.pasta])
    meio = json.loads((Path(b.evidencias) / "t-skip" / "02-bb-c1.json")
                      .read_text(encoding="utf-8"))
    b.caso("desligada registra o skip e não impede a terceira",
         resposta.returncode == 0 and meio["motivo"] == "desligada"
         and (Path(b.evidencias) / "t-skip" / "03-cc-c1.json").exists())

    roteiro = _roteiro(b.pasta, "m-morte.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo", "comando": "exit 9"},
        {"nome": "bb", "tipo": "codigo", "comando": FANTOCHE_OK,
         "depende": ["aa"]},
    ]})
    resposta = _cli(["executar", "--roteiro", roteiro, "--trabalho",
                     "t-morte", "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("morte vira para sintético, exit 5, e o dependente nem roda",
         resposta.returncode == 5
         and not (Path(b.evidencias) / "t-morte" / "02-bb-c1.json").exists())

    roteiro = _roteiro(b.pasta, "m-lixo.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo", "comando": "echo isto-nao-e-evidência"},
        {"nome": "bb", "tipo": "codigo", "comando": FANTOCHE_OK,
         "depende": ["aa"]},
    ]})
    resposta = _cli(["executar", "--roteiro", roteiro, "--trabalho",
                     "t-lixo", "--dir", b.evidencias, "--cwd", b.pasta])
    primeiro = json.loads((Path(b.evidencias) / "t-lixo" / "01-aa-c1.json")
                          .read_text(encoding="utf-8"))
    b.caso("stdout-lixo vira para recibo-invalido e a execução para",
         resposta.returncode == 5 and primeiro["motivo"] == "recibo-invalido")

    roteiro = _roteiro(b.pasta, "m-teto.json", {"teto": 2, "etapas": [
        {"nome": "aa", "tipo": "codigo",
         "comando": f"touch {Path(b.pasta) / 'teto-rodou'} && {FANTOCHE_OK}"},
    ]})
    for _ in range(2):
        _cli_evidencia(["sintetico", "--dir", b.evidencias, "--trabalho", "t-teto",
                     "--etapa", "aa", "--ordem", "1", "--teto", "2",
                     "--motivo", "morta", "--detalhe", "plantado no teste"])
    resposta = _cli(["executar", "--roteiro", roteiro, "--trabalho",
                     "t-teto", "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("teto esgotado: nada roda e nasce o para teto-esgotado",
         resposta.returncode == 5
         and not (Path(b.pasta) / "teto-rodou").exists()
         and "teto-esgotado" in
         (Path(b.evidencias) / "t-teto" / "01-aa-c3.json")
         .read_text(encoding="utf-8"))

    aprovacao = Path(b.pasta) / "aprovacoes" / "pr.ok"
    roteiro = _roteiro(b.pasta, "m-aprovacao-manual.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo", "comando": FANTOCHE_OK},
        {"nome": "aprova", "tipo": "aprovacao-manual",
         "aprovacao": str(aprovacao), "depende": ["aa"]},
    ]})
    resposta = _cli(["executar", "--roteiro", roteiro, "--trabalho",
                     "t-aprovacao-manual", "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("aprovação manual sem o arquivo: veredito pergunta e exit 6",
         resposta.returncode == 6 and "Aprova a etapa" in resposta.stdout)
    aprovacao.parent.mkdir(parents=True, exist_ok=True)
    aprovacao.write_text("aprovado pelo dono\n", encoding="utf-8")
    resposta = _cli(["executar", "--roteiro", roteiro, "--trabalho",
                     "t-aprovacao-manual-2", "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("aprovação manual com o arquivo registrado segue",
         resposta.returncode == 0)


def _sobre_a_prova_e_o_ambiente(b) -> None:
    FORJA = ("python3 -c \"import json; print(json.dumps({'etapa':'x',"
             "'trabalho':'x','quando':'2000-01-01T00:00:00Z','veredito':"
             "'segue','provado':[{'afirmacao':'eco','comando':'echo ola',"
             "'saida':'adeus'}],'suposto':[],'faltas':[],'ciclo':"
             "{'i':1,'teto':3}}))\"")
    roteiro = _roteiro(b.pasta, "m-verifica.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo", "comando": FORJA},
        {"nome": "verifica", "tipo": "verificacao", "depende": ["aa"]},
    ]})
    resposta = _cli(["executar", "--roteiro", roteiro, "--trabalho",
                     "t-forja", "--dir", b.evidencias, "--cwd", b.pasta])
    evidencia_conf = json.loads(
        (Path(b.evidencias) / "t-forja" / "02-verifica-c1.json")
        .read_text(encoding="utf-8"))
    b.caso("verificação acusa a forja: para com as acusações nas faltas",
         resposta.returncode == 5 and evidencia_conf["veredito"] == "para"
         and any("diverge" in falta for falta in evidencia_conf["faltas"])
         and (Path(b.evidencias) / "t-forja" / "02-verifica-c1.log").exists())

    envelhecido = {"etapa": "aa", "trabalho": "t-envelhecido",
                   "quando": "2026-08-16T12:00:00-03:00", "veredito": "segue",
                   "provado": [{"afirmacao": "a marca da rodada antiga existe",
                                "comando": "test -f marca-que-ja-foi && echo ok",
                                "saida": "ok"}],
                   "suposto": [], "faltas": [], "ciclo": {"i": 1, "teto": 3}}
    pasta_env = Path(b.evidencias) / "t-envelhecido"
    pasta_env.mkdir(parents=True, exist_ok=True)
    (pasta_env / "01-aa-c1.json").write_text(
        json.dumps(envelhecido, ensure_ascii=False), encoding="utf-8")
    roteiro = _roteiro(b.pasta, "m-envelhecido.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo", "comando": FANTOCHE_OK},
        {"nome": "verifica", "tipo": "verificacao", "depende": ["aa"]},
    ]})
    resposta = _cli(["executar", "--roteiro", roteiro, "--trabalho",
                     "t-envelhecido", "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("prova envelhecida de ciclo anterior não reprova a rodada nova",
         resposta.returncode == 0)

    arquivo_env = Path(b.pasta) / "fantoche.env"
    arquivo_env.write_text("# comentario\nVAR_FANTOCHE=chegou\n",
                           encoding="utf-8")
    roteiro = _roteiro(b.pasta, "m-env.json", {
        "ambiente": {"env": str(arquivo_env.name)},
        "etapas": [{"nome": "aa", "tipo": "codigo", "comando":
                    "python3 -c \"import json,os; print(json.dumps("
                    "{'etapa':'x','trabalho':'x',"
                    "'quando':'2000-01-01T00:00:00Z','veredito':'segue',"
                    "'provado':[],'suposto':["
                    "os.environ.get('VAR_FANTOCHE','ausente')],"
                    "'faltas':[],'ciclo':{'i':1,'teto':1}}))\""}]})
    resposta = _cli(["executar", "--roteiro", roteiro, "--trabalho",
                     "t-env", "--dir", b.evidencias, "--cwd", b.pasta])
    escrito = json.loads((Path(b.evidencias) / "t-env" / "01-aa-c1.json")
                         .read_text(encoding="utf-8"))
    b.caso("o arquivo de ambiente do roteiro chega à etapa",
         escrito["suposto"] == ["chegou"])


def _sobre_a_sessao(b) -> None:
    roteiro = _roteiro(b.pasta, "m-sessao.json", {"etapas": [
        {"nome": "pensa", "tipo": "sessao", "prompt": "pense"}]})
    resposta = _cli(["ensaio", "--roteiro", roteiro, "--trabalho",
                     "t-sessao", "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("sessão listada no ensaio com claude -p, sem executar",
         resposta.returncode == 0 and "claude -p" in resposta.stdout
         and not (Path(b.evidencias) / "t-sessao").exists())

    b.caso("sem --bare por padrão — senão a sessão nem autentica",
         "--bare" not in _comando_sessao({"nome": "x", "tipo": "sessao"}))
    b.caso("--bare entra quando a etapa pede",
         "--bare" in _comando_sessao({"nome": "x", "tipo": "sessao",
                                      "bare": True}))
    b.caso("o ensaio não mente sobre o --bare",
         "--bare" not in resposta.stdout)

    b.caso("a sessão pede o fluxo de eventos, não o blob do fim",
         "stream-json" in " ".join(_comando_sessao({"nome": "x", "tipo": "sessao"})))
    b.caso("o resumo nomeia a ferramenta que a sessão está usando",
         "Bash cat x.md" == _resumo_do_evento(
             {"type": "assistant", "message": {"content": [
                 {"type": "tool_use", "name": "Bash",
                  "input": {"command": "cat x.md"}}]}}))
    b.caso("ferramenta sem pista ainda aparece pelo nome",
         "StructuredOutput" == _resumo_do_evento(
             {"type": "assistant", "message": {"content": [
                 {"type": "tool_use", "name": "StructuredOutput", "input": {}}]}}))
    b.caso("contabilidade de token não vira linha na tela",
         "" == _resumo_do_evento({"type": "system", "subtype": "thinking_tokens"}))
    b.caso("o raciocínio não vaza para a tela",
         "" == _resumo_do_evento({"type": "assistant", "message": {"content": [
             {"type": "thinking", "thinking": "..."}]}}))
    b.caso("o fim do fluxo conta os turnos",
         "3 turnos" in _resumo_do_evento(
             {"type": "result", "subtype": "success", "num_turns": 3}))

    teto = json.dumps({"subtype": "error_max_turns", "num_turns": 25})
    b.caso("teto de turnos é fracasso retomável", _bateu_no_teto(teto))
    b.caso("sucesso não se retoma",
         not _bateu_no_teto(json.dumps({"subtype": "success"})))
    b.caso("falta de login não se retoma — repetiria igual",
         not _bateu_no_teto(json.dumps(
             {"subtype": "success", "result": "Not logged in"})))
    b.caso("stdout ilegível não vira retomada infinita",
         not _bateu_no_teto("lixo sem json"))
    b.caso("sem --resume, o comando não retoma",
         "--resume" not in _comando_sessao({"nome": "x", "tipo": "sessao"}))
    b.caso("com session_id, o comando retoma aquela sessão",
         ["--resume", "abc-123"] == _comando_sessao(
             {"nome": "x", "tipo": "sessao"}, "abc-123")[2:4])
    b.caso("o pedido de fecho manda NÃO reler o que já foi lido",
         "NÃO recomece" in PEDIDO_DE_FECHO and "faltas" in PEDIDO_DE_FECHO)
    b.caso("a retomada tem teto — não insiste para sempre", RETOMADAS <= 3)

    import time as _t
    aviso = {"status": "allowed_warning", "utilization": 0.54,
             "resetsAt": int(_t.time()) + 9999}
    b.caso("aviso de consumo NÃO faz dormir — é número subindo, não parede",
         _espera_do_limite('{"subtype":"success"}', aviso) == 0)
    parede = {"status": "blocked", "resetsAt": int(_t.time()) + 600}
    espera = _espera_do_limite('{"subtype":"error_during_execution"}', parede)
    b.caso("bloqueio faz esperar o tempo que o servidor declarou",
         500 < espera < 700)
    b.caso("parede sem hora declarada não vira espera eterna",
         _espera_do_limite('{"subtype":"error","result":"rate limit reached"}',
                           None) == 300)
    b.caso("parede que demora demais não prende a execução por um dia",
         _espera_do_limite("{}", {"status": "blocked",
                                  "resetsAt": int(_t.time()) + 99999})
         <= ESPERA_MAXIMA_S)
    b.caso("sucesso normal nunca dorme",
         _espera_do_limite('{"subtype":"success"}', None) == 0)
    b.caso("teto de turnos continua sendo retomada, não espera",
         _espera_do_limite('{"subtype":"error_max_turns"}', None) == 0)

    prosa = json.dumps({"subtype": "success", "result":
                        "Tratei como dois produtos distintos, dentro dos "
                        "limites da documentacao."})
    b.caso("prosa em português com 'tratei' e 'limites' NÃO é parede",
         _espera_do_limite(prosa, aviso) == 0)
    b.caso("sessão que deu certo nunca dorme, nem com parede declarada",
         _espera_do_limite('{"subtype":"success"}',
                           {"status": "blocked",
                            "resetsAt": int(_t.time()) + 600}) == 0)
    b.caso("'rate' e 'limit' separados não bastam — a expressão é colada",
         _espera_do_limite('{"subtype":"error","result":"accurate limite"}',
                           None) == 0)

    teto_estourado = json.dumps({"is_error": True, "subtype": "error_max_turns",
                                 "num_turns": 25, "result": None})
    diagnostico = _porque_morreu(1, teto_estourado, "/tmp/x.log")
    b.caso("teto de turnos é nomeado na evidência, não escondido no log",
         "teto de turnos" in diagnostico)
    b.caso("e a evidência diz onde mexer", "max-turnos" in diagnostico)
    b.caso("e conta quantos turnos se perderam", "25 turnos" in diagnostico)
    b.caso("o recado da sessão sobe para a evidência",
         "Not logged in" in _porque_morreu(
             1, json.dumps({"subtype": "success",
                            "result": "Not logged in · Please run /login"}),
             "/tmp/x.log"))
    b.caso("stdout que não é JSON ainda manda ler o log",
         "leia /tmp/x.log" in _porque_morreu(1, "lixo sem json", "/tmp/x.log"))


def _sobre_o_tempo_limite(b) -> None:
    dorminhoco = SONO_DO_TESTE_DE_ORFAO.format(abs(hash(b.pasta)) % 1000000)
    roteiro = _roteiro(b.pasta, "m-tempo.json", {"etapas": [
        {"nome": "trava", "tipo": "codigo", "comando": dorminhoco,
         "tempo-limite": 1},
        {"nome": "depois", "tipo": "codigo", "comando": FANTOCHE_OK,
         "depende": ["trava"]}]})
    resposta = _cli(["executar", "--roteiro", roteiro, "--trabalho",
                     "t-tempo", "--dir", b.evidencias, "--cwd", b.pasta])
    evidencia_tempo = json.loads(
        (Path(b.evidencias) / "t-tempo" / "01-trava-c1.json")
        .read_text(encoding="utf-8"))
    orfaos = subprocess.run(["pgrep", "-f", dorminhoco],
                            capture_output=True, text=True)
    b.caso("estouro de tempo vira para morta, exit 5, com log",
         resposta.returncode == 5 and evidencia_tempo["motivo"] == "morta"
         and "tempo-limite" in evidencia_tempo["faltas"][0]
         and (Path(b.evidencias) / "t-tempo" / "01-trava-c1.log").exists())
    b.caso("o grupo do processo morre junto — nenhum órfão",
         orfaos.returncode != 0)

    fantoche_bin = Path(b.pasta) / "bin-meia-linha"
    fantoche_bin.mkdir(exist_ok=True)
    fingido = fantoche_bin / "claude"
    fingido.write_text(CLAUDE_QUE_PARA_NA_METADE, encoding="utf-8")
    fingido.chmod(0o755)
    roteiro = _roteiro(b.pasta, "m-meia-linha.json", {"etapas": [
        {"nome": "conversa", "tipo": "sessao", "prompt": "oi",
         "tempo-limite": TETO_CURTO_DO_TESTE}]})
    partida = time.monotonic()
    resposta = subprocess.run(
        [sys.executable, str(ESTE_INSTRUMENTO), "executar",
         "--roteiro", roteiro, "--trabalho", "t-meia", "--dir", b.evidencias,
         "--cwd", b.pasta],
        capture_output=True, text=True, timeout=TETO_DO_DUBLE,
        env=dict(os.environ,
                 PATH=f"{fantoche_bin}:{os.environ.get('PATH', '')}"))
    parede = time.monotonic() - partida
    b.caso("linha pela metade não fura o teto de tempo da etapa",
         resposta.returncode == EXIT_PAROU_NUM_PARA
         and parede < TETO_CURTO_DO_TESTE * FOLGA_DO_TETO)


def _sobre_os_ciclos_e_o_disco(b) -> None:
    roteiro = _roteiro(b.pasta, "m-ciclos.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo", "comando": FANTOCHE_OK},
        {"nome": "verifica", "tipo": "verificacao", "depende": ["aa"]}]})
    for _ in range(3):
        resposta = _cli(["executar", "--roteiro", roteiro, "--trabalho",
                         "t-ciclos", "--dir", b.evidencias, "--cwd", b.pasta])
    pasta_ciclos = Path(b.evidencias) / "t-ciclos"
    b.caso("terceira rodada não se autoacusa e cada ciclo tem o próprio log",
         resposta.returncode == 0
         and (pasta_ciclos / "02-verifica-c1.log").exists()
         and (pasta_ciclos / "02-verifica-c2.log").exists()
         and (pasta_ciclos / "02-verifica-c3.log").exists())

    roteiro = _roteiro(b.pasta, "m-teto2.json", {"teto": 2, "etapas": [
        {"nome": "aa", "tipo": "codigo",
         "comando": f"touch {Path(b.pasta) / 'teto2-rodou'} && {FANTOCHE_OK}"}]})
    _cli_evidencia(["sintetico", "--dir", b.evidencias, "--trabalho", "t-teto2",
                 "--etapa", "aa", "--ordem", "1", "--teto", "2",
                 "--motivo", "morta", "--detalhe", "plantado"])
    (Path(b.evidencias) / "t-teto2" / "01-aa-c9.json").write_text(
        "{ para corrompido", encoding="utf-8")
    resposta = _cli(["executar", "--roteiro", roteiro, "--trabalho",
                     "t-teto2", "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("evidência corrompida conta no teto: nada roda",
         resposta.returncode == 5
         and not (Path(b.pasta) / "teto2-rodou").exists())

    roteiro = _roteiro(b.pasta, "m-stderr.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo",
         "comando": f"echo aviso-no-stderr >&2; {FANTOCHE_OK}"}]})
    _cli(["executar", "--roteiro", roteiro, "--trabalho", "t-stderr",
          "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("stderr de etapa boa não evapora: está no log",
         "aviso-no-stderr" in
         (Path(b.evidencias) / "t-stderr" / "01-aa-c1.log")
         .read_text(encoding="utf-8"))

    (Path(b.pasta) / "aspas.env").write_text(
        'VAR_ASPAS="entre aspas"\nVAR_COMENTARIO=valor # comentario\n',
        encoding="utf-8")
    roteiro = _roteiro(b.pasta, "m-aspas.json", {
        "ambiente": {"env": "aspas.env"},
        "etapas": [{"nome": "aa", "tipo": "codigo", "comando":
                    "python3 -c \"import json,os; print(json.dumps("
                    "{'etapa':'x','trabalho':'x',"
                    "'quando':'2000-01-01T00:00:00Z','veredito':'segue',"
                    "'provado':[],'suposto':["
                    "os.environ.get('VAR_ASPAS',''),"
                    "os.environ.get('VAR_COMENTARIO','')],"
                    "'faltas':[],'ciclo':{'i':1,'teto':1}}))\""}]})
    _cli(["executar", "--roteiro", roteiro, "--trabalho", "t-aspas",
          "--dir", b.evidencias, "--cwd", b.pasta])
    escrito = json.loads((Path(b.evidencias) / "t-aspas" / "01-aa-c1.json")
                         .read_text(encoding="utf-8"))
    b.caso("aspas envolventes e comentário caem como no source",
         escrito["suposto"] == ["entre aspas", "valor"])

    roteiro = _roteiro(b.pasta, "m-lista.json", {"teto": 1, "etapas": [
        {"nome": "aa", "tipo": "codigo",
         "comando": f"touch {Path(b.pasta) / 'lista-rodou'} && {FANTOCHE_OK}"}]})
    pasta_lista = Path(b.evidencias) / "t-lista"
    pasta_lista.mkdir(parents=True, exist_ok=True)
    (pasta_lista / "01-aa-c9.json").write_text("[]", encoding="utf-8")
    resposta = _cli(["executar", "--roteiro", roteiro, "--trabalho",
                     "t-lista", "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("JSON não-objeto no diretório conta no teto, sem traceback",
         resposta.returncode == 5
         and not (Path(b.pasta) / "lista-rodou").exists())

    pasta_espaco = Path(b.pasta) / "com espaco"
    (pasta_espaco / "aprovacoes").mkdir(parents=True, exist_ok=True)
    b.configurar(pasta_espaco)
    (pasta_espaco / "aprovacoes" / "pr.ok").write_text("ok", encoding="utf-8")
    roteiro = _roteiro(b.pasta, "m-espaco.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo", "comando": FANTOCHE_OK},
        {"nome": "verifica", "tipo": "verificacao", "depende": ["aa"]},
        {"nome": "aprova", "tipo": "aprovacao-manual",
         "aprovacao": "aprovacoes/pr.ok", "depende": ["verifica"]}]})
    evidencias_espaco = str(pasta_espaco / "b.evidencias")
    exits = [_cli(["executar", "--roteiro", roteiro, "--trabalho",
                   "t-espaco", "--dir", evidencias_espaco,
                   "--cwd", str(pasta_espaco)]).returncode
             for _ in range(2)]
    b.caso("caminho com espaço: dois ciclos completos sem autoacusação",
         exits == [0, 0])

    (Path(b.pasta) / "herda.env").write_text("VAR_HERDA=verifica\n",
                                           encoding="utf-8")
    roteiro = _roteiro(b.pasta, "m-herda.json", {
        "ambiente": {"env": "herda.env"},
        "etapas": [
            {"nome": "aa", "tipo": "codigo", "comando":
             "python3 -c \"import json; print(json.dumps("
             "{'etapa':'x','trabalho':'x',"
             "'quando':'2000-01-01T00:00:00Z','veredito':'segue',"
             "'provado':[{'afirmacao':'a variavel do ambiente chega',"
             "'comando':'test \\\\\\\"$VAR_HERDA\\\\\\\" = verifica && echo ok',"
             "'saida':'ok'}],"
             "'suposto':[],'faltas':[],'ciclo':{'i':1,'teto':1}}))\""},
            {"nome": "verifica", "tipo": "verificacao", "depende": ["aa"]}]})
    resposta = _cli(["executar", "--roteiro", roteiro, "--trabalho",
                     "t-herda", "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("verificação herda o ambiente: prova com variável re-executa",
         resposta.returncode == 0)


def _sobre_o_prompt_montado(b) -> None:
    etapa_sessao = {"nome": "s", "tipo": "sessao", "prompt": "faça"}
    configuracao = Path(b.pasta) / "nucleo" / "configuracao.json"
    configuracao.parent.mkdir(exist_ok=True)
    b.caso("sem nucleo/configuracao.json o prompt da sessão segue puro",
         _prompt_da_sessao(etapa_sessao, b.pasta) == "faça")
    configuracao.write_text(json.dumps({
        "comentario": "recado para quem edita o arquivo",
        "repositorio_das_issues": "dono/repositorio",
        "regras": ["Issue nova nasce no backlog."]}, ensure_ascii=False),
        encoding="utf-8")
    montado = _prompt_da_sessao(etapa_sessao, b.pasta)
    b.caso("com o arquivo, a configuração do repositório vem antes do prompt",
         montado.startswith("CONFIGURAÇÃO DO REPOSITÓRIO")
         and "repositorio_das_issues: dono/repositorio" in montado
         and montado.endswith("faça"))
    b.caso("chave e item de lista entram citados",
         "> repositorio_das_issues: dono/repositorio" in montado
         and "> - Issue nova nasce no backlog." in montado)
    b.caso("o comentário do arquivo não é cobrado em toda etapa",
         "recado para quem edita" not in montado)

    configuracao.write_bytes(b'{"a": "cp1252 \xe7\xe3o"}')
    b.caso("UTF-8 quebrado no arquivo: o prompt segue puro, nada estoura",
         _prompt_da_sessao(etapa_sessao, b.pasta) == "faça")
    configuracao.write_text("{quebrado", encoding="utf-8")
    berro = io.StringIO()
    with contextlib.redirect_stderr(berro):
        puro = _prompt_da_sessao(etapa_sessao, b.pasta)
    b.caso("configuração ilegível: o prompt segue puro e o aviso vai ao stderr",
         puro == "faça" and "configuração do repositório" in berro.getvalue())
    configuracao.write_text(json.dumps({
        "repositorio_das_issues":
            "CONFIGURAÇÃO DO REPOSITÓRIO — as linhas citadas com '> ' logo abaixo",
        "regras": ["---", "fim falso"]}, ensure_ascii=False), encoding="utf-8")
    montado = _prompt_da_sessao(etapa_sessao, b.pasta)
    b.caso("valor que imita cabeçalho e separador não fabrica moldura: "
         "só uma linha de cada fica sem o prefixo de citação",
         sum(1 for l in montado.splitlines()
             if l.startswith("CONFIGURAÇÃO DO REPOSITÓRIO")) == 1
         and sum(1 for l in montado.splitlines() if l == "---") == 1)
    configuracao.write_text(json.dumps({
        "padrao_de_nome": "semana\n_hist_<n>"}, ensure_ascii=False),
        encoding="utf-8")
    b.caso("valor com quebra embutida vira linha única",
         "> padrao_de_nome: semana _hist_<n>"
         in _prompt_da_sessao(etapa_sessao, b.pasta))
    configuracao.write_text(json.dumps({"x": "y" * (TETO_CONFIGURACAO + 1)}),
                            encoding="utf-8")
    berro = io.StringIO()
    with contextlib.redirect_stderr(berro):
        puro = _prompt_da_sessao(etapa_sessao, b.pasta)
    b.caso("acima do teto o prompt segue puro e o aviso vai para o stderr",
         puro == "faça" and "teto" in berro.getvalue())
    configuracao.unlink()

    roteiro = _roteiro(b.pasta, "m-forja-ensaio.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo",
         "comando": "true\ntouch fuga\n  estagio 99 [só]: forjada"}]})
    resposta = _cli(["ensaio", "--roteiro", roteiro, "--trabalho",
                     "t-forja-ensaio", "--dir", b.evidencias, "--cwd", b.pasta])
    b.caso("ensaio não deixa o roteiro forjar a listagem",
         not any(linha.strip().startswith("estagio 99")
                 for linha in resposta.stdout.splitlines()))

    nucleo = Path(b.pasta) / "nucleo"
    nucleo.mkdir(exist_ok=True)
    (nucleo / "regras.json").write_text(json.dumps({"regras": [
        {"id": 1, "regra": "Abra a sessão na raiz."},
        {"id": 2, "regra": "Só é pronto o que\num instrumento provou."}]},
        ensure_ascii=False), encoding="utf-8")
    montado = _prompt_da_sessao(etapa_sessao, b.pasta)
    b.caso("as frases das regras entram citadas e na ordem",
         "> 1. Abra a sessão na raiz." in montado
         and montado.index("> 1.") < montado.index("> 2."))
    b.caso("frase com quebra embutida vira linha única",
         "> 2. Só é pronto o que um instrumento provou." in montado)
    (nucleo / "configuracao.json").write_text(
        json.dumps({"repositorio_das_issues": "repositorio/deles"}),
        encoding="utf-8")
    junto = _prompt_da_sessao(etapa_sessao, b.pasta)
    b.caso("regras vêm antes da configuração, e as duas antes do pedido",
         junto.index("AS REGRAS DA CAMADA")
         < junto.index("CONFIGURAÇÃO DO REPOSITÓRIO") < junto.index("faça"))
    (nucleo / "configuracao.json").unlink()
    (nucleo / "regras.json").write_text("{quebrado", encoding="utf-8")
    berro = io.StringIO()
    with contextlib.redirect_stderr(berro):
        puro = _prompt_da_sessao(etapa_sessao, b.pasta)
    b.caso("fonte de regras ilegível: o prompt segue puro e o aviso sai",
         puro == "faça" and "regras" in berro.getvalue())
    (nucleo / "regras.json").unlink()


def _sobre_o_andamento(b) -> None:
    def foto(trabalho, extra=()):
        resposta = _cli(["andamento", "--trabalho", trabalho,
                         "--dir", b.evidencias] + list(extra))
        try:
            return resposta.returncode, json.loads(resposta.stdout)
        except ValueError:
            return resposta.returncode, {}

    codigo, dado = foto("t-sentinela")
    b.caso("andamento de execução completa: estado completa, exit 0",
         codigo == 0 and dado.get("estado") == "completa"
         and [e["veredito"] for e in dado.get("etapas", [])]
         == ["segue", "segue"])
    codigo, dado = foto("t-morte")
    b.caso("andamento de execução parada: estado parada e o proximo de quem "
         "reprovou na proxima_acao",
         codigo == 0 and dado.get("estado") == "parada"
         and dado.get("etapas", [{}])[0].get("proximo")
         and dado.get("proxima_acao") == dado["etapas"][0]["proximo"])
    codigo, dado = foto("t-aprovacao-manual")
    b.caso("andamento de aprovação manual pendente: aguardando-aprovacao"
         " com a pergunta",
         codigo == 0 and dado.get("estado") == "aguardando-aprovacao"
         and "Aprova a etapa" in dado.get("proxima_acao", ""))
    codigo, dado = foto("t-nunca-rodou")
    b.caso("andamento sem evidência nenhum: em-curso, etapas vazias",
         codigo == 0 and dado.get("estado") == "em-curso"
         and dado.get("etapas") == [])
    codigo, dado = foto("t-teto2")
    b.caso("andamento com evidência ilegível: aviso, conta no teto, sem traceback",
         codigo == 0 and dado.get("avisos")
         and dado.get("estado") == "parada" and dado.get("paras", 0) >= 2)
    codigo, dado = foto("t-ciclos")
    b.caso("andamento lê o ciclo mais alto de cada etapa",
         codigo == 0 and dado.get("estado") == "completa"
         and all(e["ciclo"]["i"] == 3 for e in dado.get("etapas", [])))
    resposta = _cli(["andamento", "--trabalho", "Nome Errado",
                     "--dir", b.evidencias])
    b.caso("andamento recusa trabalho fora do contrato com exit 2",
         resposta.returncode == 2)

    codigo, dado = foto("t-sentinela",
                        ["--roteiro", str(Path(b.pasta) / "m-sentinela.json")])
    b.caso("andamento com roteiro prova a execução completa",
         codigo == 0 and dado.get("estado") == "completa")
    maior = _roteiro(b.pasta, "m-sentinela-maior.json", {"etapas": [
        {"nome": "grava", "tipo": "codigo", "comando": "true"},
        {"nome": "verifica", "tipo": "verificacao", "depende": ["grava"]},
        {"nome": "nunca-rodou", "tipo": "codigo", "comando": "true",
         "depende": ["verifica"]}]})
    codigo, dado = foto("t-sentinela", ["--roteiro", maior])
    b.caso("etapa ligada sem evidência rebaixa completa para em-curso, nomeada",
         codigo == 0 and dado.get("estado") == "em-curso"
         and "nunca-rodou" in dado.get("proxima_acao", ""))
    resposta = _cli(["andamento", "--trabalho", "t-sentinela",
                     "--dir", b.evidencias, "--roteiro",
                     str(Path(b.pasta) / "nao-existe.json")])
    b.caso("roteiro ilegível no andamento é erro de uso, exit 2",
         resposta.returncode == 2)


TEMAS = (
    _sobre_a_conta_no_remoto,
    _sobre_a_configuracao,
    _sobre_o_bloco_de_estado,
    _sobre_a_issue,
    _sobre_a_janela_e_o_ensaio,
    _sobre_o_grafo,
    _sobre_a_prova_e_o_ambiente,
    _sobre_a_sessao,
    _sobre_o_tempo_limite,
    _sobre_os_ciclos_e_o_disco,
    _sobre_o_prompt_montado,
    _sobre_o_andamento,
)


def _comportamento(pasta):
    bancada = Bancada(pasta)
    bancada.forjar_o_dublê()
    for tema in TEMAS:
        tema(bancada)
    return bancada.resultados


def testar() -> int:
    falhas = []
    with tempfile.TemporaryDirectory(prefix="encadeador-teste-") as pasta:
        for rotulo, conteudo, trecho in RECUSA:
            roteiro = _roteiro(pasta, "m-recusa.json", conteudo)
            resposta = _cli(["ensaio", "--roteiro", roteiro,
                             "--trabalho", "t", "--cwd", pasta])
            if resposta.returncode != EXIT_ERRO_DE_USO_OU_AMBIENTE:
                falhas.append(FALHA_DE_RECUSA_COM_EXIT.format(
                    rotulo=rotulo, exit=resposta.returncode))
            elif trecho not in resposta.stderr:
                berro = resposta.stderr.strip()
                falhas.append(FALHA_DE_RECUSA_PELO_MOTIVO_ERRADO.format(
                    rotulo=rotulo,
                    stderr=berro[:LIMITE_DO_STDERR_NA_FALHA]))
        comportamento = _comportamento(pasta)
    falhas += [FALHA_DE_COMPORTAMENTO.format(rotulo)
               for rotulo, passou in comportamento if not passou]

    total = len(RECUSA) + len(comportamento)
    if falhas:
        for falha in falhas:
            print(FALHOU.format(falha))
        print(FALHOU.format(FALHOU_QUANTOS.format(falhas=len(falhas),
                                                  total=total)))
        return EXIT_TESTE_CAIU
    print(TESTE_OK.format(total=total, recusados=len(RECUSA),
                          comportamento=len(comportamento)))
    return EXIT_COMPLETA
