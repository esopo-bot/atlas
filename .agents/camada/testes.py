import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import camada as a_camada
from camada import (
    regras_da_pasta, PASTA_DE_REGRAS,
    medidas_da_versao, custo_por_entrega,
    MEDIDA_VERSAO, MEDIDA_LARGADA, MEDIDA_CUSTO, MEDIDA_ROTA,
    MEDIDA_CUSTO_SEM_EXECUCAO, MEDIDA_CUSTO_MEDIDO,
    MARCA_DE_BANCADA_AUSENTE,
    FORA_DA_PROVA,
    REGISTRO_DA_INSTALACAO,
    ARQUIVO_DE_CONFIGURACAO,
    ARQUIVO_SETTINGS,
    BANDEIRA_DE_TESTE,
    CAMPO_DA_CHAVE,
    CAMPO_DO_ARQUIVO,
    CAMPO_DO_MOTIVO,
    ARQUIVO_DO_LANCADOR,
    CHAVE_DAS_EXCECOES_SEM_LEITOR,
    CHAVE_DA_MAQUINA,
    CHAVE_DOS_GANCHOS,
    CHAVE_DO_COMANDO,
    CHAVE_DO_REPOSITORIO,
    CHAVE_POR_INCORPORACAO,
    CHAVE_DAS_BRANCHES,
    CHAVE_DA_INTEGRACAO,
    COMANDO_DOS_GANCHOS_RASTREADOS,
    EVENTO_DE_ABERTURA,
    EXCECAO_DECLARADA,
    FONTE_DAS_REGRAS,
    INSTALADOR,
    INSTALADOR_DE_MENTIRA,
    INSTRUMENTOS_QUE_FICAM,
    INSTRUMENTO_DE_MODULO_DE_MENTIRA,
    INTERPRETADOR,
    INTERPRETADOR_NO_SHELL,
    NUMEROS,
    NUMERO_NAO_MEDIDO,
    ORCAMENTO_DAS_BANCADAS_TOCADAS,
    TEMPO_DE_UMA_BANCADA_TOCADA,
    PASTAS_DE_INSTRUMENTO_NO_RASCUNHO,
    PASTA_DAS_EVIDENCIAS,
    PASTA_DAS_SKILLS_FONTE,
    GANCHO_DO_DESPACHANTE,
    PASTA_DOS_GANCHOS,
    SALDO_MATCHER_DIVERGENTE,
    BRIEFING_DA_SESSAO,
    SAIDA_FORA_DO_UTF8,
    divergencias_do_despachante,
    PASTA_DOS_INSTRUMENTOS,
    PASTA_DOS_MODULOS,
    PASTA_DOS_SUBAGENTES,
    PASTA_DO_CONHECIMENTO,
    PERGUNTA_DA_VERSAO,
    PILHA_NAO_CLASSIFICADO,
    PILHA_SEM_LEITOR,
    PROVAS,
    RAIZ_NO_COMANDO,
    RASCUNHO,
    SALDO_DESLIGADO,
    SALDO_EXCECAO_VELHA,
    SALDO_ORFA,
    SALDO_SEM_DECLARACAO,
    SALDO_SEM_LEITOR,
    SEGUNDOS_DO_DIA,
    SKILL_ACIMA_DO_TETO,
    SUFIXO_DO_EXEMPLO,
    SUPOSTO_SEM_SIMULACAO,
    TETO_DE_DIAS_NO_RASCUNHO,
    TETO_DO_CORPO_DA_SKILL,
    VERSAO_QUE_SERVE,
    VIA_DA_PROSA,
    VIA_DO_CODIGO,
    VIA_DO_LINK,
    VIA_DO_MODULO,
    VIA_DO_ROTEIRO,
    arquivos_do_rascunho,
    bancada_dos_tocados,
    orcamento_das_bancadas,
    teto_desta_bancada,
    e_desvio_de_caminho,
    MARCA_DE_PONTO_DE_DESVIO,
    ETIQUETA_DE_PONTO_DE_MONTAGEM,
    ETIQUETA_DE_LINK_SIMBOLICO,
    branch_de_incorporacao,
    branches_de_longa_duracao,
    branches_ja_entregues,
    caminhos_que_a_sessao_tocou,
    casos_da_suite,
    catalogo_e_corpo,
    chaves,
    chaves_declaradas,
    declarados_fora_do_git,
    caminho_que_o_git_ignora,
    colher_json,
    conta,
    corre,
    custo_das_execucoes,
    custo_por_etapa,
    de_quem_e_a_chave,
    entrega,
    onde_a_issue_nasce,
    arvores_de_trabalho,
    UMA_ARVORE_SO,
    ARVORES_NAO_MEDIDAS,
    abertura,
    instrucoes_da_raiz,
    servidores_de_contexto,
    estado_do_cliente_sobre_os_servidores,
    ESTADO_DO_CLIENTE_AUSENTE,
    ARQUIVO_DE_ESTADO_DO_CLIENTE,
    ARQUIVO_DE_AUTENTICACAO_PENDENTE,
    CHAVE_DOS_PROJETOS_DO_CLIENTE,
    CHAVE_DOS_SERVIDORES_DESLIGADOS,
    indice_da_abertura,
    ARQUIVO_DAS_INSTRUCOES,
    ARQUIVO_DA_DECLARACAO_DE_MCP,
    ARQUIVO_DOS_ALVOS_DO_INDICE,
    INSTRUMENTO_DO_INDICE,
    BUSCADOR_DO_INDICE,
    ARQUIVO_DO_EXECUTOR,
    veredito_da_entrega,
    SAIDA_LIMPA,
    SAIDA_COM_ACHADO,
    SAIDA_NAO_MEDIDO,
    esquecidos_no_rascunho,
    ganchos_ligados_fora_do_git,
    comando_do_pedido_aberto,
    integracao_declarada,
    o_que_espera_incorporacao,
    candidatos_do_lancador,
    interpretador_com_nome_portatil,
    interpretadores_que_somem,
    julgar_a_simulacao,
    largada,
    leitores_da_configuracao,
    marcas_da_chave,
    markdown,
    matricula,
    matricula_do_instalador,
    medir,
    nome_curto_da_branch,
    o_que_ainda_nao_saiu,
    o_que_saiu_e_ficou,
    onde_a_marca_aparece,
    pecas_de_instrumento,
    perguntas,
    pilhas_do_markdown,
    provar,
    quantas_regras,
    rascunho,
    rastreados_por_git,
    referencia_que_existe,
    saldos_da_matricula,
    saldos_dos_instrumentos,
    subagentes,
    teste_toca_o_proprio_codigo,
    teto_da_largada,
    um_numero,
    versao_da_camada,
)


def ligar_ganchos(raiz: Path, caminhos: list) -> None:
    blocos = [{CHAVE_DOS_GANCHOS: [{
        "type": "command",
        CHAVE_DO_COMANDO: f'python "{RAIZ_NO_COMANDO}/{c}"'}]}
        for c in caminhos]
    destino = raiz / ARQUIVO_SETTINGS
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps({CHAVE_DOS_GANCHOS: {EVENTO_DE_ABERTURA: blocos}}),
        encoding="utf-8")


RAIZ_DA_CAMADA = Path(__file__).resolve().parents[2]


def executavel_de_mentira(pasta: Path, nome: str, no_posix: str,
                          no_windows: str) -> Path:
    if os.name == "nt":
        alvo = pasta / f"{nome}.cmd"
        alvo.write_text(f"@echo off\r\n{no_windows}\r\n", encoding="utf-8")
        return alvo
    alvo = pasta / nome
    alvo.write_text(f"#!/bin/sh\n{no_posix}\n", encoding="utf-8")
    alvo.chmod(0o755)
    return alvo


def interpretador_que_nao_roda(pasta: Path, nome: str) -> Path:
    return executavel_de_mentira(pasta, nome, "exit 9", "exit /b 9")


def interpretador_que_roda_de_mentira(pasta: Path, nome: str) -> Path:
    return executavel_de_mentira(pasta, nome,
                                 f'exec "{sys.executable}" "$@"',
                                 f'"{sys.executable}" %*')


INSTRUMENTO_QUE_PASSA = (
    "import sys\n"
    "print('OK: 1 caso')\n"
    f"sys.exit(0 if '{BANDEIRA_DE_TESTE}' in sys.argv else 1)\n")
INSTRUMENTO_QUE_CAI = (
    "import sys\n"
    "print('FALHOU: 1 de 1 casos')\n"
    f"sys.exit(1 if '{BANDEIRA_DE_TESTE}' in sys.argv else 0)\n")
INSTRUMENTO_QUE_DEMORA = (
    "import sys\n"
    "import time\n"
    f"time.sleep(30 if '{BANDEIRA_DE_TESTE}' in sys.argv else 0)\n")
INSTRUMENTO_UM_POUCO_LERDO = (
    "import sys\n"
    "import time\n"
    f"time.sleep(2 if '{BANDEIRA_DE_TESTE}' in sys.argv else 0)\n"
    "print('OK: 1 casos')\n")
INSTRUMENTO_SEM_BANCADA = "valor = 1\n"
ORCAMENTO_QUE_SO_DA_PARA_UMA = 0.001
TETO_QUE_NENHUMA_BANCADA_LENTA_ALCANCA = 1
ASSINATURA_DE_MENTIRA = ("-c user.name=t -c user.email=t@t "
                         "-c commit.gpgsign=false")


def arvore_com_instrumentos_de_mentira(onde: Path) -> Path:
    pecas = onde / PASTA_DOS_INSTRUMENTOS / "pecas"
    pecas.mkdir(parents=True)
    (onde / "nucleo").mkdir()
    (onde / ARQUIVO_DE_CONFIGURACAO).write_text(
        json.dumps({CHAVE_POR_INCORPORACAO: ["main"]}), encoding="utf-8")
    (pecas / "verde.py").write_text(INSTRUMENTO_QUE_PASSA, encoding="utf-8")
    (pecas / "vermelho.py").write_text(INSTRUMENTO_QUE_CAI, encoding="utf-8")
    (pecas / "mudo.py").write_text(INSTRUMENTO_SEM_BANCADA, encoding="utf-8")
    corre(f'git init -q -b main && git add -A '
          f'&& git {ASSINATURA_DE_MENTIRA} commit -qm um', cwd=onde)
    corre("git checkout -q -b trabalho", cwd=onde)
    return pecas


def criar_atalho_de_pasta(destino: Path, atalho: Path) -> bool:
    try:
        os.symlink(destino, atalho, target_is_directory=True)
        return True
    except (OSError, NotImplementedError, AttributeError):
        pass
    if os.name != "nt":
        return False
    feito = subprocess.run(["cmd", "/c", "mklink", "/J", str(atalho),
                            str(destino)], capture_output=True, text=True)
    return feito.returncode == 0 and atalho.exists()


def testar() -> int:
    falhas, casos = [], []

    def caso(rotulo, passou):
        casos.append(rotulo)
        if not passou:
            falhas.append(rotulo)

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        (raiz / "AGENTS.md").write_bytes(b"abc\n")
        (raiz / PASTA_DO_CONHECIMENTO).mkdir()
        (raiz / PASTA_DOS_GANCHOS).mkdir(parents=True)
        skill = raiz / PASTA_DAS_SKILLS_FONTE / "s"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: s\ndescription: faz algo\n---\n\ncorpo longo aqui\n",
            encoding="utf-8")

        (raiz / INSTALADOR).write_text('VERSAO = "1.2"\n', encoding="utf-8")
        (raiz / PASTA_DOS_MODULOS).mkdir()
        medidas_medidas = dict(medidas_da_versao(raiz))
        caso("as medidas da versão medem a largada e confessam o que não "
             "mediram — versão sem git, custo sem execução e rota sem rodada; "
             "a VERSAO que sobrou no montar.py não conta",
             medidas_medidas[MEDIDA_VERSAO] == NUMERO_NAO_MEDIDO
             and medidas_medidas[MEDIDA_LARGADA].endswith("sem teto declarado")
             and medidas_medidas[MEDIDA_CUSTO] == MEDIDA_CUSTO_SEM_EXECUCAO
             and medidas_medidas[MEDIDA_ROTA].startswith("não medido"))
        (raiz / PASTA_DOS_MODULOS).rmdir()
        registro = raiz / REGISTRO_DA_INSTALACAO
        registro.parent.mkdir(parents=True)
        registro.write_text(json.dumps({"versao": "0.9",
                                        "commit_da_camada": "abc1234"}),
                            encoding="utf-8")
        caso("numa instalação, sem modulos/, a versão é o commit que o "
             "registro da instalação guarda, e não o montar.py antigo que "
             "sobrou na raiz nem o número velho do registro",
             dict(medidas_da_versao(raiz))[MEDIDA_VERSAO]
             == "commit abc1234")
        (raiz / PASTA_DOS_MODULOS).mkdir()
        caso("destino com registro segue destino mesmo tendo pasta própria "
             "chamada modulos/: a versão continua saindo do registro",
             dict(medidas_da_versao(raiz))[MEDIDA_VERSAO]
             == "commit abc1234")
        (raiz / PASTA_DOS_MODULOS).rmdir()
        registro.unlink()
        with tempfile.TemporaryDirectory(
                prefix="camada-versao-na-casa-") as outra_pasta:
            casa = Path(outra_pasta)
            (casa / PASTA_DOS_MODULOS).mkdir()
            (casa / PASTA_DOS_MODULOS / "LEIAME.md").write_text(
                "m\n", encoding="utf-8")
            corre(f'git init -q && git add -A '
                  f'&& git {ASSINATURA_DE_MENTIRA} commit -qm um', cwd=casa)
            _, ponta = corre("git rev-parse --short HEAD", cwd=casa)
            caso("na casa da camada, a versão é o commit da árvore",
                 bool(ponta.strip())
                 and versao_da_camada(casa) == f"commit {ponta.strip()}")
        caso("o custo por entrega é a mediana do cobrado por execução, com o "
             "buraco de atribuição em porcentagem — nunca a soma, que cresce "
             "com o número de execuções",
             custo_por_entrega([("a", 1.0, 1.0), ("b", 3.0, 0.0),
                                ("c", 10.0, 10.0)])
             == MEDIDA_CUSTO_MEDIDO.format(3.0, 3, 100 * 3.0 / 14.0))
        (raiz / INSTALADOR).unlink()

        regras = raiz / PASTA_DE_REGRAS
        regras.mkdir(parents=True)
        (regras / "sempre.md").write_text("# sempre\n", encoding="utf-8")
        (regras / "codigo.md").write_text(
            '---\npaths:\n  - "**/*.py"\n---\n\n# só com código\n' + "x" * 100,
            encoding="utf-8")
        sempre, por_caminho = regras_da_pasta(raiz)
        caso("regra sem paths entra na largada; regra por caminho fica fora, "
             "porque só carrega quando o arquivo tocado bate com o padrão",
             sempre == len("# sempre\n") and por_caminho > 100
             and medir(raiz)[1]["regras_por_caminho"] == por_caminho
             and medir(raiz)[1]["instrucoes"] >= sempre)
        (regras / "sempre.md").unlink()
        (regras / "codigo.md").unlink()

        _, dados = medir(raiz)
        caso("a largada soma instruções mais catálogo, nunca o corpo",
             dados["largada"] == 4 + len("- s: faz algo\n".encode()))

        injecao = "regra que o gancho injeta\n"
        (raiz / "gancho.py").write_text(
            "import json\n"
            "print(json.dumps({'hookSpecificOutput': "
            "{'additionalContext': %r}}))\n" % injecao,
            encoding="utf-8")
        (raiz / ".claude").mkdir(exist_ok=True)
        (raiz / ".claude" / "settings.json").write_text(
            json.dumps({"hooks": {"SessionStart": [{"hooks": [
                {"type": "command", "command":
                 f'{INTERPRETADOR_NO_SHELL} "${{CLAUDE_PROJECT_DIR}}/gancho.py"'}]}]}}),
            encoding="utf-8")
        _, com_gancho = medir(raiz)
        caso("o gancho de abertura entra na conta",
             com_gancho["injetado_por_gancho"] == len(injecao.encode()))
        caso("e a largada cresce exatamente o que ele injeta",
             com_gancho["largada"]
             == dados["largada"] + len(injecao.encode()))
        (raiz / "gancho.py").write_text("", encoding="utf-8")
        calado = medir(raiz)[1]
        caso("gancho que RODA e fica CALADO vale zero, não cego",
             calado["injetado_por_gancho"] == 0
             and calado["ganchos_nao_medidos"] == 0)
        (raiz / "gancho.py").write_text(
            "print('nao sou json')\n", encoding="utf-8")
        torto = medir(raiz)[1]
        caso("gancho que RODA e fala TORTO conta como não medido, "
             "nunca zero calado",
             torto["injetado_por_gancho"] == 0
             and torto["ganchos_nao_medidos"] == 1)
        (raiz / "gancho.py").write_text("import sys\nsys.exit(1)\n",
                                        encoding="utf-8")
        caso("gancho que CAI não derruba a medida, e conta como cego",
             medir(raiz)[1]["injetado_por_gancho"] == 0
             and medir(raiz)[1]["ganchos_nao_medidos"] == 1)
        pasta_dos_ganchos = raiz / ".claude" / "hooks"
        a_pasta_ja_existia = pasta_dos_ganchos.is_dir()
        pasta_dos_ganchos.mkdir(parents=True, exist_ok=True)
        (pasta_dos_ganchos / "gancho-sem-variavel.py").write_text(
            "import json\n"
            "print(json.dumps({'hookSpecificOutput': "
            "{'additionalContext': %r}}))\n" % injecao,
            encoding="utf-8")
        so_pelo_ambiente = (
            "import os,sys,runpy;"
            "a=os.path.join(os.environ['CLAUDE_PROJECT_DIR'],sys.argv[1]);"
            "sys.argv=[a];runpy.run_path(a,run_name='__main__')")
        (raiz / ".claude" / "settings.json").write_text(
            json.dumps({"hooks": {"SessionStart": [{"hooks": [
                {"type": "command", "command":
                 f'{INTERPRETADOR_NO_SHELL} -c "{so_pelo_ambiente}" '
                 '.claude/hooks/gancho-sem-variavel.py'}]}]}}),
            encoding="utf-8")
        sem_variavel = medir(raiz)[1]
        caso("gancho sem variável no texto do comando recebe a raiz pelo "
             "ambiente e entra na conta da largada",
             sem_variavel["injetado_por_gancho"] == len(injecao.encode())
             and sem_variavel["ganchos_nao_medidos"] == 0)
        (pasta_dos_ganchos / "gancho-sem-variavel.py").unlink()
        if not a_pasta_ja_existia:
            shutil.rmtree(pasta_dos_ganchos)
        (raiz / ".claude" / "settings.json").write_text(
            json.dumps({"hooks": {"SessionStart": [{"hooks": [
                {"type": "command",
                 "command": "binario-que-nao-existe-nenhum"}]}]}}),
            encoding="utf-8")
        caso("gancho que NÃO RODOU é contado como não medido",
             medir(raiz)[1]["ganchos_nao_medidos"] == 1)
        with contextlib.redirect_stdout(io.StringIO()):
            cega = largada(raiz)
        caso("largada com gancho de abertura que não respondeu não dá "
             "veredito: sai não medida, nem dentro nem acima do teto",
             cega == SAIDA_NAO_MEDIDO)
        sem_briefing = medir(raiz)[1]
        briefing = raiz / BRIEFING_DA_SESSAO
        briefing.parent.mkdir(parents=True, exist_ok=True)
        briefing.write_text("b" * 700, encoding="utf-8")
        com_briefing = medir(raiz)[1]
        caso("o briefing que o AGENTS.md manda ler inteiro entra na "
             "largada, byte a byte",
             com_briefing["briefing"] == 700
             and com_briefing["largada"] == sem_briefing["largada"] + 700)
        briefing.unlink()
        (raiz / ".claude" / "settings.json").write_text(
            json.dumps({"hooks": {}}), encoding="utf-8")
        caso("o corpo da skill fica no adiado", dados["adiado"] > 0)
        caso("conta as skills", dados["skills"] == 1)

        anexo = skill / "references" / "molde.md"
        anexo.parent.mkdir()
        anexo.write_text("m" * 500, encoding="utf-8")
        com_anexo = medir(raiz)[1]
        caso("o conteúdo de references/ entra no corpo adiado",
             com_anexo["adiado"] == dados["adiado"] + 500)
        caso("skill dentro do teto não é acusada",
             com_anexo["skills_acima_do_teto"] == 0)
        anexo.write_text("m" * (TETO_DO_CORPO_DA_SKILL + 1), encoding="utf-8")
        linhas_do_teto, gorda = medir(raiz)
        caso("skill acima do teto do corpo é acusada",
             gorda["skills_acima_do_teto"] == 1)
        caso("a acusação nomeia a skill e o peso dela",
             any(SKILL_ACIMA_DO_TETO.format("s", gorda["adiado"]) in linha
                 for linha in linhas_do_teto))
        anexo.unlink()
        anexo.parent.rmdir()

        listada, corpo = catalogo_e_corpo(skill / "SKILL.md")
        caso("o catálogo é nome e descrição", listada == "- s: faz algo\n")
        caso("o corpo é o que sobra do frontmatter", corpo > 0)

        sem_frente = raiz / "solta.md"
        sem_frente.write_text("só corpo\n", encoding="utf-8")
        caso("skill sem frontmatter não vira catálogo",
             catalogo_e_corpo(sem_frente)[0] == "")

        gancho = raiz / PASTA_DOS_GANCHOS / "g.py"
        gancho.write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
        _, prova = provar(raiz)
        caso("gancho sem --testar é acusado", prova["sem_teste"] == 1)
        gancho.write_text(
            "import sys\nif '--testar' in sys.argv:\n"
            "    print('OK: 1 caso')\n    sys.exit(0)\n",
            encoding="utf-8")
        _, prova = provar(raiz)
        caso("gancho com --testar que passa não é acusado", prova["caem"] == 0)
        (raiz / INSTALADOR).write_text("import sys\nsys.exit(1)\n",
                                       encoding="utf-8")
        linhas_da_prova, prova = provar(raiz)
        caso("numa instalação, sem modulos/, a prova não roda o montar.py "
             "antigo que sobrou na raiz: ele não é a origem, e cairia por "
             "estar velho; a linha diz de onde a instalação se verifica",
             prova["caem"] == 0
             and any(FORA_DA_PROVA in l and INSTALADOR in l
                     for l in linhas_da_prova))
        (raiz / PASTA_DOS_MODULOS).mkdir()
        registro_da_prova = raiz / REGISTRO_DA_INSTALACAO
        registro_da_prova.parent.mkdir(parents=True, exist_ok=True)
        registro_da_prova.write_text(
            json.dumps({"commit_da_camada": "abc1234"}), encoding="utf-8")
        linhas_da_prova, prova = provar(raiz)
        caso("destino com registro e pasta própria modulos/ também não roda "
             "o montar.py antigo da raiz",
             prova["caem"] == 0
             and any(FORA_DA_PROVA in l and INSTALADOR in l
                     for l in linhas_da_prova))
        registro_da_prova.unlink()
        (raiz / PASTA_DOS_MODULOS).rmdir()
        (raiz / INSTALADOR).write_text('VERSAO = "1.2"\n', encoding="utf-8")

        bancada_que_ficou = raiz / PASTA_DOS_INSTRUMENTOS / "i" / "i.py"
        bancada_que_ficou.parent.mkdir(parents=True)
        bancada_que_ficou.write_text(
            "import sys\nif '--testar' in sys.argv:\n"
            f"    print('{MARCA_DE_BANCADA_AUSENTE}: ficou')\n    sys.exit(0)\n",
            encoding="utf-8")
        linhas_da_prova, prova = provar(raiz)
        caso("instrumento cujo --testar diz que a bancada não viaja fica "
             "FORA da conta — nem OK, nem caído: não há o que provar aqui",
             prova["caem"] == 0 and prova["fora"] == 1
             and any(FORA_DA_PROVA in l and "i.py" in l for l in linhas_da_prova))
        bancada_que_ficou.unlink()

        gancho.write_text(
            "import sys\nif '--testar' in sys.argv:\n    sys.exit(0)\n",
            encoding="utf-8")
        _, prova = provar(raiz)
        caso("gancho que sai 0 sem provar caso nenhum é acusado, não "
             "carimbado OK — silêncio não é prova",
             prova["caem"] == 1)
        gancho.write_text(
            "import sys\nif '--testar' in sys.argv:\n    sys.exit(1)\n",
            encoding="utf-8")
        _, prova = provar(raiz)
        caso("gancho com --testar que cai é acusado", prova["caem"] == 1)
        gancho.write_text(
            "import sys\nif '--testar' in sys.argv:\n"
            "    print('OK: 1 caso')\n", encoding="utf-8")
        sem_o_modo = raiz / PASTA_DOS_INSTRUMENTOS / "modo" / "modo.py"
        sem_o_modo.parent.mkdir(parents=True)
        sem_o_modo.write_text(
            "import sys\nif '--testar' in sys.argv:\n"
            "    sys.exit(1 if sys.flags.utf8_mode else print('OK: 1 caso'))\n",
            encoding="utf-8")
        _, prova = provar(raiz)
        caso("a prova roda cada instrumento sem o modo UTF-8 do Python, como "
             "a máquina que não o liga", prova["caem"] == 0)
        sem_o_modo.unlink()
        sem_o_modo.parent.rmdir()
        gancho.write_text(
            "import sys\nif '--testar' in sys.argv:\n"
            "    print('OK: 1 caso, ação')\n", encoding="utf-8")
        _, prova = provar(raiz)
        caso("gancho roda na prova com o -X utf8 da linha dele, e a saída "
             "com acento sai inteira", prova["caem"] == 0)
        acentuado = raiz / PASTA_DOS_INSTRUMENTOS / "acento" / "acento.py"
        acentuado.parent.mkdir(parents=True)
        acentuado.write_text(
            "import sys\nif '--testar' in sys.argv:\n"
            "    print('OK: 1 caso, ação')\n", encoding="utf-8")
        linhas_da_prova, prova = provar(raiz)
        caso("instrumento que passa mas escreve fora do UTF-8 cai na prova, "
             "e a linha diz por quê",
             prova["caem"] == 1
             and any(SAIDA_FORA_DO_UTF8 in l and "acento.py" in l
                     for l in linhas_da_prova))
        acentuado.unlink()
        acentuado.parent.rmdir()

        pasta_de_subagentes = raiz / PASTA_DOS_SUBAGENTES
        pasta_de_subagentes.mkdir(parents=True, exist_ok=True)
        caso("sem subagente nenhum, conta zero e não acusa coleira",
             subagentes(raiz) == ([], []))
        (pasta_de_subagentes / "com-coleira.md").write_text(
            "---\nname: a\ndescription: faz\ntools: Read, Grep\n---\n",
            encoding="utf-8")
        (pasta_de_subagentes / "sem-coleira.md").write_text(
            "---\nname: b\ndescription: faz\n---\n", encoding="utf-8")
        achados, soltos = subagentes(raiz)
        caso("conta os subagentes do disco", len(achados) == 2)
        caso("acusa só o que herda tudo, e diz qual",
             soltos == ["sem-coleira.md"])
        _, com_subagentes = medir(raiz)
        caso("a medida carrega os dois números",
             com_subagentes["subagentes"] == 2
             and com_subagentes["subagentes_sem_coleira"] == 1)
        falso = raiz / "bin-de-mentira"
        falso.mkdir(exist_ok=True)
        interpretador_que_nao_roda(falso, "python3")
        interpretador_que_roda_de_mentira(falso, "interpretador-de-mentira")
        antes_do_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{falso}{os.pathsep}{antes_do_path}"
        interpretador_com_nome_portatil.cache_clear()
        escolhido = interpretador_com_nome_portatil(RAIZ_DA_CAMADA)
        interpretador_com_nome_portatil.cache_clear()
        caso("python3 que existe e NAO roda é descartado — é o atalho "
             "da loja do Windows, e foi assim que a camada caiu lá",
             escolhido != "python3")
        caso("e o escolhido no lugar dele roda mesmo",
             corre(f"{escolhido} -c \"{PERGUNTA_DA_VERSAO}\"")[1].strip()
             == VERSAO_QUE_SERVE)
        lancador_de_mentira = raiz / ARQUIVO_DO_LANCADOR
        lancador_de_mentira.parent.mkdir(parents=True, exist_ok=True)
        lancador_de_mentira.write_text(
            'CANDIDATOS="interpretador-de-mentira"\n', encoding="utf-8")
        caso("a lista de candidatos mora no lançador, e só nele: outro "
             "lançador, outro nome escolhido",
             interpretador_com_nome_portatil(raiz)
             == "interpretador-de-mentira")
        interpretador_com_nome_portatil.cache_clear()
        os.environ["PATH"] = antes_do_path
        nome = interpretador_com_nome_portatil(RAIZ_DA_CAMADA)
        caso("o interpretador portátil é um dos nomes que o lançador da "
             "camada lista, não um caminho",
             nome in candidatos_do_lancador(RAIZ_DA_CAMADA))
        caso("e o nome escolhido roda mesmo um Python 3",
             corre(f"{nome} -c \"{PERGUNTA_DA_VERSAO}\"")[1].strip()
             == VERSAO_QUE_SERVE)
        caso("o que executa por dentro é o intérprete desta sessão",
             INTERPRETADOR == sys.executable
             and INTERPRETADOR_NO_SHELL.strip('"') == sys.executable)
        caso("sem teto declarado, mede e não cobra",
             teto_da_largada(raiz) is None and largada(raiz) == 0)
        (raiz / "nucleo").mkdir(exist_ok=True)
        (raiz / "nucleo" / "configuracao.json").write_text(
            json.dumps({"teto_da_largada_em_bytes": 1}), encoding="utf-8")
        caso("teto apertado reprova, e diz o número",
             teto_da_largada(raiz) == 1 and largada(raiz) == 1)
        (raiz / "nucleo" / "configuracao.json").write_text(
            json.dumps({"teto_da_largada_em_bytes": 10 ** 9}),
            encoding="utf-8")
        caso("teto folgado passa", largada(raiz) == 0)
        (raiz / "nucleo" / "configuracao.json").write_text(
            json.dumps({"teto_da_largada_em_bytes": "muito"}),
            encoding="utf-8")
        caso("teto que não é número não vira cobrança",
             teto_da_largada(raiz) is None)

        evid = raiz / PASTA_DAS_EVIDENCIAS / "issue-9"
        evid.mkdir(parents=True)

        def _evidencia(nome, etapa, usd=None, duracao=None, turnos=None):
            corpo = {"etapa": etapa, "trabalho": "issue-9",
                     "quando": "2026-09-02T10:00:00-03:00",
                     "veredito": "segue", "provado": [], "suposto": [],
                     "faltas": [], "ciclo": {"i": 1, "teto": 2}}
            if usd is not None:
                corpo["custo"] = {"usd": usd, "tokens": {
                    "entrada": 1, "saida": 1,
                    "cache-lido": 1, "cache-criado": 1}}
            if duracao is not None:
                corpo["duracao"] = duracao
            if turnos is not None:
                corpo["turnos"] = turnos
            (evid / nome).write_text(json.dumps(corpo), encoding="utf-8")

        _evidencia("01-trabalhar-c1.json", "trabalhar", 2.0, 100.0, 3)
        _evidencia("01-trabalhar-c2.json", "trabalhar", 3.0, 200.0, 4)
        _evidencia("02-revisar-c1.json", "revisar", 1.0, 50.0, 1)
        _evidencia("03-entregar-c1.json", "entregar")
        _evidencia("04-medir-c1.json", "medir", 0.25)
        (evid / "issue-9.log").write_text(
            '"total_cost_usd":6.5 "num_turns":8', encoding="utf-8")

        por_etapa = dict((e[0], e[1:]) for e in custo_por_etapa(raiz))
        caso("a conta soma por etapa, e o ciclo repetido aparece somado",
             por_etapa["trabalhar"][:2] == (5.0, 2))
        caso("e a duração de cada etapa soma junto",
             por_etapa["trabalhar"][2] == 300.0)
        caso("etapa sem custo medido não vira zero na tabela",
             "entregar" not in por_etapa)

        linhas = dict((l[0], l[1:]) for l in custo_das_execucoes(raiz))
        caso("a execução mostra o cobrado no log e o atribuído à etapa",
             linhas["issue-9"][:2] == (6.5, 6.25))
        caso("a diferença é confessada, não escondida: o que a evidência "
             "perdeu foi sessão que morreu sem evidência",
             round(linhas["issue-9"][0] - linhas["issue-9"][1], 2) == 0.25)

        antiga = raiz / PASTA_DAS_EVIDENCIAS / "issue-1"
        antiga.mkdir(parents=True)
        (antiga / "issue-1.log").write_text('"total_cost_usd":40.0',
                                            encoding="utf-8")
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            conta(raiz)
        dito = saida.getvalue()
        caso("execução sem atribuição nenhuma não entra no buraco, e a "
             "rotina não afirma qual das duas causas é: ela não sabe",
             "US$ 40.00 em 1 execução(ões) ficam fora" in dito
             and "US$ 0.25 de US$ 6.50" in dito
             and "não dá para separar as duas" in dito)
        sobrando = raiz / PASTA_DAS_EVIDENCIAS / "issue-8"
        sobrando.mkdir(parents=True)
        (sobrando / "issue-8.log").write_text('"total_cost_usd":0.10',
                                              encoding="utf-8")
        corpo = {"etapa": "trabalhar", "trabalho": "issue-8",
                 "quando": "2026-09-02T10:00:00-03:00", "veredito": "segue",
                 "provado": [], "suposto": [], "faltas": [],
                 "ciclo": {"i": 1, "teto": 2},
                 "custo": {"usd": 9.0, "tokens": {
                     "entrada": 1, "saida": 1,
                     "cache-lido": 1, "cache-criado": 1}}}
        (sobrando / "01-trabalhar-c1.json").write_text(json.dumps(corpo),
                                                       encoding="utf-8")
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            conta(raiz)
        caso("etapa que soma MAIS que o log não vira conta fechada: "
             "discordância se diz nos dois sentidos",
             "A MAIS do que" in saida.getvalue())
        caso("etapa sem duração medida diz que não mediu, em vez de "
             "imprimir zero minuto",
             "sem relógio" in dito)


        bom = raiz / "bom.py"
        bom.write_text("def somar(n):\n    return sum(n)\n"
                       "def testar():\n    assert somar([1]) == 1\n",
                       encoding="utf-8")
        ruim = raiz / "ruim.py"
        ruim.write_text("def testar():\n    assert sum([1]) == 1\n",
                        encoding="utf-8")
        caso("teste que chama função do arquivo conta",
             teste_toca_o_proprio_codigo(bom))
        caso("teste que só usa embutido não conta",
             not teste_toca_o_proprio_codigo(ruim))
        na_guarda = raiz / "na-guarda.py"
        na_guarda.write_text(
            'import sys\ndef somar(n):\n    return sum(n)\n'
            'if "--testar" in sys.argv:\n    assert somar([1]) == 1\n'
            '    sys.exit(0)\n', encoding="utf-8")
        caso("teste na guarda da bandeira também conta — o repositório mede o que o "
             "teste FAZ, não onde ele mora",
             teste_toca_o_proprio_codigo(na_guarda))
        guarda_vazia = raiz / "guarda-vazia.py"
        guarda_vazia.write_text(
            'import sys\ndef somar(n):\n    return sum(n)\n'
            'if "--testar" in sys.argv:\n    assert 1 + 1 == 2\n'
            '    sys.exit(0)\n', encoding="utf-8")
        caso("teste na guarda que não chama o arquivo segue não contando",
             not teste_toca_o_proprio_codigo(guarda_vazia))
        assincrono = raiz / "assincrono.py"
        assincrono.write_text(
            "async def buscar(n):\n    return n\n"
            "async def testar():\n    assert await buscar(1) == 1\n",
            encoding="utf-8")
        caso("teste assíncrono que chama função do arquivo conta",
             teste_toca_o_proprio_codigo(assincrono))
        mista = raiz / "mista.py"
        mista.write_text(
            "async def buscar(n):\n    return n\n"
            "def testar():\n    assert buscar(1)\n",
            encoding="utf-8")
        caso("teste comum que chama função assíncrona do arquivo conta",
             teste_toca_o_proprio_codigo(mista))

        fonte_das_regras = raiz / FONTE_DAS_REGRAS
        caso("sem a fonte das regras, não medido em vez de zero",
             quantas_regras(raiz) is None)
        fonte_das_regras.write_text(
            json.dumps({"regras": [{"id": 1}, {"id": 2}, {"id": 3}]}),
            encoding="utf-8")
        caso("com a fonte sã, a contagem sai da fonte",
             quantas_regras(raiz) == 3)
        fonte_das_regras.write_text('{"regras": [', encoding="utf-8")
        caso("regras corrompidas viram não medido, nunca zero",
             quantas_regras(raiz) is None)
        fonte_das_regras.write_text('{"outra": []}', encoding="utf-8")
        caso("fonte sem a chave das regras também é não medido",
             quantas_regras(raiz) is None)
        fluxo = io.StringIO()
        with contextlib.redirect_stdout(fluxo):
            um_numero(raiz, "regras-da-camada")
        caso("e quem imprime o número diz não medido, nunca 0",
             fluxo.getvalue().strip() == NUMERO_NAO_MEDIDO)
        fonte_das_regras.unlink()

    caso("o JSON sai de dentro de cerca de código",
         colher_json('```json\n{"a": 1}\n```') == {"a": 1})
    caso("texto sem JSON devolve vazio", colher_json("nada aqui") == {})
    caso("objeto com lista dentro não é confundido com fluxo de eventos — "
         "esta é a regressão que apagou a resposta do modelo e deixou a "
         "acurácia em 2 de 8 sem dizer por quê",
         colher_json('texto {"onde": "raiz", "itens": [1, 2]} fim')
         == {"onde": "raiz", "itens": [1, 2]})
    caso("do fluxo de eventos da sessão headless sai o evento do resultado, "
         "não o primeiro",
         colher_json('[{"type": "system"}, {"type": "result", '
                     '"result": "ok", "num_turns": 3}]').get("num_turns") == 3)
    caso("e o aviso impresso antes do fluxo não apaga o resultado",
         colher_json('Warning: servidor bloqueado\n'
                     '[{"type": "system"}, {"type": "result", '
                     '"result": "ok"}]').get("result") == "ok")
    caso("fluxo sem evento de resultado devolve o último objeto, nunca vazio",
         colher_json('[{"type": "system"}, {"type": "assistant", "i": 2}]')
         .get("i") == 2)
    gabarito = {p[1]: p[2] for p in perguntas(14)}
    caso("commitar: 'não' passa", gabarito["posso_commitar"](
        {"posso_commitar": "não — sem autorização declarada"}))
    caso("commitar: 'sim' não passa", not gabarito["posso_commitar"](
        {"posso_commitar": "sim, pode"}))
    caso("as regras se contam pelo número da fonte",
         gabarito["quantas_regras"]({"quantas_regras": 14})
         and not gabarito["quantas_regras"]({"quantas_regras": 13}))
    caso("a acurácia não entra em provado: ela varia sozinha",
         all(chave != "acertos-da-simulacao"
             for _, chave in PROVAS["simular"]))
    caso("mas a simulação prova algo determinístico, senão segue sem prova",
         PROVAS["simular"] != ()
         and all(NUMEROS[chave][0] != "simular"
                 for _, chave in PROVAS["simular"]))

    def resumo_de(certas, caidas):
        return {"rodou": True, "acertos": certas + 2 - len(caidas), "casos": 8,
                "certas_do_nucleo": certas, "casos_do_nucleo": 6,
                "caidas_do_nucleo": ["abre na raiz"] * (6 - certas),
                "caidas_do_artefato": caidas, "turnos": 5, "segundos": 40.0,
                "dolar": 0.07}

    caso("as 6 determinísticas certas seguem, mesmo com o artefato caído",
         julgar_a_simulacao(resumo_de(6, ["o --testar exercita o código"]))[0]
         == [])
    caso("a checagem do artefato que cai vira suposto, com o nome",
         any("o --testar exercita o código" in dito
             for dito in julgar_a_simulacao(
                 resumo_de(6, ["o --testar exercita o código"]))[1]))
    caso("determinística errada derruba a etapa, e a falta diz qual",
         julgar_a_simulacao(resumo_de(5, []))[0]
         and "abre na raiz" in julgar_a_simulacao(resumo_de(5, []))[0][0])
    caso("tudo certo não gera falta nem suposto de artefato",
         julgar_a_simulacao(resumo_de(6, []))[0] == []
         and len(julgar_a_simulacao(resumo_de(6, []))[1]) == 1)
    caso("simulação que não rodou não inventa falta",
         julgar_a_simulacao({"rodou": False}) == ([], [SUPOSTO_SEM_SIMULACAO]))
    caso("toda prova declarada tem número que a imprime",
         all(chave in NUMEROS for provas in PROVAS.values()
             for _, chave in provas))

    with tempfile.TemporaryDirectory(prefix="camada-quadro-") as quadro:
        onde = Path(quadro)
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            sem_arquivo = onde_a_issue_nasce(onde)
        caso("sem o arquivo do executor, a rotina do quadro ACUSA e diz o que "
             "fazer, em vez de calar",
             sem_arquivo == 1 and ARQUIVO_DO_EXECUTOR in dito.getvalue())

        alvo = onde / ARQUIVO_DO_EXECUTOR
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(
            json.dumps({"issues": {"repositorio": "${DONO}/${QUADRO}"}}),
            encoding="utf-8")
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            por_preencher = onde_a_issue_nasce(onde)
        caso("endereço por preencher não conta como declarado",
             por_preencher == 1)

        alvo.write_text(
            json.dumps({"issues": {"repositorio": "quem-instala/o-quadro"}}),
            encoding="utf-8")
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            declarado = onde_a_issue_nasce(onde)
        caso("com o endereço declarado, a rotina imprime o endereço e sai zero",
             declarado == 0 and "quem-instala/o-quadro" in dito.getvalue())

        alvo.write_text("{ isto nao e json", encoding="utf-8")
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            ilegivel = onde_a_issue_nasce(onde)
        caso("arquivo ilegível acusa, em vez de estourar",
             ilegivel == 1)

    with tempfile.TemporaryDirectory(prefix="camada-arvores-") as arvores:
        base = Path(arvores).resolve()
        sozinho = base / "sozinho"
        sozinho.mkdir()
        assinatura = ("-c user.name=t -c user.email=t@t "
                      "-c commit.gpgsign=false")
        corre(f'git init -q -b main && echo a > a.txt && git add -A '
              f'&& git {assinatura} commit -qm um', cwd=sozinho)
        caso("com uma árvore só, a entrega diz que a medida vale para ela",
             arvores_de_trabalho(sozinho) == UMA_ARVORE_SO)
        corre(f'git worktree add -q "{base / "ao-lado"}" -b outra',
              cwd=sozinho)
        dito = arvores_de_trabalho(sozinho)
        caso("com duas árvores, a entrega conta as árvores, cita a hora e "
             "avisa que não se declara estado final de árvore compartilhada",
             "2 árvores" in dito and "ao-lado" in dito
             and "estado final" in dito)
        caso("fora de repositório, a contagem de árvores é NÃO MEDIDA, nunca "
             "uma",
             arvores_de_trabalho(base / "nao-existe")
             == ARVORES_NAO_MEDIDAS)

    with tempfile.TemporaryDirectory(prefix="camada-abertura-") as vazia:
        onde = Path(vazia)
        caso("sem o arquivo de instruções, a abertura diz que a sessão não "
             "está na raiz — é a regra 1, e quem abre fora dela não carrega "
             "instrução nenhuma",
             instrucoes_da_raiz(onde)[0] is False)
        (onde / ARQUIVO_DAS_INSTRUCOES).write_text("regras", encoding="utf-8")
        caso("com o arquivo de instruções na pasta, a peça está de pé",
             instrucoes_da_raiz(onde)[0] is True)

        caso("declaração de servidor ausente NÃO é falta: repositório que não "
             "usa servidor de contexto abre íntegro",
             servidores_de_contexto(onde)[0] is None)
        principal = onde / "principal"
        principal.mkdir()
        corre("git init -q -b main && git -c user.name=t -c user.email=t@t "
              "-c commit.gpgsign=false commit -q --allow-empty -m um",
              cwd=principal)
        (principal / ARQUIVO_DA_DECLARACAO_DE_MCP).write_text(
            json.dumps({"mcpServers": {"do-projeto": {}}}), encoding="utf-8")
        ligada = onde / "ligada"
        corre(f'git worktree add -q --detach "{ligada}"', cwd=principal)
        sem_arquivo_na_ligada, dito_na_ligada = servidores_de_contexto(ligada)
        caso("worktree sem declaração, com a raiz principal declarando, não "
             "é falta, e a linha diz os servidores de lá e que o que a "
             "sessão carrega depende do cliente",
             sem_arquivo_na_ligada is None and "do-projeto" in dito_na_ligada
             and "raiz principal" in dito_na_ligada)
        alvo_do_mcp = onde / ARQUIVO_DA_DECLARACAO_DE_MCP
        alvo_do_mcp.write_text("{ isto nao e json", encoding="utf-8")
        caso("declaração ilegível é falta, e a razão nomeia o arquivo",
             servidores_de_contexto(onde)[0] is False
             and ARQUIVO_DA_DECLARACAO_DE_MCP
             in servidores_de_contexto(onde)[1])
        alvo_do_mcp.write_text(json.dumps({"mcpServers": {}}),
                               encoding="utf-8")
        caso("declaração que existe e não declara servidor nenhum é falta — "
             "o arquivo está lá e não serve para nada",
             servidores_de_contexto(onde)[0] is False)
        alvo_do_mcp.write_text(
            json.dumps({"mcpServers": {"segundo": {}, "primeiro": {}}}),
            encoding="utf-8")
        de_pe, dito = servidores_de_contexto(onde)
        caso("com servidor declarado, a peça está de pé e a linha lista os "
             "nomes em ordem, nunca o valor de variável nenhuma",
             de_pe is True and "primeiro, segundo" in dito)
        casa = onde / "casa"
        casa.mkdir()
        caso("sem estado do cliente na casa, a abertura diz que não há o que "
             "ler sobre os servidores — sem inventar conexão",
             ESTADO_DO_CLIENTE_AUSENTE.split("{")[0]
             in estado_do_cliente_sobre_os_servidores(
                 onde, ["primeiro", "segundo"], casa=casa))
        (casa / ARQUIVO_DE_ESTADO_DO_CLIENTE).write_text(json.dumps({
            CHAVE_DOS_PROJETOS_DO_CLIENTE: {
                str(onde): {CHAVE_DOS_SERVIDORES_DESLIGADOS: ["segundo"]},
                str(onde / "outra"): {
                    CHAVE_DOS_SERVIDORES_DESLIGADOS: ["primeiro"]}}}),
            encoding="utf-8")
        dito = estado_do_cliente_sobre_os_servidores(
            onde, ["primeiro", "segundo"], casa=casa)
        caso("servidor declarado que o cliente desligou neste projeto vai "
             "nomeado na abertura; o desligado de outro projeto não conta",
             "segundo" in dito and "desligou" in dito
             and "primeiro" not in dito)
        (casa / ARQUIVO_DE_AUTENTICACAO_PENDENTE).parent.mkdir(
            parents=True, exist_ok=True)
        (casa / ARQUIVO_DE_AUTENTICACAO_PENDENTE).write_text(
            json.dumps({"primeiro": {"id": "x"}, "de-fora": {"id": "y"}}),
            encoding="utf-8")
        dito = estado_do_cliente_sobre_os_servidores(
            onde, ["primeiro", "segundo"], casa=casa)
        caso("servidor declarado que o cliente marca como pedindo "
             "autenticação vai nomeado; o que não é deste repositório não",
             "primeiro" in dito and "autentica" in dito
             and "de-fora" not in dito)
        (casa / ".claude" / "remote-settings.json").write_text(json.dumps(
            {"allowedMcpServers": [{"serverName": "github"}]}), encoding="utf-8")
        (onde / ".claude").mkdir(exist_ok=True)
        (onde / ".claude" / "settings.local.json").write_text(json.dumps(
            {"allowedMcpServers": [{"serverCommand": ["python", "s.py"]}]}),
            encoding="utf-8")
        alvo_do_mcp.write_text(json.dumps({"mcpServers": {
            "absoluto": {"command": "python", "args": ["D:/a/s.py"]},
            "relativo": {"command": "python", "args": ["s.py"]}}}),
            encoding="utf-8")
        _, com_lista = servidores_de_contexto(onde, casa=casa)
        caso("a lista permitida casa o comando exato: servidor cujo comando não "
             "casa é acusado como barrado, e o que casa não — o caminho "
             "absoluto some em silêncio contra o relativo da lista",
             "barra" in com_lista and "absoluto" in com_lista
             and "relativo" not in com_lista.split("barra", 1)[1].split("\n", 1)[0])
        (onde / ".claude" / "settings.local.json").unlink()
        (casa / ".claude" / "remote-settings.json").unlink()
        _, sem_lista = servidores_de_contexto(onde, casa=casa)
        caso("sem lista permitida em fonte nenhuma, nada é acusado como barrado",
             "barra" not in sem_lista)
        alvo_do_mcp.write_text(
            json.dumps({"mcpServers": {"segundo": {}, "primeiro": {}}}),
            encoding="utf-8")
        caso("o cliente não guarda conectado nem falhou, e a abertura diz "
             "isso em vez de fingir que mediu a conexão",
             "conectado" in dito.lower())
        de_pe, dito = servidores_de_contexto(onde, casa=casa)
        caso("a linha da declaração carrega o estado do cliente logo abaixo, "
             "e servidor desligado não derruba a peça — é aviso",
             de_pe is True and "desligou" in dito)
        (casa / ARQUIVO_DE_ESTADO_DO_CLIENTE).write_text("{ nao e json",
                                                          encoding="utf-8")
        caso("estado do cliente ilegível não derruba a abertura: a linha "
             "diz que não se deixou ler",
             servidores_de_contexto(onde, casa=casa)[0] is True
             and "não se deixou ler"
             in servidores_de_contexto(onde, casa=casa)[1])

        caso("sem o instrumento do índice, o índice não é cobrado: o módulo "
             "não está instalado, e isso não é falta",
             indice_da_abertura(onde)[0] is None)
        instrumento = onde / INSTRUMENTO_DO_INDICE
        instrumento.parent.mkdir(parents=True, exist_ok=True)
        instrumento.write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
        caso("com o instrumento e sem a lista de alvos, é falta — o indexador "
             "não sabe o que indexar e a busca responde menos do que existe",
             indice_da_abertura(onde)[0] is False
             and ARQUIVO_DOS_ALVOS_DO_INDICE in indice_da_abertura(onde)[1])
        (onde / ARQUIVO_DOS_ALVOS_DO_INDICE).write_text(
            json.dumps({"alvos": []}), encoding="utf-8")
        de_pe, dito = indice_da_abertura(onde)
        caso("com alvos declarados e o estado saindo zero, a peça está de pé "
             "e a linha ensina o buscador local, para quem não tem servidor "
             "de contexto",
             de_pe is True and BUSCADOR_DO_INDICE in dito)
        instrumento.write_text("import sys\nsys.exit(1)\n", encoding="utf-8")
        de_pe, dito = indice_da_abertura(onde)
        caso("índice que não responde é falta que NOMEIA o buscador por "
             "termo exato como saída — falhar alto, com o caminho na mão",
             de_pe is False and BUSCADOR_DO_INDICE in dito)

        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            incompleta = abertura(onde)
        caso("a abertura com peça faltando SAI 1 e conta as faltas, em vez de "
             "seguir em silêncio",
             incompleta == 1 and "INCOMPLETA" in dito.getvalue())

        instrumento.write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
        executor = onde / ARQUIVO_DO_EXECUTOR
        executor.parent.mkdir(parents=True, exist_ok=True)
        executor.write_text(
            json.dumps({"issues": {"repositorio": "quem-instala/o-quadro"}}),
            encoding="utf-8")
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            integra = abertura(onde)
        caso("com as quatro peças de pé, a abertura sai zero e diz quantas "
             "provou",
             integra == 0 and "íntegra" in dito.getvalue())

    with tempfile.TemporaryDirectory(prefix="camada-entrega-") as sozinho:
        repositorio = Path(sozinho) / "repositorio"
        repositorio.mkdir()
        assinatura = ("-c user.name=t -c user.email=t@t "
                      "-c commit.gpgsign=false")
        corre(f'git init -q -b main && echo a > a.txt && git add -A && git {assinatura} commit -qm um', cwd=repositorio)
        caso("o comando roda na pasta pedida, mesmo em outro drive",
             Path(corre("git rev-parse --show-toplevel",
                        cwd=repositorio)[1]).resolve() == repositorio.resolve())
        caso("o veredito da entrega separa não-medido de achado: achado "
             "manda, e não-medido só fala quando não há achado nenhum",
             [veredito_da_entrega(a, b)
              for a in (SAIDA_LIMPA, SAIDA_COM_ACHADO, SAIDA_NAO_MEDIDO)
              for b in (SAIDA_LIMPA, SAIDA_COM_ACHADO, SAIDA_NAO_MEDIDO)]
             == [SAIDA_LIMPA, SAIDA_COM_ACHADO, SAIDA_NAO_MEDIDO,
                 SAIDA_COM_ACHADO, SAIDA_COM_ACHADO, SAIDA_COM_ACHADO,
                 SAIDA_NAO_MEDIDO, SAIDA_COM_ACHADO, SAIDA_NAO_MEDIDO])
        caso("sem remoto nenhum, a entrega não se prova",
             entrega(repositorio) == 1)
        remoto = Path(sozinho) / "remoto.git"
        corre(f'git init -q --bare "{remoto}"')
        corre(f'git remote add origin "{remoto}" && git push -q origin HEAD:refs/heads/main', cwd=repositorio)
        caso("tudo empurrado, a entrega está limpa",
             entrega(repositorio) == 0)
        corre(f'echo b > b.txt && git add -A && git {assinatura} commit -qm dois', cwd=repositorio)
        caso("commit que não saiu da máquina reprova",
             entrega(repositorio) == 1)
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            entrega(repositorio)
        primeira_linha = dito.getvalue().strip().splitlines()[0]
        caso("a PRIMEIRA linha da entrega diz a raiz que ela mediu: com "
             "várias árvores de trabalho, veredito sem endereço é lido como "
             "se fosse da árvore de quem perguntou",
             Path(repositorio).name in primeira_linha)
        caso("a entrega diz em DADOS qual das três medidas achou o quê: "
             "fundidas num código só, quem a chama não distingue commit sem "
             "destino de branch por podar e acusa um pelo outro",
             "CATEGORIAS DA ENTREGA: commit-sem-destino=1 "
             "branch-por-podar=0" in dito.getvalue())
        caso("a linha das categorias carrega o NÃO MEDIDO de cada medida, "
             "sem fundi-lo no achado de outra",
             a_camada.linha_das_categorias(
                 SAIDA_LIMPA, SAIDA_NAO_MEDIDO, SAIDA_COM_ACHADO)
             == "CATEGORIAS DA ENTREGA: commit-sem-destino=0 "
                "branch-por-podar=2 integracao-sem-pedido=1")

        corre('git push -q origin HEAD:refs/heads/main', cwd=repositorio)
        corre('git checkout -q -b claude/vazia', cwd=repositorio)
        with contextlib.redirect_stdout(io.StringIO()):
            vazia = o_que_ainda_nao_saiu(repositorio, "claude/vazia")
        caso("branch sem upstream e sem commit próprio, como a que o app cria "
             "para a sessão, não é commit sem destino: tudo o que ela tem já "
             "está no remoto",
             vazia == SAIDA_LIMPA)
        corre(f'echo c > c.txt && git add -A && git {assinatura} commit -qm tres', cwd=repositorio)
        with contextlib.redirect_stdout(io.StringIO()):
            com_commit = o_que_ainda_nao_saiu(repositorio, "claude/vazia")
        caso("a mesma branch, com um commit que só existe aqui, segue acusada",
             com_commit == SAIDA_COM_ACHADO)

    with tempfile.TemporaryDirectory(prefix="camada-poda-") as sozinho:
        repositorio = Path(sozinho) / "repositorio"
        (repositorio / "nucleo").mkdir(parents=True)
        (repositorio / ".claude").mkdir()
        (repositorio / "nucleo" / "configuracao.json").write_text(
            json.dumps({CHAVE_POR_INCORPORACAO: ["main"]}), encoding="utf-8")
        (repositorio / ".claude" / "branches-protegidas.txt").write_text(
            "# as de longa duração\nmain\nhomolog\n", encoding="utf-8")
        assinatura = ("-c user.name=t -c user.email=t@t "
                      "-c commit.gpgsign=false")
        corre(f'git init -q -b main && git add -A && git {assinatura} commit -qm um', cwd=repositorio)
        remoto = Path(sozinho) / "remoto.git"
        corre(f'git init -q --bare "{remoto}"')
        corre(f'git remote add origin "{remoto}" && git push -q origin main', cwd=repositorio)
        protegidas = branches_de_longa_duracao(repositorio)
        caso("a lista de longa duração se lê, sem os comentários",
             protegidas == {"main", "homolog"})
        caso("a branch de incorporação sai da configuração, nunca de palpite",
             branch_de_incorporacao(repositorio) == "main")
        referencia = referencia_que_existe(repositorio, "main")
        caso("a referência preferida é a do remoto, que é a que entregou",
             referencia == "origin/main")

        corre(f'git checkout -q -b entregue && echo b > b.txt && git add -A && git {assinatura} commit -qm dois', cwd=repositorio)
        corre('git push -q origin entregue', cwd=repositorio)
        corre(f'git checkout -q main && git {assinatura} merge -q --no-ff -m mescla entregue && git push -q origin main', cwd=repositorio)
        corre(f'git checkout -q -b viva && echo c > c.txt && git add -A && git {assinatura} commit -qm tres && git checkout -q main', cwd=repositorio)
        chamadas_ao_git, rodar_de_verdade = [], a_camada.subprocess.run

        def rodar_contando(*argumentos, **nomeados):
            chamadas_ao_git.append(str(argumentos[0]))
            return rodar_de_verdade(*argumentos, **nomeados)

        a_camada.subprocess.run = rodar_contando
        try:
            locais, remotas, mediu = branches_ja_entregues(
                repositorio, referencia_que_existe(repositorio, "main"),
                "main", protegidas)
        finally:
            a_camada.subprocess.run = rodar_de_verdade
        caso("a listagem se declara medida quando o git respondeu", mediu)
        caso("a poda lê o topo de toda branch num for-each-ref só, e o "
             "rev-parse fica só para a referência — medido, um rev-parse por "
             "branch pesava segundos em cada parada",
             sum("for-each-ref" in c for c in chamadas_ao_git) == 1
             and sum("rev-parse" in c for c in chamadas_ao_git) == 2)
        corre('git remote set-head origin main', cwd=repositorio)
        caso("o ponteiro origin/HEAD, que encurta para o nome do remoto, "
             "não vira branch acusada",
             "origin" not in branches_ja_entregues(
                 repositorio, referencia_que_existe(repositorio, "main"),
                 "main", protegidas)[1])
        caso("git que falha vira NÃO MEDIDO e reprova, nunca acusação falsa",
             branches_ja_entregues(repositorio, "referencia-que-nao-existe",
                                   "main", protegidas)[2] is False
             and o_que_saiu_e_ficou(Path(sozinho) / "sem-git", "main") == 0)
        caso("a branch já entregue é acusada, local e remota",
             locais == ["entregue"] and "origin/entregue" in remotas)
        caso("a branch viva, que ninguém mesclou, NÃO é acusada",
             "viva" not in locais and "origin/viva" not in remotas)
        caso("a de longa duração e a atual não entram na acusação",
             not any(nome_curto_da_branch(b) in ("main", "homolog")
                     for b in locais + remotas))
        caso("branch entregue e de pé reprova a entrega",
             o_que_saiu_e_ficou(repositorio, "main") == 1)
        corre('git branch -q -D entregue && git push -q origin --delete entregue', cwd=repositorio)
        caso("podadas as duas pontas, a entrega fica limpa",
             o_que_saiu_e_ficou(repositorio, "main") == 0)

        corre(f'git checkout -q -b garfo && echo d > d.txt && git add -A && git {assinatura} commit -qm quatro', cwd=repositorio)
        corre(f'git checkout -q main && git {assinatura} merge -q --no-ff -m mescla garfo', cwd=repositorio)
        corre(f'git checkout -q garfo && git {assinatura} merge -q --no-ff -m "no orfao" main && git checkout -q main && git push -q origin main', cwd=repositorio)
        orfaos = branches_ja_entregues(
            repositorio, referencia_que_existe(repositorio, "main"),
            "main", protegidas)[0]
        caso("o no de mescla orfao, cujos pais ja estao na incorporacao, "
             "e acusado — nada dele falta la",
             "garfo" in orfaos)
        corre('git tag garfo garfo', cwd=repositorio)
        com_tag = branches_ja_entregues(
            repositorio, referencia_que_existe(repositorio, "main"),
            "main", protegidas)[0]
        corre('git tag -d garfo', cwd=repositorio)
        caso("branch com tag de mesmo nome sai com o nome da branch, que o "
             "git branch -d aceita e que casa com a branch em uso",
             "garfo" in com_tag and "heads/garfo" not in com_tag)
        corre('git branch -q heads/tarefa main~1 && git tag garfo garfo',
              cwd=repositorio)
        com_prefixo_no_nome = branches_ja_entregues(
            repositorio, referencia_que_existe(repositorio, "main"),
            "main", protegidas)[0]
        corre('git tag -d garfo && git branch -q -D heads/tarefa',
              cwd=repositorio)
        caso("branch que se chama de fato heads/tarefa sai com o nome "
             "inteiro, ao lado da branch com tag homônima: tirar heads/ de "
             "todo nome local que começa com ele cortava o nome dela",
             "heads/tarefa" in com_prefixo_no_nome
             and "tarefa" not in com_prefixo_no_nome
             and "garfo" in com_prefixo_no_nome
             and "heads/garfo" not in com_prefixo_no_nome)
        corre('git checkout -q -b recem-criada && git checkout -q main', cwd=repositorio)
        caso("branch recem-criada, identica ao topo da incorporacao, NAO e "
             "acusada — ali nao ha rastro, ha comeco",
             "recem-criada" not in branches_ja_entregues(
                 repositorio, referencia_que_existe(repositorio, "main"),
                 "main", protegidas)[0])
        corre('git branch -q nova-do-passado main~1', cwd=repositorio)
        acusadas_com_a_nova = branches_ja_entregues(
            repositorio, referencia_que_existe(repositorio, "main"),
            "main", protegidas)[0]
        caso("o limite declarado: branch nova cortada de um ponto anterior ao "
             "topo E acusada, porque o git nao diz em que branch um commit "
             "nasceu — e contar commits proprios nao separa, da zero nos dois",
             "nova-do-passado" in acusadas_com_a_nova
             and "entregue" not in acusadas_com_a_nova
             and corre('git rev-list --count main..nova-do-passado',
                       cwd=repositorio)[1].strip()
             == "0")
        corre('git branch -q -D nova-do-passado', cwd=repositorio)
        caso("a branch viva continua fora da acusacao depois de tudo",
             "viva" not in branches_ja_entregues(
                 repositorio, referencia_que_existe(repositorio, "main"),
                 "main", protegidas)[0])
        corre('git checkout -q --detach main', cwd=repositorio)
        destacada = branches_ja_entregues(
            repositorio, referencia_que_existe(repositorio, "main"),
            "HEAD", protegidas)
        with contextlib.redirect_stdout(io.StringIO()):
            poda_destacada = o_que_saiu_e_ficou(repositorio, "HEAD")
        corre('git checkout -q main', cwd=repositorio)
        caso("em HEAD destacado a poda MEDE: a listagem do git traz uma "
             "linha que não é branch, e antes ela ia ao git diff, falhava e "
             "a poda inteira saía NÃO MEDIDA",
             destacada[2] is True and poda_destacada != SAIDA_NAO_MEDIDO
             and "garfo" in destacada[0])
        corre('git branch -q em-uso main~1', cwd=repositorio)
        arvore_em_uso = Path(sozinho) / "arvore-em-uso"
        corre(f'git worktree add -q "{arvore_em_uso.as_posix()}" em-uso',
              cwd=repositorio)
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            o_que_saiu_e_ficou(repositorio, "main")
        linhas_da_poda = dito.getvalue().splitlines()
        caso("branch entregue mas aberta numa árvore de trabalho sai do "
             "comando de poda e é nomeada à parte: o git não apaga branch "
             "em uso, e o comando que a mandava apagar falhava",
             not any("em-uso" in linha for linha in linhas_da_poda
                     if "git branch -d" in linha)
             and any("em-uso" in linha and "árvore de trabalho" in linha
                     for linha in linhas_da_poda))
        corre(f'git worktree remove --force "{arvore_em_uso.as_posix()}"',
              cwd=repositorio)
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            o_que_saiu_e_ficou(repositorio, "main")
        caso("fechada a árvore, a mesma branch volta ao comando de poda",
             any("em-uso" in linha for linha in dito.getvalue().splitlines()
                 if "git branch -d" in linha))
        corre('git branch -q -D em-uso', cwd=repositorio)
        (repositorio / "nucleo" / "configuracao.json").write_text(
            json.dumps({}), encoding="utf-8")
        caso("sem incorporação declarada é NÃO MEDIDO, nunca zero calado",
             o_que_saiu_e_ficou(repositorio, "main") == 0
             and branch_de_incorporacao(repositorio) == "")

    with tempfile.TemporaryDirectory(prefix="camada-poda-so-em-uso-") as sozinho:
        repositorio = Path(sozinho) / "repositorio"
        (repositorio / "nucleo").mkdir(parents=True)
        (repositorio / "nucleo" / "configuracao.json").write_text(
            json.dumps({CHAVE_POR_INCORPORACAO: ["main"]}), encoding="utf-8")
        assinatura = ("-c user.name=t -c user.email=t@t "
                      "-c commit.gpgsign=false")
        corre(f'git init -q -b main && git add -A && git {assinatura} commit -qm um', cwd=repositorio)
        corre(f'git {assinatura} commit -q --allow-empty -m dois', cwd=repositorio)
        remoto = Path(sozinho) / "remoto.git"
        corre(f'git init -q --bare "{remoto}"')
        corre(f'git remote add origin "{remoto}" && git push -q origin main', cwd=repositorio)
        corre('git branch -q so-em-uso main~1', cwd=repositorio)
        corre('git push -q origin so-em-uso', cwd=repositorio)
        arvore = Path(sozinho) / "arvore-so-em-uso"
        corre(f'git worktree add -q "{arvore.as_posix()}" so-em-uso',
              cwd=repositorio)
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            veredito = o_que_saiu_e_ficou(repositorio, "main")
        caso("quando a única branch entregue está aberta numa árvore, a poda "
             "sai limpa E ainda nomeia a branch em uso — calada, ela some "
             "do relatório justo quando não há mais nada a podar; e a "
             "remota dela também não vira ordem de apagar",
             veredito == SAIDA_LIMPA
             and any("so-em-uso" in linha and "árvore de trabalho" in linha
                     for linha in dito.getvalue().splitlines())
             and "push origin --delete" not in dito.getvalue())

    with tempfile.TemporaryDirectory(prefix="camada-incorporacao-") as sozinho:
        repositorio = Path(sozinho) / "repositorio"
        (repositorio / "nucleo").mkdir(parents=True)
        (repositorio / "nucleo" / "configuracao.json").write_text(
            json.dumps({CHAVE_POR_INCORPORACAO: ["main"]}), encoding="utf-8")
        assinatura = ("-c user.name=t -c user.email=t@t "
                      "-c commit.gpgsign=false")
        corre(f'git init -q -b main && git add -A && git {assinatura} commit -qm um', cwd=repositorio)
        remoto = Path(sozinho) / "remoto.git"
        corre(f'git init -q --bare -b main "{remoto}"')
        corre(f'git remote add origin "{remoto}" && git push -q origin main', cwd=repositorio)
        perguntas_ao_gh = []

        def gh_sem_pedido(raiz, base, cabeca):
            perguntas_ao_gh.append((base, cabeca))
            return []

        def gh_com_pedido(raiz, base, cabeca):
            return [368]

        def gh_que_falhou(raiz, base, cabeca):
            return None

        def ponta(atual, consultar):
            dito = io.StringIO()
            with contextlib.redirect_stdout(dito):
                saida = o_que_espera_incorporacao(repositorio, atual, consultar)
            return saida, dito.getvalue()

        saida, dito = ponta("homolog", gh_sem_pedido)
        caso("sem integração declarada, a ponta pula com uma linha que nomeia "
             "o arquivo e a chave, e não conta como achado",
             saida == SAIDA_LIMPA and ARQUIVO_DO_EXECUTOR in dito
             and f"{CHAVE_DAS_BRANCHES}.{CHAVE_DA_INTEGRACAO}" in dito
             and not perguntas_ao_gh)
        (repositorio / ARQUIVO_DO_EXECUTOR).write_text(
            json.dumps({CHAVE_DAS_BRANCHES: {CHAVE_DA_INTEGRACAO: "homolog"}}),
            encoding="utf-8")
        caso("a integração sai do executor.json, nunca de palpite",
             integracao_declarada(repositorio) == "homolog")
        saida, dito = ponta("main", gh_sem_pedido)
        caso("na própria branch de incorporação a ponta pula: dali não se "
             "pede, se publica",
             saida == SAIDA_LIMPA and "pulado" in dito and not perguntas_ao_gh)
        saida, dito = ponta("homolog", gh_sem_pedido)
        caso("integração que não existe no remoto é NÃO MEDIDO, nunca limpo",
             saida == SAIDA_NAO_MEDIDO and "NÃO MEDIDO" in dito
             and not perguntas_ao_gh)
        corre(f'git checkout -q -b homolog && echo b > b.txt && git add -A && git {assinatura} commit -qm dois && git push -q origin homolog', cwd=repositorio)
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            veredito = entrega(repositorio, gh_sem_pedido)
        caso("o defeito medido: tudo empurrado, a integração à frente da "
             "incorporação e nenhum pedido aberto — a entrega REPROVA, em "
             "vez de dizer que nada ficou para trás",
             veredito == SAIDA_COM_ACHADO and "abra o pedido" in dito.getvalue()
             and "dois" in dito.getvalue())
        caso("a pergunta ao gh leva a incorporação como base e a integração "
             "como cabeça",
             perguntas_ao_gh == [("main", "homolog")])
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            pulado = entrega(repositorio, gh_sem_pedido, sem_pedido=True)
        caso("pedido pulado por quem chama não vai ao gh, diz que pulou, e a "
             "categoria sai 'pulada', nunca zero; o veredito fica com as "
             "outras duas medidas",
             perguntas_ao_gh == [("main", "homolog")]
             and "integracao-sem-pedido=pulada" in dito.getvalue()
             and "pulado a pedido" in dito.getvalue()
             and pulado == SAIDA_LIMPA)
        do_camada = __import__("camada")
        ja_buscou = getattr(do_camada, "quem_chamou_ja_buscou", None)
        caso("existe a marca pela qual quem chama avisa que acabou de buscar",
             callable(ja_buscou))
        if callable(ja_buscou):
            marca = do_camada.MARCA_DA_BUSCA_FEITA_POR_QUEM_CHAMOU
            agora = time.time()
            caso("marca de agora com as duas branches dispensa outra busca",
                 ja_buscou(("homolog", "main"),
                           {marca: f"{agora}|main,homolog"}, agora) is True)
            caso("marca que não trouxe uma das branches não dispensa nada",
                 ja_buscou(("homolog", "main"), {marca: f"{agora}|main"},
                           agora) is False)
            caso("marca velha não dispensa nada: vale só dentro da mesma parada",
                 ja_buscou(("homolog", "main"),
                           {marca: f"{agora - 3600}|main,homolog"}, agora) is False)
            caso("sem marca, ou com marca torta, a ponta busca como sempre",
                 ja_buscou(("homolog", "main"), {}, agora) is False
                 and ja_buscou(("homolog", "main"), {marca: "torta"}, agora) is False)
            corre('git fetch -q origin homolog main', cwd=repositorio)
            corre('git remote set-url origin "D:/remoto-que-nao-existe.git"',
                  cwd=repositorio)
            os.environ[marca] = f"{time.time()}|main,homolog"
            try:
                saida, dito = ponta("homolog", gh_sem_pedido)
            finally:
                os.environ.pop(marca, None)
            caso("com a marca de quem chamou, a ponta mede pelo espelho que "
                 "ele acabou de buscar, sem ir à rede de novo",
                 saida != SAIDA_NAO_MEDIDO and "NÃO MEDIDO" not in dito)
            corre(f'git remote set-url origin "{remoto}"', cwd=repositorio)
            perguntas_ao_gh.clear()
        montado = comando_do_pedido_aberto("main", "homolog")
        caso("o comando montado para o gh põe a base depois de --base e a "
             "cabeça depois de --head — formatar cada pedaço sozinho punha a "
             "base nos dois, e a pergunta voltava vazia parecendo resposta",
             montado[montado.index("--base") + 1] == "main"
             and montado[montado.index("--head") + 1] == "homolog")
        saida, dito = ponta("homolog", gh_com_pedido)
        caso("com pedido aberto o passo seguinte está aberto: a ponta conta "
             "como limpa e nomeia o pedido",
             saida == SAIDA_LIMPA and "esperam o dono no pedido #368" in dito)
        saida, dito = ponta("homolog", gh_que_falhou)
        caso("gh que falta ou falha vira NÃO MEDIDO, nunca 'aberto' nem "
             "'por abrir'",
             saida == SAIDA_NAO_MEDIDO and "NÃO MEDIDO" in dito
             and "abra o pedido" not in dito)
        dono = Path(sozinho) / "dono"
        corre(f'git clone -q "{remoto}" "{dono}"')
        corre(f'git checkout -q main && git {assinatura} merge -q --ff-only origin/homolog && git push -q origin main', cwd=dono)
        perguntas_ao_gh.clear()
        saida, dito = ponta("homolog", gh_sem_pedido)
        caso("a ponta busca o remoto antes de medir: o que o dono já mesclou "
             "não é acusado por ref local velha, e ninguém pergunta ao gh",
             saida == SAIDA_LIMPA and "já contém tudo" in dito
             and not perguntas_ao_gh)

    with tempfile.TemporaryDirectory(prefix="camada-rascunho-") as pasta:
        raiz = Path(pasta)
        (raiz / RASCUNHO).mkdir()
        leiame = raiz / RASCUNHO / "LEIAME.md"
        leiame.write_text("a pasta se explica\n", encoding="utf-8")
        velho = time.time() - (TETO_DE_DIAS_NO_RASCUNHO + 1) * SEGUNDOS_DO_DIA
        os.utime(leiame, (velho, velho))
        corre('git init -q && git add -A', cwd=raiz)
        caso("arquivo rastreado e velho não entra na acusação — "
             "o git é a declaração",
             rascunho(raiz) == 0)

        solto = raiz / RASCUNHO / "esquecido.md"
        solto.write_text("rascunho de uma vez só\n", encoding="utf-8")
        caso("arquivo não rastreado e novo passa", rascunho(raiz) == 0)
        os.utime(solto, (velho, velho))
        caso("arquivo não rastreado parado acima do teto reprova",
             rascunho(raiz) == 1)
        caso("a acusação nomeia o arquivo e a idade dele",
             esquecidos_no_rascunho(arquivos_do_rascunho(raiz), set(), raiz,
                                    time.time())
             == [(f"{RASCUNHO}/LEIAME.md", TETO_DE_DIAS_NO_RASCUNHO + 1),
                 (f"{RASCUNHO}/esquecido.md", TETO_DE_DIAS_NO_RASCUNHO + 1)])

        for nome in PASTAS_DE_INSTRUMENTO_NO_RASCUNHO:
            de_instrumento = raiz / RASCUNHO / nome / "saida.json"
            de_instrumento.parent.mkdir()
            de_instrumento.write_text("{}", encoding="utf-8")
            os.utime(de_instrumento, (velho, velho))
        solto.unlink()
        caso("subpasta de instrumento declarada fica fora da conta",
             rascunho(raiz) == 0)

        pastas_de_marcas = set()
        for fonte in [*(RAIZ_DA_CAMADA / ".claude" / "hooks").glob("*.py"),
                      *(RAIZ_DA_CAMADA / PASTA_DOS_MODULOS).glob(
                          f"*/{PASTA_DOS_INSTRUMENTOS}/**/*.py")]:
            pastas_de_marcas |= set(re.findall(
                r'(?m)^(?:PASTA_MARCAS|CASA) = (?:Path\()?"tmp/([^"/]+)"',
                fonte.read_text(encoding="utf-8", errors="replace")))
        caso("toda pasta que gancho ou módulo declara em tmp/ para as "
             "próprias marcas fica fora da conta do rascunho — fora da "
             "lista, as marcas envelhecem e viram esquecido falso",
             bool(pastas_de_marcas)
             and pastas_de_marcas <= set(PASTAS_DE_INSTRUMENTO_NO_RASCUNHO))

        sem_pasta = raiz / "sem-rascunho"
        sem_pasta.mkdir()
        caso("sem a pasta no disco a rotina cala e não inventa acusação",
             rascunho(sem_pasta) == 0)

    with tempfile.TemporaryDirectory(prefix="camada-rascunho-atalho-") as pasta:
        raiz = Path(pasta)
        (raiz / RASCUNHO).mkdir()
        (raiz / RASCUNHO / "meu.md").write_text("um só\n", encoding="utf-8")
        alheio = raiz / "pasta-de-outro-projeto"
        alheio.mkdir()
        for indice in range(5):
            (alheio / f"{indice}.js").write_text("x", encoding="utf-8")
        atalho = raiz / RASCUNHO / "atalho-para-o-alheio"
        criou = criar_atalho_de_pasta(alheio, atalho)
        caso("esta máquina sabe criar atalho de pasta — sem isso o caso "
             "abaixo não mede nada, e passar seria falso verde",
             criou)
        caso("a contagem do rascunho NÃO atravessa atalho de pasta: contar "
             "através dele inflou 658 arquivos para 90.320, e limpeza que o "
             "siga apaga instalação real de outro projeto",
             [a.name for a in arquivos_do_rascunho(raiz)] == ["meu.md"])
        caso("ponto de desvio é o que REDIRECIONA o caminho, e só isso: "
             "atributo de desvio com etiqueta de outra coisa, como arquivo "
             "guardado na nuvem, continua sendo arquivo que existe",
             e_desvio_de_caminho(MARCA_DE_PONTO_DE_DESVIO,
                                 ETIQUETA_DE_PONTO_DE_MONTAGEM)
             and e_desvio_de_caminho(MARCA_DE_PONTO_DE_DESVIO,
                                     ETIQUETA_DE_LINK_SIMBOLICO)
             and not e_desvio_de_caminho(MARCA_DE_PONTO_DE_DESVIO, 0x9000001A)
             and not e_desvio_de_caminho(0, ETIQUETA_DE_PONTO_DE_MONTAGEM))
        caso("o que não é arquivo comum fica fora da conta: soquete e cano "
             "nomeado parados há dias não são rascunho esquecido",
             all(a.is_file() for a in arquivos_do_rascunho(raiz)))

    with tempfile.TemporaryDirectory(prefix="camada-rascunho-raiz-") as pasta:
        raiz = Path(pasta)
        alheio = raiz / "pasta-de-outro-projeto"
        alheio.mkdir()
        for indice in range(3):
            (alheio / f"{indice}.js").write_text("x", encoding="utf-8")
        criou = criar_atalho_de_pasta(alheio, raiz / RASCUNHO)
        caso("a própria pasta de rascunho sendo um atalho também não se "
             "atravessa — o detector olhava só os filhos dela",
             criou and arquivos_do_rascunho(raiz) is None)
        corre("git init -q && git add -A", cwd=raiz)
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            veredito = rascunho(raiz)
        caso("e não atravessar NÃO é rascunho em dia: a rotina diz NÃO MEDIDO "
             "e reprova, porque zero aqui seria invenção — lista vazia por "
             "não ter olhado tem a mesma cara de lista vazia por não haver "
             "nada",
             veredito == 1 and "NÃO MEDIDO" in dito.getvalue()
             and "atalho" in dito.getvalue())

    with tempfile.TemporaryDirectory(prefix="camada-rascunho-cego-") as pasta:
        raiz = Path(pasta)
        (raiz / RASCUNHO).mkdir()
        (raiz / RASCUNHO / "solto.md").write_text("x", encoding="utf-8")
        caso("git que não responde vira NÃO MEDIDO, nunca rascunho em dia",
             rascunho(raiz) == 1)

    with tempfile.TemporaryDirectory(prefix="camada-matricula-") as pasta:
        raiz = Path(pasta)
        (raiz / PASTA_DOS_GANCHOS).mkdir(parents=True)
        (raiz / INSTALADOR).write_text(INSTALADOR_DE_MENTIRA,
                                       encoding="utf-8")
        gancho = raiz / PASTA_DOS_GANCHOS / "bom.py"
        gancho.write_text("", encoding="utf-8")
        ligar_ganchos(raiz, [f"{PASTA_DOS_GANCHOS}/bom.py"])
        for caminho in INSTRUMENTOS_QUE_FICAM:
            (raiz / caminho).parent.mkdir(parents=True, exist_ok=True)
            (raiz / caminho).write_text("", encoding="utf-8")
        corre('git init -q && git add -A', cwd=raiz)
        caso("gancho rastreado, embutido e declarado não vira saldo",
             matricula(raiz) == 0)
        (raiz / ARQUIVO_SETTINGS).write_text(json.dumps({CHAVE_DOS_GANCHOS: {
            EVENTO_DE_ABERTURA: [{CHAVE_DOS_GANCHOS: [{
                "type": "command",
                CHAVE_DO_COMANDO: 'python -c "import os,runpy" '
                                  f'{PASTA_DOS_GANCHOS}/bom.py'}]}]}}),
            encoding="utf-8")
        corre('git add -A', cwd=raiz)
        caso("gancho ligado sem variável no texto do comando, com o caminho "
             "como argumento, também é reconhecido pela matrícula",
             matricula(raiz) == 0)
        ligar_ganchos(raiz, [f"{PASTA_DOS_GANCHOS}/bom.py"])
        corre('git add -A', cwd=raiz)

        instrumento = raiz / INSTRUMENTO_DE_MODULO_DE_MENTIRA
        instrumento.parent.mkdir(parents=True)
        instrumento.write_text("", encoding="utf-8")
        corre('git add -A', cwd=raiz)
        caso("instrumento que chega por módulo não vira saldo",
             matricula(raiz) == 0)
        (raiz / INSTALADOR).write_text(
            INSTALADOR_DE_MENTIRA
            + "MODULOS = {'m': {'.agents/mod/outro.py': ''}}\n",
            encoding="utf-8")
        caso("a matrícula segue o leitor da camada, não a carga embutida: "
             "quando os dois discordam, o instrumento que o leitor põe no "
             "módulo não vira saldo",
             matricula(raiz) == 0)
        (raiz / INSTALADOR).write_text(INSTALADOR_DE_MENTIRA,
                                       encoding="utf-8")
        instrumento.rename(instrumento.with_name("fora.py"))
        corre('git add -A', cwd=raiz)
        caso("instrumento rastreado fora do FONTES é acusado de não viajar",
             matricula(raiz) == 1)
        privado = raiz / "modulos" / "segredo"
        (privado / PASTA_DOS_INSTRUMENTOS / "mod").mkdir(parents=True)
        (privado / PASTA_DOS_INSTRUMENTOS / "mod" / "fora.py").write_text(
            "", encoding="utf-8")
        caso("sem a marca, o instrumento do módulo continua acusado",
             matricula(raiz) == 1)
        (privado / "MODULO_PRIVADO").write_text("privado", encoding="utf-8")
        caso("com a marca de módulo privado, o instrumento dele fica de "
             "propósito e não vira saldo",
             matricula(raiz) == 0)
        shutil.rmtree(raiz / "modulos")
        corre(f'git rm -q --cached "{PASTA_DOS_INSTRUMENTOS}/mod/fora.py"',
              cwd=raiz)
        instrumento.with_name("fora.py").unlink()

        fontes, declarados, por_modulo = matricula_do_instalador(raiz)[0]
        caso("instrumento que fica neste repositório não vira saldo",
             saldos_dos_instrumentos(raiz, sorted(INSTRUMENTOS_QUE_FICAM),
                                     fontes, por_modulo) == [])
        caso("exceção declarada e fora do git é acusada de envelhecida",
             saldos_dos_instrumentos(raiz, [], fontes, por_modulo)
             == [(c, SALDO_EXCECAO_VELHA)
                 for c in sorted(INSTRUMENTOS_QUE_FICAM)])

        solto = raiz / PASTA_DOS_GANCHOS / "novo.py"
        solto.write_text("", encoding="utf-8")
        corre('git add -A', cwd=raiz)
        caso("gancho rastreado fora do FONTES é acusado de não viajar",
             matricula(raiz) == 1)
        corre(f'git rm -q --cached "{PASTA_DOS_GANCHOS}/novo.py"', cwd=raiz)
        caso("tirado do git, o mesmo arquivo cala a rotina",
             matricula(raiz) == 0)
        solto.unlink()

        gancho.unlink()
        corre(f'git rm -q --cached "{PASTA_DOS_GANCHOS}/bom.py"', cwd=raiz)
        caso("matrícula sem arquivo no disco é acusada de órfã",
             saldos_da_matricula(raiz, [], fontes, declarados)
             == [(f"{PASTA_DOS_GANCHOS}/bom.py", SALDO_ORFA)])
        gancho.write_text("", encoding="utf-8")
        corre('git add -A', cwd=raiz)

        ligar_ganchos(raiz, [f"{PASTA_DOS_GANCHOS}/bom.py",
                             f"{PASTA_DOS_GANCHOS}/nao-declarado.py"])
        caso("ligado no settings.json sem GanchoDeclarado é acusado",
             saldos_da_matricula(raiz, [], fontes, declarados)
             == [(f"{PASTA_DOS_GANCHOS}/nao-declarado.py",
                  SALDO_SEM_DECLARACAO)])
        ligar_ganchos(raiz, [f"{PASTA_DOS_GANCHOS}/bom.py"])

        ligar_ganchos(raiz, [])
        caso("declarado no instalador e desligado do settings.json é "
             "acusado — a matrícula cobra os dois lados",
             saldos_da_matricula(raiz, [], fontes, declarados)
             == [(f"{PASTA_DOS_GANCHOS}/bom.py", SALDO_DESLIGADO)])

        (raiz / GANCHO_DO_DESPACHANTE).write_text(
            'CERCAS = (\n    ("bom", "Bash"),\n)\n', encoding="utf-8")
        caso("despachante que existe mas não está ligado não avaliza cerca "
             "nenhuma — a cerca desligada segue sendo saldo",
             saldos_da_matricula(raiz, [], fontes, declarados)
             == [(f"{PASTA_DOS_GANCHOS}/bom.py", SALDO_DESLIGADO)])
        ligar_ganchos(raiz, [GANCHO_DO_DESPACHANTE])
        caso("cerca que o despachante ligado roda deixa de ser saldo, e o "
             "próprio despachante segue devendo declaração",
             saldos_da_matricula(raiz, [], fontes, declarados)
             == [(GANCHO_DO_DESPACHANTE, SALDO_SEM_DECLARACAO)])
        caso("matcher diferente entre o despachante e o instalador é "
             "acusado — a duplicação fica, derivar em silêncio não",
             divergencias_do_despachante(raiz)
             == [(f"{PASTA_DOS_GANCHOS}/bom.py", SALDO_MATCHER_DIVERGENTE)])
        (raiz / GANCHO_DO_DESPACHANTE).write_text(
            'CERCAS = (\n    ("bom", ""),\n)\n', encoding="utf-8")
        caso("matcher igual nos dois lugares não é acusado",
             divergencias_do_despachante(raiz) == [])
        (raiz / INSTALADOR).write_text(
            INSTALADOR_DE_MENTIRA
            + "GANCHO_BOM_ANTES_DA_FERRAMENTA = GanchoDeclarado(\n"
              "    'bom', 'PreToolUse', 'Read',\n"
              "    'python \"${CLAUDE_PROJECT_DIR}/.claude/hooks/bom.py\"',\n"
              "    '.claude/hooks/bom.py')\n"
              "GANCHO_BOM_NO_FIM_DE_TURNO = GanchoDeclarado(\n"
              "    'bom', 'Stop', '',\n"
              "    'python \"${CLAUDE_PROJECT_DIR}/.claude/hooks/bom.py\"',\n"
              "    '.claude/hooks/bom.py')\n", encoding="utf-8")
        (raiz / GANCHO_DO_DESPACHANTE).write_text(
            'CERCAS = (\n    ("bom", "Read"),\n)\n', encoding="utf-8")
        caso("gancho declarado em DOIS eventos se compara com o despachante "
             "pela declaração de antes da ferramenta: o matcher vazio do fim "
             "de turno não é divergência, é outro evento",
             divergencias_do_despachante(raiz) == [])
        (raiz / GANCHO_DO_DESPACHANTE).write_text(
            'CERCAS = (\n    ("bom", "Bash"),\n)\n', encoding="utf-8")
        caso("e a divergência de verdade, no evento certo, segue acusada",
             divergencias_do_despachante(raiz)
             == [(f"{PASTA_DOS_GANCHOS}/bom.py", SALDO_MATCHER_DIVERGENTE)])
        (raiz / INSTALADOR).write_text(INSTALADOR_DE_MENTIRA,
                                       encoding="utf-8")
        (raiz / GANCHO_DO_DESPACHANTE).write_text(
            'CERCAS = (\n    ("bom", ""),\n)\n', encoding="utf-8")
        (raiz / GANCHO_DO_DESPACHANTE).unlink()
        caso("sem despachante no disco não há divergência a acusar",
             divergencias_do_despachante(raiz) == [])
        ligar_ganchos(raiz, [])

        gancho.unlink()
        caso("declarado, desligado e SEM arquivo no disco sai uma vez só, "
             "como órfã — o saldo novo não duplica a acusação",
             saldos_da_matricula(raiz, [], fontes, declarados)
             == [(f"{PASTA_DOS_GANCHOS}/bom.py", SALDO_ORFA)])
        gancho.write_text("", encoding="utf-8")
        ligar_ganchos(raiz, [f"{PASTA_DOS_GANCHOS}/bom.py"])

        (raiz / INSTALADOR).write_text("(", encoding="utf-8")
        caso("instalador que não compila vira NÃO MEDIDO, não zero",
             matricula(raiz) == 1
             and matricula_do_instalador(raiz)[0] is None)
        (raiz / INSTALADOR).unlink()
        caso("sem instalador nenhum, não há matrícula a cobrar",
             matricula(raiz) == 0)

    with tempfile.TemporaryDirectory(prefix="camada-chaves-") as pasta:
        raiz = Path(pasta)
        leitor = raiz / PASTA_DOS_INSTRUMENTOS / "mod" / "leitor.py"
        leitor.parent.mkdir(parents=True)
        (raiz / "nucleo").mkdir()
        (raiz / PASTA_DOS_MODULOS).mkdir()

        def declarar(chaves_do_arquivo: dict, excecoes: list = None):
            if excecoes is not None:
                chaves_do_arquivo[CHAVE_DAS_EXCECOES_SEM_LEITOR] = excecoes
            (raiz / ARQUIVO_DE_CONFIGURACAO).write_text(
                json.dumps(chaves_do_arquivo), encoding="utf-8")

        declarar({"lida": 1})
        leitor.write_text(f'dado["lida"]\n'
                          f'dado["{CHAVE_DAS_EXCECOES_SEM_LEITOR}"]\n',
                          encoding="utf-8")
        (raiz / INSTALADOR).write_text(INSTALADOR_DE_MENTIRA,
                                       encoding="utf-8")
        corre('git init -q && git add -A', cwd=raiz)
        caso("chave citada por .py rastreado não vira saldo",
             chaves(raiz) == 0)

        caso("exceção declarada não é confundida com órfã na linha de "
             "detalhe: quem lê a saída vê o motivo, não o alarme",
             EXCECAO_DECLARADA.format("por isto") != SALDO_SEM_LEITOR
             and "declarado" in EXCECAO_DECLARADA.format("x"))

        caso("a chave nomeia o arquivo:linha de quem a lê",
             onde_a_marca_aparece(marcas_da_chave("lida"),
                                  leitores_da_configuracao(raiz)[0][1])
             == f"{PASTA_DOS_INSTRUMENTOS}/mod/leitor.py:1")

        caso("chave de arquivo rastreado que roda é fato do repositório",
             de_quem_e_a_chave(ARQUIVO_DE_CONFIGURACAO, 1)
             == CHAVE_DO_REPOSITORIO)

        caso("chave de arquivo de exemplo é dado da máquina",
             de_quem_e_a_chave(f"nucleo/executor{SUFIXO_DO_EXEMPLO}", 1)
             == CHAVE_DA_MAQUINA)

        caso("valor que a máquina preenche é dado da máquina",
             de_quem_e_a_chave(ARQUIVO_DE_CONFIGURACAO, "${CONTA}")
             == CHAVE_DA_MAQUINA)

        fora_do_git = raiz / "nucleo" / "so-no-disco.json"
        fora_do_git.write_text('{"ninguem_le_nem_rastreia": 1}',
                               encoding="utf-8")
        caso("chave de arquivo não rastreado fica de fora do universo",
             chaves(raiz) == 0
             and not [a for a, _, _ in chaves_declaradas(raiz)[0]
                      if a.endswith("so-no-disco.json")])
        fora_do_git.unlink()

        declarar({"lida": 1, "ninguem_le": 2})
        caso("chave declarada e lida por ninguém reprova",
             chaves(raiz) == 1)

        declarar({"lida": 1, "ninguem_le": 2},
                 [{CAMPO_DO_ARQUIVO: ARQUIVO_DE_CONFIGURACAO,
                   CAMPO_DA_CHAVE: "ninguem_le",
                   CAMPO_DO_MOTIVO: "prosa para gente, não para instrumento"}])
        caso("chave sem leitor, com motivo declarado, cala a rotina",
             chaves(raiz) == 0)

        declarar({"lida": 1, "ninguem_le": 2},
                 [{CAMPO_DO_ARQUIVO: ARQUIVO_DE_CONFIGURACAO,
                   CAMPO_DA_CHAVE: "ninguem_le"}])
        caso("exceção sem motivo não vale, e a chave segue acusada",
             chaves(raiz) == 1)

        declarar({"so_o_modulo_le": 3})
        (raiz / INSTALADOR).write_text(
            INSTALADOR_DE_MENTIRA.replace(
                f"'{INSTRUMENTO_DE_MODULO_DE_MENTIRA}': ''",
                f"'{INSTRUMENTO_DE_MODULO_DE_MENTIRA}': "
                "'dado[\\'so_o_modulo_le\\']'"),
            encoding="utf-8")
        caso("chave lida só pelo que chega por módulo não vira saldo",
             chaves(raiz) == 0)

        declarar({"lida": 1})
        (raiz / PASTA_DOS_MODULOS).rmdir()
        (raiz / INSTALADOR).write_text(
            "MODULOS = {'m': {'.agents/mod/mod.py': ''}}\n", encoding="utf-8")
        caso("numa instalação, sem modulos/, as chaves se medem sem pedir "
             "nada ao montar.py antigo que sobrou na raiz",
             chaves(raiz) == 0)
        (raiz / PASTA_DOS_MODULOS).mkdir()

        declarar({"so_o_instalador_cita": 4})
        (raiz / INSTALADOR).write_text(
            f'{INSTALADOR_DE_MENTIRA}MOLDE = '
            '{"so_o_instalador_cita": 4}\n', encoding="utf-8")
        caso("o instalador não conta como leitor: a carga dele cita tudo",
             '"so_o_instalador_cita"' in
             (raiz / INSTALADOR).read_text(encoding="utf-8")
             and chaves(raiz) == 1)

        (raiz / ARQUIVO_DE_CONFIGURACAO).write_text("{", encoding="utf-8")
        caso("configuração que não se deixa ler vira NÃO MEDIDO, não zero",
             chaves(raiz) == 1)

        (raiz / ARQUIVO_DE_CONFIGURACAO).unlink()
        caso("universo vazio não vira verde: sem nenhum `.json` com chave, a "
             "rotina diz que NÃO MEDIU, porque a listagem que volta vazia "
             "por engano é idêntica ao repositório sem configuração",
             chaves(raiz) == 1)

    with tempfile.TemporaryDirectory(prefix="camada-declarados-") as pasta:
        raiz = Path(pasta)
        (raiz / "nucleo").mkdir()
        corre("git init -q", cwd=raiz)

        def declarar_fora_do_git(caminhos: list):
            (raiz / ARQUIVO_DE_CONFIGURACAO).write_text(json.dumps(
                {"referencias_que_ficam_fora_do_git":
                 [{"caminho": c, "motivo": "porque sim"} for c in caminhos]}),
                encoding="utf-8")

        declarar_fora_do_git(["local/", "anotacao.md"])
        (raiz / ".gitignore").write_text("local/\n", encoding="utf-8")
        caso("caminho declarado fora do git que o git NÃO ignora REPROVA — "
             "declaração pela metade faz a cobrança de destino pedir destino "
             "para o que ninguém vai commitar",
             declarados_fora_do_git(raiz) == 1)

        (raiz / ".gitignore").write_text("local/\nanotacao.md\n",
                                         encoding="utf-8")
        caso("com todos alinhados, passa",
             declarados_fora_do_git(raiz) == 0)

        caso("a barra final é significativa: padrão que só vale para pasta "
             "não casa quando se pergunta pelo nome sem ela, e tirá-la "
             "acusaria alinhado como solto",
             caminho_que_o_git_ignora(raiz, "local/")
             and not caminho_que_o_git_ignora(raiz, "local"))

        (raiz / ARQUIVO_DE_CONFIGURACAO).write_text("{}", encoding="utf-8")
        caso("repositório que não declara caminho nenhum fora do git passa — "
             "aqui vazio é vazio mesmo, e não listagem que falhou",
             declarados_fora_do_git(raiz) == 0)

    with tempfile.TemporaryDirectory(prefix="camada-markdown-") as pasta:
        raiz = Path(pasta)
        conhecimento = raiz / PASTA_DO_CONHECIMENTO
        conhecimento.mkdir()
        instrumento = raiz / PASTA_DOS_INSTRUMENTOS / "mod"
        instrumento.mkdir(parents=True)
        (instrumento / "leitor.py").write_text(
            'ALVO = "conhecimento/contrato.md"\n', encoding="utf-8")
        (conhecimento / "contrato.md").write_text("o que o instrumento lê\n",
                                                  encoding="utf-8")
        (conhecimento / "LEIAME.md").write_text(
            "o cartão da pasta aponta para [a página](pagina.md)\n",
            encoding="utf-8")
        (conhecimento / "pagina.md").write_text("a página de saber\n",
                                                encoding="utf-8")
        (conhecimento / "so-em-prosa.md").write_text(
            "ninguém aponta para mim, e eu cito `citada.md` sem link\n",
            encoding="utf-8")
        (conhecimento / "citada.md").write_text("citada em prosa\n",
                                                encoding="utf-8")
        (conhecimento / "orfao.md").write_text("ninguém me alcança\n",
                                               encoding="utf-8")
        roteiros = raiz / "execucoes"
        roteiros.mkdir()
        (roteiros / "entrega.json").write_text("{}\n", encoding="utf-8")
        (roteiros / "entrega.md").write_text("a descrição do roteiro\n",
                                             encoding="utf-8")
        do_modulo = raiz / PASTA_DOS_MODULOS / "voz" / PASTA_DO_CONHECIMENTO
        do_modulo.mkdir(parents=True)
        (do_modulo / "voz.md").write_text("chega por --modulo voz\n",
                                          encoding="utf-8")
        corre('git init -q && git add -A', cwd=raiz)
        pilhas = pilhas_do_markdown(raiz)
        do = {nome: [rel for rel, _ in pilhas[nome]] for nome in pilhas}
        prova = {rel: p for pilha in pilhas.values() for rel, p in pilha}

        caso("`.md` nomeado por `.py` rastreado é contrato que instrumento "
             "deveria ler, e a prova diz a via 2",
             prova["conhecimento/contrato.md"]
             == VIA_DO_CODIGO.format(
                 f"{PASTA_DOS_INSTRUMENTOS}/mod/leitor.py:1"))

        caso("`.md` com link markdown de entrada é página de saber, e a "
             "prova diz a via 1",
             prova["conhecimento/pagina.md"]
             == VIA_DO_LINK.format("conhecimento/LEIAME.md"))

        caso("`.md` citado por caminho relativo à pasta de quem cita sai da "
             "pilha sem quem o leia pela via 2",
             prova["conhecimento/citada.md"]
             == VIA_DA_PROSA.format("conhecimento/so-em-prosa.md:1"))

        caso("`.md` irmão de um `.json` de roteiro sai da pilha sem quem o "
             "leia pela via 3",
             prova["execucoes/entrega.md"]
             == VIA_DO_ROTEIRO.format("execucoes/entrega.json"))

        caso("`.md` dentro de pasta de módulo sai da pilha sem quem o leia "
             "pela via 4",
             prova[f"{PASTA_DOS_MODULOS}/voz/{PASTA_DO_CONHECIMENTO}/voz.md"]
             == VIA_DO_MODULO.format(f"{PASTA_DOS_MODULOS}/voz"))

        caso("cartão de pasta não cai na pilha sem quem o leia",
             do[PILHA_NAO_CLASSIFICADO] == ["conhecimento/LEIAME.md"])

        caso("`.md` que nada referencia cai na pilha sem quem o leia",
             do[PILHA_SEM_LEITOR] == ["conhecimento/orfao.md",
                                      "conhecimento/so-em-prosa.md"])

        caso("a soma das pilhas é o universo `.md` rastreado",
             sum(len(p) for p in pilhas.values()) == 8 and markdown(raiz) == 0)

        (conhecimento / "orfao.md").unlink()
        corre('git add -A', cwd=raiz)
        caso("apagado o `.md` sem quem o leia, a pilha encolhe",
             len(pilhas_do_markdown(raiz)[PILHA_SEM_LEITOR]) == 1)

        caso("comando de barra em .claude/commands/ não cai na pilha sem "
             "quem o leia: quem o lê é o cliente, quando alguém digita o "
             "comando; o `.md` solto em outra pasta segue sem leitor",
             a_camada.pilha_do_markdown(".claude/commands/partida.md", ())[0]
             == PILHA_NAO_CLASSIFICADO
             and a_camada.pilha_do_markdown("conhecimento/solta.md", ())[0]
             == PILHA_SEM_LEITOR)

    with tempfile.TemporaryDirectory(prefix="camada-git-com-aviso-") as pasta:
        falante = Path(pasta) / "falante.py"
        falante.write_text(
            "import sys\n"
            "print('a.txt')\n"
            "print(\"warning: in the working copy of 'a.txt', LF will be "
            "replaced by CRLF\", file=sys.stderr)\n", encoding="utf-8")
        caso("o aviso que o git escreve no stderr não vira caminho: com um "
             "arquivo LF numa cópia CRLF, a bancada contava 4 tocados onde "
             "havia 3",
             a_camada.linhas_do_git(
                 Path(pasta), f'"{sys.executable}" "{falante}"') == ["a.txt"])

    with tempfile.TemporaryDirectory(prefix="camada-markdown-cego-") as pasta:
        raiz = Path(pasta)
        caso("git que não responde vira markdown NÃO MEDIDO, não zero",
             pilhas_do_markdown(raiz) is None and markdown(raiz) == 1)

    with tempfile.TemporaryDirectory(prefix="camada-sem-git-") as pasta:
        raiz = Path(pasta)
        (raiz / INSTALADOR).write_text(INSTALADOR_DE_MENTIRA,
                                       encoding="utf-8")
        (raiz / "nucleo").mkdir()
        (raiz / ARQUIVO_DE_CONFIGURACAO).write_text('{"lida": 1}',
                                                    encoding="utf-8")
        caso("git que não responde vira NÃO MEDIDO, não zero",
             rastreados_por_git(raiz, COMANDO_DOS_GANCHOS_RASTREADOS) is None
             and matricula(raiz) == 1
             and chaves(raiz) == 1)

    with tempfile.TemporaryDirectory(prefix="camada-bancada-") as sozinho:
        repositorio = Path(sozinho) / "repositorio"
        repositorio.mkdir()
        pecas = arvore_com_instrumentos_de_mentira(repositorio)
        verde = ".agents/pecas/verde.py"
        vermelho = ".agents/pecas/vermelho.py"

        def rodar_a_bancada_da_sessao(orcamento=ORCAMENTO_DAS_BANCADAS_TOCADAS,
                                      teto=TEMPO_DE_UMA_BANCADA_TOCADA,
                                      tetos=None):
            dito = io.StringIO()
            with contextlib.redirect_stdout(dito):
                veredito = bancada_dos_tocados(repositorio, orcamento, teto,
                                               tetos)
            return veredito, dito.getvalue()

        def limpar_a_arvore():
            corre("git checkout -q -- .", cwd=repositorio)

        veredito, dito = rodar_a_bancada_da_sessao()
        caso("sem instrumento tocado a rotina passa E diz isso em uma linha "
             "— rotina que cala no caso comum ensina a ignorar rotina",
             veredito == SAIDA_LIMPA
             and "Nenhum instrumento tocado" in dito)

        _, branch_medida = corre("git branch --show-current", cwd=repositorio)
        caso("a rotina diz QUE raiz e QUE branch mediu — rodada da raiz com "
             "o trabalho noutra árvore, o zero dela é verdade sobre o lugar "
             "errado, e sem o lugar dito ninguém percebe",
             repositorio.as_posix() in dito
             and branch_medida.strip() and branch_medida.strip() in dito)

        ao_lado = Path(sozinho) / "arvore-ao-lado"
        corre(f'git worktree add -q -b frente-ao-lado "{ao_lado.as_posix()}"',
              cwd=repositorio)
        veredito, dito = rodar_a_bancada_da_sessao()
        caso("sem nada tocado E com outra árvore de trabalho viva, a rotina "
             "nomeia a outra árvore: é lá que o trabalho pode estar",
             veredito == SAIDA_LIMPA and "arvore-ao-lado" in dito)
        corre(f'git worktree remove --force "{ao_lado.as_posix()}"',
              cwd=repositorio)
        veredito, dito = rodar_a_bancada_da_sessao()
        caso("sem outra árvore de trabalho, a rotina não inventa aviso",
             "arvore-ao-lado" not in dito and "outra árvore" not in dito)

        leitor_de_verdade = a_camada.linhas_do_git

        def cego_para(comando_cego):
            def leitor(raiz_lida, comando):
                if comando == comando_cego:
                    return None
                return leitor_de_verdade(raiz_lida, comando)
            return leitor

        a_camada.linhas_do_git = cego_para(
            a_camada.COMANDO_DAS_ARVORES_DE_TRABALHO)
        try:
            veredito, dito = rodar_a_bancada_da_sessao()
        finally:
            a_camada.linhas_do_git = leitor_de_verdade
        caso("git que não lista as árvores de trabalho é rotina NÃO MEDIDA: "
             "dizer que não mediu e sair zero é verde de quem não olhou",
             veredito == SAIDA_NAO_MEDIDO and "NÃO FORAM MEDIDAS" in dito)

        caso("git que não responde pela branch não é HEAD destacado: são "
             "dois estados, e cada um ganha o nome dele",
             a_camada.nome_da_branch_medida(None)
             != a_camada.nome_da_branch_medida([])
             and "destacado" in a_camada.nome_da_branch_medida([])
             and a_camada.nome_da_branch_medida(["frente"]) == "frente")

        porcelana = ["worktree " + repositorio.as_posix(), "HEAD abc",
                     "branch refs/heads/x",
                     "worktree " + (Path(sozinho) / "viva").as_posix(),
                     "HEAD def", "branch refs/heads/y",
                     "worktree " + (Path(sozinho) / "sumiu").as_posix(),
                     "HEAD 123", "detached",
                     "prunable gitdir file points to non-existent location"]
        vivas = a_camada.arvores_vivas_da_listagem(porcelana, repositorio)
        caso("árvore de trabalho PODÁVEL não é lugar onde o trabalho possa "
             "estar: a pasta dela sumiu, e mandar rodar de lá é mandar ao "
             "vazio",
             len(vivas) == 1 and vivas[0].endswith("viva"))

        a_camada.linhas_do_git = cego_para(a_camada.COMANDO_DA_BRANCH_ATUAL)
        try:
            veredito, dito = rodar_a_bancada_da_sessao()
        finally:
            a_camada.linhas_do_git = leitor_de_verdade
        caso("git que não responde pela branch é rotina NÃO MEDIDA de ponta "
             "a ponta: dizer que o git não disse e sair zero é o mesmo verde "
             "de quem não olhou",
             veredito == SAIDA_NAO_MEDIDO)

        corre("git checkout -q --detach", cwd=repositorio)
        veredito, dito = rodar_a_bancada_da_sessao()
        corre("git checkout -q -", cwd=repositorio)
        caso("HEAD destacado é dito pela ROTINA, não só pelo ajudante, e "
             "não reprova: é estado legítimo, medido",
             "destacado" in dito and veredito == SAIDA_LIMPA)

        sumida = Path(sozinho) / "arvore-que-sumiu"
        corre(f'git worktree add -q -b frente-que-sumiu "{sumida.as_posix()}"',
              cwd=repositorio)
        shutil.rmtree(sumida)
        veredito, dito = rodar_a_bancada_da_sessao()
        corre("git worktree prune", cwd=repositorio)
        caso("árvore de trabalho cuja pasta sumiu não é anunciada pela "
             "ROTINA como lugar onde o trabalho pode estar",
             "arvore-que-sumiu" not in dito)

        caso("falha ao listar o que nasceu, antes OU depois das bancadas, é "
             "sujeira NÃO MEDIDA, nunca árvore limpa",
             a_camada.o_que_a_bancada_sujou(None, ["a"]) is None
             and a_camada.o_que_a_bancada_sujou(["a"], None) is None
             and a_camada.o_que_a_bancada_sujou(["a"], ["a", "b"]) == ["b"])

        (pecas / "testes.py").write_text(INSTRUMENTO_QUE_PASSA + "\n",
                                         encoding="utf-8")
        (pecas / "delega.py").write_text(
            "from testes import testar\n" + INSTRUMENTO_QUE_PASSA + "\n",
            encoding="utf-8")
        (pecas / "propria.py").write_text(INSTRUMENTO_QUE_PASSA + "\n",
                                          encoding="utf-8")
        corre("git add -A", cwd=repositorio)
        veredito, dito = rodar_a_bancada_da_sessao()
        caso("instrumento que DELEGA a bancada ao testes.py da pasta não roda "
             "duas vezes a mesma prova — antes, o par gastava o orçamento "
             "inteiro e as bancadas baratas ficavam de fora",
             ".agents/pecas/delega.py" not in dito
             and ".agents/pecas/testes.py" in dito)
        caso("e o instrumento com bancada PRÓPRIA na mesma pasta continua "
             "rodando: a dedução é por delegação, não por pasta",
             ".agents/pecas/propria.py" in dito)
        for nome in ("testes.py", "delega.py", "propria.py"):
            (pecas / nome).unlink()
        corre("git add -A", cwd=repositorio)
        limpar_a_arvore()

        (pecas / "verde.py").write_text(INSTRUMENTO_QUE_PASSA + "\n",
                                        encoding="utf-8")
        veredito, dito = rodar_a_bancada_da_sessao()
        caso("instrumento sujo na árvore é tocado: a bancada dele roda e a "
             "rotina passa",
             veredito == SAIDA_LIMPA and verde in dito
             and "Bancada em dia" in dito)

        limpar_a_arvore()
        (pecas / "vermelho.py").write_text(INSTRUMENTO_QUE_CAI + "\n",
                                           encoding="utf-8")
        veredito, dito = rodar_a_bancada_da_sessao()
        caso("bancada vermelha reprova a rotina E nomeia o instrumento que "
             "caiu — placar sem nome não se investiga",
             veredito == SAIDA_COM_ACHADO and "Bancada VERMELHA" in dito
             and vermelho in dito)

        limpar_a_arvore()
        (pecas / "mudo.py").write_text(INSTRUMENTO_SEM_BANCADA + "\n",
                                       encoding="utf-8")
        veredito, dito = rodar_a_bancada_da_sessao()
        caso("instrumento tocado sem bancada não é falha, e sim uma linha "
             "dizendo que ali não há o que rodar",
             veredito == SAIDA_LIMPA
             and ".agents/pecas/mudo.py" in dito
             and "sem --testar próprio" in dito)

        limpar_a_arvore()
        (pecas / "verde.py").write_text(INSTRUMENTO_QUE_PASSA + "\n",
                                        encoding="utf-8")
        (pecas / "vermelho.py").write_text(INSTRUMENTO_QUE_CAI + "\n",
                                           encoding="utf-8")
        veredito, dito = rodar_a_bancada_da_sessao(
            ORCAMENTO_QUE_SO_DA_PARA_UMA)
        caso("estourado o orçamento, a rotina CORTA e ANUNCIA quem ficou de "
             "fora, com o comando que prova o resto — corte calado é o "
             "falso verde que esta rotina existe para não repetir",
             veredito == SAIDA_NAO_MEDIDO and "Fora do orçamento" in dito
             and vermelho in dito and "saude.py testes" in dito)

        limpar_a_arvore()
        lenta = pecas / "lenta.py"
        lenta.write_text(INSTRUMENTO_QUE_DEMORA, encoding="utf-8")
        partida = time.monotonic()
        veredito, dito = rodar_a_bancada_da_sessao(
            teto=TETO_QUE_NENHUMA_BANCADA_LENTA_ALCANCA)
        caso("bancada que não cabe no teto de tempo NÃO vira reprovação "
             "falsa: sai como orçamento, com o nome, e a rotina fica NÃO "
             "MEDIDA em vez de verde",
             veredito == SAIDA_NAO_MEDIDO and "não coube no teto" in dito
             and ".agents/pecas/lenta.py" in dito
             and "VERMELHA" not in dito
             and time.monotonic() - partida < 20)
        lenta.unlink()

        limpar_a_arvore()
        propria = pecas / "com-teto-proprio.py"
        propria.write_text(INSTRUMENTO_UM_POUCO_LERDO, encoding="utf-8")
        caminho_da_propria = ".agents/pecas/com-teto-proprio.py"
        veredito, dito = rodar_a_bancada_da_sessao(
            teto=TETO_QUE_NENHUMA_BANCADA_LENTA_ALCANCA)
        caso("sem teto próprio declarado, a bancada mais lenta que o teto "
             "geral deixa a rotina NÃO MEDIDA — foi o que aconteceu com o "
             "medidor da camada, que leva 66 s contra um teto de 60 s",
             veredito == SAIDA_NAO_MEDIDO and "não coube no teto" in dito)
        veredito, dito = rodar_a_bancada_da_sessao(
            teto=TETO_QUE_NENHUMA_BANCADA_LENTA_ALCANCA,
            tetos={caminho_da_propria: 30})
        caso("com teto próprio declarado, ela RODA e a rotina volta a medir",
             veredito == SAIDA_LIMPA and "não coube no teto" not in dito
             and caminho_da_propria in dito)
        caso("o orçamento cresce com o teto próprio, senão o corte por "
             "orçamento faria o mesmo estrago que o teto",
             orcamento_das_bancadas([caminho_da_propria], 120, 60,
                                    {caminho_da_propria: 180}) == 240
             and orcamento_das_bancadas([caminho_da_propria], 120, 60, {})
             == 120)
        caso("teto próprio menor que o geral não encurta ninguém",
             teto_desta_bancada(caminho_da_propria, 60,
                                {caminho_da_propria: 10}) == 60)
        caso("o teto próprio se declara por PASTA, senão vale só quando o "
             "testes.py da pasta é o tocado: tocar só o instrumento que "
             "delega recebia o teto geral e voltava a não caber",
             teto_desta_bancada(".agents/pecas/com-teto-proprio.py", 60,
                                {".agents/pecas": 180}) == 180
             and teto_desta_bancada(".agents/pecas/testes.py", 60,
                                    {".agents/pecas": 180}) == 180)
        propria.unlink()

        novo = pecas / "recem-nascido.py"
        novo.write_text(INSTRUMENTO_QUE_PASSA, encoding="utf-8")
        veredito, dito = rodar_a_bancada_da_sessao()
        caso("instrumento recém-nascido, que o git ainda não rastreia, "
             "também é tocado",
             veredito == SAIDA_LIMPA
             and ".agents/pecas/recem-nascido.py" in dito)
        novo.unlink()

        (pecas / "verde.py").write_text(INSTRUMENTO_QUE_PASSA + "\n",
                                        encoding="utf-8")
        corre(f'git add -A && git {ASSINATURA_DE_MENTIRA} commit -qm dois',
              cwd=repositorio)
        veredito, dito = rodar_a_bancada_da_sessao()
        caso("instrumento commitado nesta branch e ainda fora da integração "
             "conta como tocado — árvore limpa não é sessão sem trabalho",
             veredito == SAIDA_LIMPA and verde in dito
             and "Bancada em dia" in dito)

        caso("toda peça de instrumento entra na varredura, tenha bancada ou "
             "não — é ela que separa o mudo do que nem instrumento é",
             {p.name for p in pecas_de_instrumento(repositorio)}
             == {"verde.py", "vermelho.py", "mudo.py"})

        fonte_do_modulo = (repositorio / PASTA_DOS_MODULOS / "mod"
                           / PASTA_DOS_INSTRUMENTOS / "mod")
        fonte_do_modulo.mkdir(parents=True)
        (fonte_do_modulo / "mod.py").write_text(INSTRUMENTO_QUE_CAI,
                                                encoding="utf-8")
        veredito, dito = rodar_a_bancada_da_sessao()
        caso("instrumento tocado na FONTE de um módulo, em "
             "modulos/<módulo>/.agents/, roda a bancada dele como qualquer "
             "outro — fora da conta, ele não entrava nem com bancada nem sem",
             veredito == SAIDA_COM_ACHADO
             and "modulos/mod/.agents/mod/mod.py" in dito)
        shutil.rmtree(repositorio / PASTA_DOS_MODULOS)

    with tempfile.TemporaryDirectory(prefix="camada-bancada-cega-") as pasta:
        raiz = Path(pasta)
        corre(f'git init -q -b trabalho && git {ASSINATURA_DE_MENTIRA} '
              f'commit -q --allow-empty -m um', cwd=raiz)
        tocados, porque = caminhos_que_a_sessao_tocou(raiz)
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            veredito = bancada_dos_tocados(raiz)
        caso("sem upstream e sem branch de incorporação declarada, a metade "
             "commitada fica cega: NÃO MEDIDO, nunca zero",
             tocados is None and "upstream" in porque
             and veredito == SAIDA_NAO_MEDIDO
             and "NÃO MEDIDA" in dito.getvalue())

    with tempfile.TemporaryDirectory(prefix="camada-bancada-sem-git-") as pasta:
        raiz = Path(pasta)
        tocados, porque = caminhos_que_a_sessao_tocou(raiz)
        with contextlib.redirect_stdout(io.StringIO()):
            veredito = bancada_dos_tocados(raiz)
        caso("git que não responde vira bancada NÃO MEDIDA, não bancada "
             "vazia — lista vazia se leria como sessão que não tocou nada",
             tocados is None and "o git não disse" in porque
             and veredito == SAIDA_NAO_MEDIDO)

    caso("resumo de teste conta os casos qualquer que seja o prefixo — "
         "exigir 'OK' fazia tres instrumentos SADIOS serem acusados de "
         "caidos, e acusacao falsa e pior que nao acusar",
         casos_da_suite("OK: 45 casos") == 45
         and casos_da_suite("placar: 10 de 10 casos") == 10)
    caso("saida que nao fala de caso nenhum nao vira contagem — senao "
         "'Pronto. 3 arquivos escritos' passaria por tres casos provados",
         casos_da_suite("Pronto. 3 arquivos escritos") == 0)
    caso("saida vazia nao conta nada",
         casos_da_suite("") == 0 and casos_da_suite("   ") == 0)

    with tempfile.TemporaryDirectory() as longe,             tempfile.TemporaryDirectory() as pedida:
        (Path(pedida) / PASTA_DO_CONHECIMENTO).mkdir()
        rodada = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("camada.py")),
             "--quadro", "--raiz", pedida],
            cwd=longe, capture_output=True, text=True, encoding="utf-8",
            errors="replace")
        caso("--raiz mede a pasta pedida com o processo parado em outro "
             "diretório — o briefing manda rodar a abertura com a raiz por "
             "extenso, e a cerca recusa cd seguido de caminho relativo",
             rodada.returncode in (0, 1)
             and "Rode na raiz" not in rodada.stdout + rodada.stderr)

    with tempfile.TemporaryDirectory(prefix="camada-simular-") as pasta:
        raiz = Path(pasta)
        corre("git init -q", cwd=raiz)
        (raiz / "AGENTS.md").write_text("camada\n", encoding="utf-8")
        (raiz / "nucleo").mkdir()
        (raiz / "nucleo" / "regras.json").write_text(
            json.dumps({"regras": []}), encoding="utf-8")
        (raiz / ".gitignore").write_text("/nucleo/executor.json\n/tmp/*\n",
                                         encoding="utf-8")
        (raiz / "nucleo" / "executor.json").write_text("{}", encoding="utf-8")
        evidencia = raiz / "tmp" / "evidencias" / "etapa.json"
        evidencia.parent.mkdir(parents=True)
        evidencia.write_text("{}", encoding="utf-8")
        vistas = []

        def sessao_que_apaga_o_rascunho(argumentos, tempo=None, cwd=None):
            onde = Path(cwd)
            vistas.append((onde, (onde / "AGENTS.md").is_file(),
                           (onde / "nucleo" / "executor.json").is_file()))
            shutil.rmtree(onde / "tmp", ignore_errors=True)
            return 0, json.dumps({"type": "result", "result": "{}"})

        rodar_de_verdade = a_camada.corre_a_lista
        achar_de_verdade = a_camada.shutil.which
        a_camada.corre_a_lista = sessao_que_apaga_o_rascunho
        a_camada.shutil.which = lambda nome: nome
        try:
            a_camada.simular(raiz)
        finally:
            a_camada.corre_a_lista = rodar_de_verdade
            a_camada.shutil.which = achar_de_verdade
        caso("a sessão simulada roda numa cópia: a sessão que apaga tmp/ "
             "não leva a evidência de quem a chamou",
             evidencia.is_file())
        caso("a cópia leva a camada, e a sessão lê o AGENTS.md dela",
             len(vistas) == 1 and vistas[0][1]
             and vistas[0][0].resolve() != raiz.resolve())
        caso("a cópia sai do disco quando a simulação termina",
             len(vistas) == 1 and not vistas[0][0].exists())
        caso("a cópia leva a configuração local que o git ignora, como a "
             "sessão a teria na raiz",
             len(vistas) == 1 and vistas[0][2])

        estouradas = []

        def sessao_que_estoura_o_tempo(argumentos, tempo=None, cwd=None):
            estouradas.append(Path(cwd))
            raise subprocess.TimeoutExpired(argumentos, tempo or 1)

        a_camada.corre_a_lista = sessao_que_estoura_o_tempo
        a_camada.shutil.which = lambda nome: nome
        try:
            with contextlib.suppress(subprocess.TimeoutExpired):
                a_camada.simular(raiz)
        finally:
            a_camada.corre_a_lista = rodar_de_verdade
            a_camada.shutil.which = achar_de_verdade
        caso("a cópia sai do disco mesmo quando a sessão estoura o tempo",
             len(estouradas) == 1 and not estouradas[0].exists())

    total = len(casos)
    if falhas:
        print(f"FALHOU: {len(falhas)} de {total} casos")
        for falha in falhas:
            print(f"  [{falha}]")
        return 1
    print(f"OK: {total} casos — medida, prova e gabarito da simulação")
    return 0


if __name__ == "__main__":
    for canal in (sys.stdin, sys.stdout, sys.stderr):
        if not getattr(canal, "closed", True) and hasattr(canal, "reconfigure"):
            canal.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(testar())
