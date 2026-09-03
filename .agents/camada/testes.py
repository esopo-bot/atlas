import contextlib
import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from camada import (
    regras_da_pasta, PASTA_DE_REGRAS,
    medidas_da_versao, custo_por_entrega,
    MEDIDA_VERSAO, MEDIDA_LARGADA, MEDIDA_CUSTO, MEDIDA_ROTA,
    MEDIDA_CUSTO_SEM_EXECUCAO, MEDIDA_CUSTO_MEDIDO,
    MARCA_DE_BANCADA_AUSENTE,
    FORA_DA_PROVA,
    ARQUIVO_DE_CONFIGURACAO,
    ARQUIVO_SETTINGS,
    BANDEIRA_DE_TESTE,
    CAMPO_DA_CHAVE,
    CAMPO_DO_ARQUIVO,
    CAMPO_DO_MOTIVO,
    CANDIDATOS_DE_INTERPRETADOR,
    CHAVE_DAS_EXCECOES_SEM_LEITOR,
    CHAVE_DA_MAQUINA,
    CHAVE_DOS_GANCHOS,
    CHAVE_DO_COMANDO,
    CHAVE_DO_REPOSITORIO,
    CHAVE_POR_INCORPORACAO,
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
    PASTAS_DE_INSTRUMENTO_NO_RASCUNHO,
    PASTA_DAS_EVIDENCIAS,
    PASTA_DAS_SKILLS_FONTE,
    PASTA_DOS_GANCHOS,
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
    branch_de_incorporacao,
    branches_de_longa_duracao,
    branches_ja_entregues,
    casos_da_suite,
    catalogo_e_corpo,
    chaves,
    chaves_declaradas,
    colher_json,
    conta,
    corre,
    custo_das_execucoes,
    custo_por_etapa,
    de_quem_e_a_chave,
    entrega,
    esquecidos_no_rascunho,
    folga_do_termo,
    ganchos_ligados_fora_do_git,
    interpretador_com_nome_portatil,
    interpretadores_que_somem,
    julgar_a_simulacao,
    largada,
    leitores_da_configuracao,
    lotes_de_caminhos,
    marcas_da_chave,
    markdown,
    matricula,
    matricula_do_instalador,
    medir,
    nome_curto_da_branch,
    o_que_saiu_e_ficou,
    onde_a_marca_aparece,
    perguntas,
    pilhas_do_markdown,
    provar,
    quantas_linhas_casam,
    quantas_regras,
    rascunho,
    rastreados_por_git,
    referencia_que_existe,
    saldo_do_vocabulario,
    saldos_da_matricula,
    saldos_dos_instrumentos,
    soma_das_contagens,
    subagentes,
    teste_toca_o_proprio_codigo,
    teto_da_largada,
    um_numero,
    vocabulario,
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


def testar() -> int:
    falhas, casos = [], []

    def caso(rotulo, passou):
        casos.append(rotulo)
        if not passou:
            falhas.append(rotulo)

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        (raiz / "AGENTS.md").write_text("abc\n", encoding="utf-8")
        (raiz / PASTA_DO_CONHECIMENTO).mkdir()
        (raiz / PASTA_DOS_GANCHOS).mkdir(parents=True)
        skill = raiz / PASTA_DAS_SKILLS_FONTE / "s"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: s\ndescription: faz algo\n---\n\ncorpo longo aqui\n",
            encoding="utf-8")

        (raiz / INSTALADOR).write_text('VERSAO = "1.2"\n', encoding="utf-8")
        medidas_medidas = dict(medidas_da_versao(raiz))
        caso("as medidas da versão leem a versão do instalador, mede a largada e confessa "
             "o que não mediu — custo sem execução e rota sem rodada",
             medidas_medidas[MEDIDA_VERSAO] == "1.2"
             and medidas_medidas[MEDIDA_LARGADA].endswith("sem teto declarado")
             and medidas_medidas[MEDIDA_CUSTO] == MEDIDA_CUSTO_SEM_EXECUCAO
             and medidas_medidas[MEDIDA_ROTA].startswith("não medido"))
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
        (raiz / ".claude" / "settings.json").write_text(
            json.dumps({"hooks": {"SessionStart": [{"hooks": [
                {"type": "command",
                 "command": "binario-que-nao-existe-nenhum"}]}]}}),
            encoding="utf-8")
        caso("gancho que NÃO RODOU é contado como não medido",
             medir(raiz)[1]["ganchos_nao_medidos"] == 1)
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
        alias = falso / "python3"
        alias.write_text("#!/bin/sh\nexit 9\n", encoding="utf-8")
        alias.chmod(0o755)
        antes_do_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{falso}:{antes_do_path}"
        interpretador_com_nome_portatil.cache_clear()
        escolhido = interpretador_com_nome_portatil()
        os.environ["PATH"] = antes_do_path
        interpretador_com_nome_portatil.cache_clear()
        caso("python3 que existe e NAO roda é descartado — é o atalho "
             "da loja do Windows, e foi assim que a camada caiu lá",
             escolhido != "python3")
        caso("e o escolhido no lugar dele roda mesmo",
             corre(f"{escolhido} -c \"{PERGUNTA_DA_VERSAO}\"")[1].strip()
             == VERSAO_QUE_SERVE)
        nome = interpretador_com_nome_portatil()
        caso("o interpretador portátil é um nome, não um caminho",
             nome in CANDIDATOS_DE_INTERPRETADOR)
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
        caso("sem vocabulario.json não há o que medir",
             saldo_do_vocabulario(raiz) == [])
        (raiz / "nucleo").mkdir(exist_ok=True)
        (raiz / "nucleo" / "vocabulario.json").write_text(json.dumps(
            {"termos": [
                {"id": "aberto", "excecoes": [],
                 "pronto": {"padrao": r"(?i)\bfoo\b"}},
                {"id": "perdoado",
                 "excecoes": [{"ocorrencias": 2,
                               "arquivos": ["texto.md"]}],
                 "pronto": {"padrao": r"(?i)\bbar\b"}},
                {"id": "sem-referente",
                 "excecoes": [{"caso": "número solto",
                               "ocorrencias": 2}],
                 "pronto": {"padrao": r"(?i)\bbar\b"}},
                {"id": "referente-errado",
                 "excecoes": [{"caso": "aponta para onde não está",
                               "ocorrencias": 2,
                               "arquivos": ["outro.md"]}],
                 "pronto": {"padrao": r"(?i)\bbar\b"}},
                {"id": "referente-que-nao-viaja",
                 "excecoes": [{"caso": "o arquivo não chega nesta árvore",
                               "ocorrencias": 2,
                               "arquivos": ["nunca-chega-aqui.md"]}],
                 "pronto": {"padrao": r"(?i)\bzzz\b"}}]}),
            encoding="utf-8")
        (raiz / "texto.md").write_text("foo\nbar\nBar\n",
                                       encoding="utf-8")
        (raiz / "outro.md").write_text("nada aqui\n", encoding="utf-8")
        corre(f'cd "{raiz}" && git init -q && git add -A')
        contas = dict((c[0], c[1:4]) for c in saldo_do_vocabulario(raiz))
        caso("termo sem exceção acusa o saldo cheio",
             contas["aberto"] == (1, 0, 1))
        caso("exceção declarada desconta, e o padrão pega maiúscula",
             contas["perdoado"] == (2, 2, 0))
        caso("exceção sem referente não desconta nada",
             contas["sem-referente"] == (2, 0, 2))
        caso("e a exceção sem referente é nomeada pelo caso",
             [c[4] for c in saldo_do_vocabulario(raiz)
              if c[0] == "sem-referente"] == [["número solto"]])
        (raiz / PASTA_DOS_GANCHOS).mkdir(parents=True, exist_ok=True)
        for nome in ("rastreado.py", "so-local.py"):
            (raiz / PASTA_DOS_GANCHOS / nome).write_text(
                BANDEIRA_DE_TESTE, encoding="utf-8")
        ligacao = {CHAVE_DOS_GANCHOS: {EVENTO_DE_ABERTURA: [{
            CHAVE_DOS_GANCHOS: [
                {CHAVE_DO_COMANDO:
                 f'python3 "{RAIZ_NO_COMANDO}/{PASTA_DOS_GANCHOS}/{nome}"'}
                for nome in ("rastreado.py", "so-local.py")]}]}}
        (raiz / ARQUIVO_SETTINGS).write_text(
            json.dumps(ligacao), encoding="utf-8")
        caso("gancho ligado e fora do git é nomeado, e não vira saldo",
             ganchos_ligados_fora_do_git(
                 raiz, [f"{PASTA_DOS_GANCHOS}/rastreado.py"])
             == [f"{PASTA_DOS_GANCHOS}/so-local.py"])
        caso("gancho ligado que o git rastreia não entra nessa lista",
             f"{PASTA_DOS_GANCHOS}/rastreado.py" not in
             ganchos_ligados_fora_do_git(
                 raiz, [f"{PASTA_DOS_GANCHOS}/rastreado.py"]))
        caso("interpretador que existe no PATH não vira acusação",
             interpretadores_que_somem(
                 [f'{sys.executable} "$X/.claude/hooks/a.py"']) == [])
        caso("interpretador que NÃO existe é acusado pelo nome — gancho que "
             "não roda não acusa, e o silêncio dele é indistinguível de verde",
             interpretadores_que_somem(
                 ['naoexisteesteinterpretador "$X/.claude/hooks/a.py"'])
             == ["naoexisteesteinterpretador"])
        caso("o mesmo interpretador ausente em dois ganchos aparece uma vez",
             interpretadores_que_somem(
                 ['naoexiste "$X/a.py"', 'naoexiste "$X/b.py"'])
             == ["naoexiste"])
        caso("exceção que aponta para arquivo sem a ocorrência desconta "
             "só o que o arquivo carrega",
             contas["referente-errado"] == (2, 0, 2))
        caso("exceção cujo referente não existe nesta árvore não vira "
             "acusação: o arquivo não chegou, e a ocorrência também não",
             [c[4] for c in saldo_do_vocabulario(raiz)
              if c[0] == "referente-que-nao-viaja"] == [[]])
        caso("e ela também não desconta nada, porque não há o que descontar",
             contas["referente-que-nao-viaja"] == (0, 0, 0))
        caso("a medida carrega o saldo aberto, e exceção sem referente "
             "engorda o saldo em vez de sumir",
             medir(raiz)[1]["vocabulario_aberto"] == 5)
        caso("a medida conta as exceções sem referente",
             medir(raiz)[1]["excecoes_sem_referente"] == 1)
        caso("o flag sai 1 quando algum termo reabriu",
             vocabulario(raiz) == 1)

        caso("o lote respeita o teto e não perde caminho",
             [c for lote in lotes_de_caminhos(["a" * 40] * 50)
              for c in lote] == ["a" * 40] * 50)
        caso("lista curta cabe num lote só",
             len(lotes_de_caminhos(["curto"])) == 1)
        caso("lote de um arquivo só conta certo — sem o -H o grep não "
             "prefixa o nome, e o lote inteiro virava zero",
             quantas_linhas_casam(r"(?i)\bfoo\b", ["texto.md"], raiz) == 1)
        caso("contagem por arquivo soma o lote inteiro",
             soma_das_contagens("a.md:2\nb.md:3\n") == 5)
        caso("linha que não vira contagem sai não medido, nunca "
             "subcontagem",
             soma_das_contagens("a.md:2\nsem contagem\n") is None)
        caso("grep que ERRA devolve não medido, nunca zero",
             quantas_linhas_casam("(", ["texto.md"], raiz) is None)
        caso("grep que não acha devolve zero de verdade",
             quantas_linhas_casam("(?i)zzzz", ["texto.md"], raiz) == 0)
        (raiz / "nucleo" / "vocabulario.json").write_text(json.dumps(
            {"termos": [{"id": "quebrado", "excecoes": [],
                         "pronto": {"padrao": "("}}]}), encoding="utf-8")
        caso("termo com padrão quebrado não vira fechado",
             saldo_do_vocabulario(raiz)[0][3] is None)
        caso("e o flag sai 1 em vez de dizer verde",
             vocabulario(raiz) == 1)
        caso("a medida conta o que não foi medido",
             medir(raiz)[1]["vocabulario_nao_medido"] == 1)
        caso("exceção que sobra é folga, e folga esconde termo reabrindo",
             folga_do_termo(10, 11) == 1)
        caso("exceção que bate com o disco não é folga",
             folga_do_termo(10, 10) == 0)
        caso("exceção menor que o medido é saldo, não folga",
             folga_do_termo(11, 10) == 0)
        caso("termo não medido não vira folga inventada",
             folga_do_termo(None, 7) == 0)

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

    with tempfile.TemporaryDirectory(prefix="camada-entrega-") as sozinho:
        repositorio = Path(sozinho) / "repositorio"
        repositorio.mkdir()
        assinatura = ("-c user.name=t -c user.email=t@t "
                      "-c commit.gpgsign=false")
        corre(f'cd "{repositorio}" && git init -q && echo a > a.txt && git add -A && git {assinatura} commit -qm um')
        caso("sem remoto nenhum, a entrega não se prova",
             entrega(repositorio) == 1)
        remoto = Path(sozinho) / "remoto.git"
        corre(f'git init -q --bare "{remoto}"')
        corre(f'cd "{repositorio}" && git remote add origin "{remoto}" && git push -q origin HEAD:refs/heads/$(git branch --show-current)')
        caso("tudo empurrado, a entrega está limpa",
             entrega(repositorio) == 0)
        corre(f'cd "{repositorio}" && echo b > b.txt && git add -A && git {assinatura} commit -qm dois')
        caso("commit que não saiu da máquina reprova",
             entrega(repositorio) == 1)

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
        corre(f'cd "{repositorio}" && git init -q -b main && git add -A && git {assinatura} commit -qm um')
        remoto = Path(sozinho) / "remoto.git"
        corre(f'git init -q --bare "{remoto}"')
        corre(f'cd "{repositorio}" && git remote add origin "{remoto}" && git push -q origin main')
        protegidas = branches_de_longa_duracao(repositorio)
        caso("a lista de longa duração se lê, sem os comentários",
             protegidas == {"main", "homolog"})
        caso("a branch de incorporação sai da configuração, nunca de palpite",
             branch_de_incorporacao(repositorio) == "main")
        referencia = referencia_que_existe(repositorio, "main")
        caso("a referência preferida é a do remoto, que é a que entregou",
             referencia == "origin/main")

        corre(f'cd "{repositorio}" && git checkout -q -b entregue && echo b > b.txt && git add -A && git {assinatura} commit -qm dois')
        corre(f'cd "{repositorio}" && git push -q origin entregue')
        corre(f'cd "{repositorio}" && git checkout -q main && git {assinatura} merge -q --no-ff -m mescla entregue && git push -q origin main')
        corre(f'cd "{repositorio}" && git checkout -q -b viva && echo c > c.txt && git add -A && git {assinatura} commit -qm tres && git checkout -q main')
        locais, remotas, mediu = branches_ja_entregues(
            repositorio, referencia_que_existe(repositorio, "main"),
            "main", protegidas)
        caso("a listagem se declara medida quando o git respondeu", mediu)
        corre(f'cd "{repositorio}" && git remote set-head origin main')
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
        corre(f'cd "{repositorio}" && git branch -q -D entregue && git push -q origin --delete entregue')
        caso("podadas as duas pontas, a entrega fica limpa",
             o_que_saiu_e_ficou(repositorio, "main") == 0)

        corre(f'cd "{repositorio}" && git checkout -q -b garfo && echo d > d.txt && git add -A && git {assinatura} commit -qm quatro')
        corre(f'cd "{repositorio}" && git checkout -q main && git {assinatura} merge -q --no-ff -m mescla garfo')
        corre(f'cd "{repositorio}" && git checkout -q garfo && git {assinatura} merge -q --no-ff -m "no orfao" main && git checkout -q main && git push -q origin main')
        orfaos = branches_ja_entregues(
            repositorio, referencia_que_existe(repositorio, "main"),
            "main", protegidas)[0]
        caso("o no de mescla orfao, cujos pais ja estao na incorporacao, "
             "e acusado — nada dele falta la",
             "garfo" in orfaos)
        corre(f'cd "{repositorio}" && git checkout -q -b recem-criada && git checkout -q main')
        caso("branch recem-criada, identica ao topo da incorporacao, NAO e "
             "acusada — ali nao ha rastro, ha comeco",
             "recem-criada" not in branches_ja_entregues(
                 repositorio, referencia_que_existe(repositorio, "main"),
                 "main", protegidas)[0])
        corre(f'cd "{repositorio}" && git branch -q nova-do-passado main~1')
        acusadas_com_a_nova = branches_ja_entregues(
            repositorio, referencia_que_existe(repositorio, "main"),
            "main", protegidas)[0]
        caso("o limite declarado: branch nova cortada de um ponto anterior ao "
             "topo E acusada, porque o git nao diz em que branch um commit "
             "nasceu — e contar commits proprios nao separa, da zero nos dois",
             "nova-do-passado" in acusadas_com_a_nova
             and "entregue" not in acusadas_com_a_nova
             and corre(f'cd "{repositorio}" && '
                       'git rev-list --count main..nova-do-passado')[1].strip()
             == "0")
        corre(f'cd "{repositorio}" && git branch -q -D nova-do-passado')
        caso("a branch viva continua fora da acusacao depois de tudo",
             "viva" not in branches_ja_entregues(
                 repositorio, referencia_que_existe(repositorio, "main"),
                 "main", protegidas)[0])
        (repositorio / "nucleo" / "configuracao.json").write_text(
            json.dumps({}), encoding="utf-8")
        caso("sem incorporação declarada é NÃO MEDIDO, nunca zero calado",
             o_que_saiu_e_ficou(repositorio, "main") == 0
             and branch_de_incorporacao(repositorio) == "")

    with tempfile.TemporaryDirectory(prefix="camada-rascunho-") as pasta:
        raiz = Path(pasta)
        (raiz / RASCUNHO).mkdir()
        leiame = raiz / RASCUNHO / "LEIAME.md"
        leiame.write_text("a pasta se explica\n", encoding="utf-8")
        velho = time.time() - (TETO_DE_DIAS_NO_RASCUNHO + 1) * SEGUNDOS_DO_DIA
        os.utime(leiame, (velho, velho))
        corre(f'cd "{raiz}" && git init -q && git add -A')
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

        sem_pasta = raiz / "sem-rascunho"
        sem_pasta.mkdir()
        caso("sem a pasta no disco a rotina cala e não inventa acusação",
             rascunho(sem_pasta) == 0)

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
            (raiz / caminho).parent.mkdir(parents=True)
            (raiz / caminho).write_text("", encoding="utf-8")
        corre(f'cd "{raiz}" && git init -q && git add -A')
        caso("gancho rastreado, embutido e declarado não vira saldo",
             matricula(raiz) == 0)

        instrumento = raiz / INSTRUMENTO_DE_MODULO_DE_MENTIRA
        instrumento.parent.mkdir(parents=True)
        instrumento.write_text("", encoding="utf-8")
        corre(f'cd "{raiz}" && git add -A')
        caso("instrumento que chega por módulo não vira saldo",
             matricula(raiz) == 0)
        instrumento.rename(instrumento.with_name("fora.py"))
        corre(f'cd "{raiz}" && git add -A')
        caso("instrumento rastreado fora do FONTES é acusado de não viajar",
             matricula(raiz) == 1)
        corre(f'cd "{raiz}" && git rm -q --cached '
              f'"{PASTA_DOS_INSTRUMENTOS}/mod/fora.py"')
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
        corre(f'cd "{raiz}" && git add -A')
        caso("gancho rastreado fora do FONTES é acusado de não viajar",
             matricula(raiz) == 1)
        corre(f'cd "{raiz}" && git rm -q --cached '
              f'"{PASTA_DOS_GANCHOS}/novo.py"')
        caso("tirado do git, o mesmo arquivo cala a rotina",
             matricula(raiz) == 0)
        solto.unlink()

        gancho.unlink()
        corre(f'cd "{raiz}" && git rm -q --cached '
              f'"{PASTA_DOS_GANCHOS}/bom.py"')
        caso("matrícula sem arquivo no disco é acusada de órfã",
             saldos_da_matricula(raiz, [], fontes, declarados)
             == [(f"{PASTA_DOS_GANCHOS}/bom.py", SALDO_ORFA)])
        gancho.write_text("", encoding="utf-8")
        corre(f'cd "{raiz}" && git add -A')

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
        corre(f'cd "{raiz}" && git init -q && git add -A')
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
        caso("sem arquivo de configuração nenhum, não há chave a cobrar",
             chaves(raiz) == 0)

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
        corre(f'cd "{raiz}" && git init -q && git add -A')
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
        corre(f'cd "{raiz}" && git add -A')
        caso("apagado o `.md` sem quem o leia, a pilha encolhe",
             len(pilhas_do_markdown(raiz)[PILHA_SEM_LEITOR]) == 1)

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

    caso("resumo de teste conta os casos qualquer que seja o prefixo — "
         "exigir 'OK' fazia tres instrumentos SADIOS serem acusados de "
         "caidos, e acusacao falsa e pior que nao acusar",
         casos_da_suite("OK: 45 casos") == 45
         and casos_da_suite("higiene: 10 de 10 casos") == 10)
    caso("saida que nao fala de caso nenhum nao vira contagem — senao "
         "'Pronto. 3 arquivos escritos' passaria por tres casos provados",
         casos_da_suite("Pronto. 3 arquivos escritos") == 0)
    caso("saida vazia nao conta nada",
         casos_da_suite("") == 0 and casos_da_suite("   ") == 0)

    total = len(casos)
    if falhas:
        print(f"FALHOU: {len(falhas)} de {total} casos")
        for falha in falhas:
            print(f"  [{falha}]")
        return 1
    print(f"OK: {total} casos — medida, prova e gabarito da simulação")
    return 0


if __name__ == "__main__":
    sys.exit(testar())
