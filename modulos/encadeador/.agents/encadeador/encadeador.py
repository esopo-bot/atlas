#!/usr/bin/env python3
"""encadeador — roda a corrente de etapas do manifesto, um recibo por etapa.

Generaliza a receita do `rotinas/executar.sh` (preparar ambiente e rodar
`claude -p` com um prompt), peça a peça: a raiz virou `--cwd`; o venv e o
arquivo de ambiente viraram o bloco `ambiente` do manifesto (lidos por ESTE
processo, nunca pelo modelo — igual à receita); o prompt virou a etapa de
tipo `sessao`; e o log virou recibo materializado por código (degrau 1)
mais o log da conferência (degrau 2). O que a receita não tinha e aqui
existe: manifesto com dependências, fork/join, ensaio e teto de ciclos.

O manifesto (JSON):

    {
      "teto": 3,
      "ambiente": {"venv": ".venv", "env": ".credenciais/mcp.env"},
      "etapas": [
        {"nome": "prepara", "tipo": "codigo", "comando": "bash prepara.sh"},
        {"nome": "analisa", "tipo": "sessao", "prompt": "…",
         "depende": ["prepara"]},
        {"nome": "confere", "tipo": "conferencia", "depende": ["analisa"]},
        {"nome": "aprova", "tipo": "portao",
         "aprovacao": "aprovacoes/pr.ok", "depende": ["confere"]}
      ]
    }

As regras que este script impõe:

- **Fork só de etapas sem dependência declarada entre si** — quem está
  pronto junto roda junto; `conferencia` e `portao` NUNCA dividem onda com
  ninguém (conferir em paralelo com sessão é conferir código que ainda
  muda; portão é do dono e não disputa CPU com nada).
- **O ensaio lista a corrente inteira sem executar NADA**: nem comando,
  nem sessão, nem leitura do arquivo de ambiente.
- **Recibo só por código** (o contrato é `.agents/recibo/recibo.schema.json`):
  o stdout de cada etapa vai ao `materializar`; etapa que morre vira `para`
  sintético `morta`; stdout que não é recibo vira `para` `recibo-invalido`;
  etapa desligada vira skip. Veredito que não seja `segue` PARA a corrente.
- **Teto pela contagem**: com `teto` ou mais recibos `para` no diretório do
  trabalho, nada roda — nasce o `para` sintético `teto-esgotado`.
- **Um escritor só**: quem materializa recibo deste trabalho é este
  processo; a mesma etapa nunca roda duas vezes na mesma onda.

O que ele NÃO FAZ — e confessa (os refutadores mediram cada limite):
- não escreve recibo (chama `recibo.py`) nem confere (chama `conferir.py`);
- não isola etapas entre si: fork de etapas que escrevem no mesmo arquivo
  é corrida — o desenho manda worktree por etapa (a receita dos
  fabricantes), e o isolamento é de quem escreve o manifesto;
- não reescreve prompt de ciclo — o `proximo` de quem reprovou é a
  instrução; reexecutar é decisão de quem opera;
- não preserva a série de recibos se o MANIFESTO for reordenado no meio de
  um trabalho: a ordem NN vem da posição na lista — reordenar começa outra
  série; não reordene manifesto de trabalho já rodado;
- skip satisfaz dependência (o contrato do degrau 1: desligar o meio não
  impede a terceira) — dependente que precisava da entrega da desligada
  morre, e o log da etapa diz por quê; desligar etapa com entrega é
  tesoura de quem opera;
- etapa de sessão herda da receita o `--dangerously-skip-permissions`
  (sessão de rotina não tem quem responder prompt) — rode a corrente em
  worktree ou clone descartável, nunca na árvore que importa;
- no estouro de tempo mata o GRUPO do processo, mas comando que abre
  sessão própria (`setsid …`) escapa da matança e fica órfão — o recibo
  `morta` e a parada da corrente nascem mesmo assim (medido); órfão
  desses é de quem escreveu o comando;
- lê `ambiente.env` como SUBCONJUNTO do source do shell: aspas
  envolventes caem, comentário após espaço-# cai, e `$()` NÃO expande —
  de propósito, mais seguro que a receita;
- não imprime valor de ambiente; não empurra, não publica e não toca na
  automação da casa — portão e destrutivo são do dono.

Uso:
    encadeador.py ensaio    --manifesto M --trabalho T [--dir recibos] [--cwd .]
    encadeador.py executar  --manifesto M --trabalho T [--dir recibos] [--cwd .]
    encadeador.py andamento --trabalho T [--dir recibos] [--manifesto M]

Saída de ensaio/executar: 0 = corrente completa (tudo `segue`); 5 = parou
num `para`; 6 = parou num `pergunta` (aguardando o dono); 2 = erro de
uso/ambiente.

O `andamento` fotografa os recibos do trabalho e devolve JSON no stdout
(exit 0; 2 = erro de uso). O contrato:

    {"trabalho": T, "dir": <absoluto>, "estado":
       "completa | parada | aguardando-portao | em-curso",
     "etapas": [{"ordem": N, "nome": ..., "veredito": segue|para|pergunta,
                 "ciclo": {"i": N, "teto": N}, "faltas": [...],
                 "proximo": texto|null, "pergunta": texto|null}],
     "paras": <total de recibos para — o contador do teto>,
     "teto": <o teto visto nos recibos>|null,
     "avisos": [...], "proxima_acao": <texto>}

- Por etapa entra o recibo do CICLO MAIS ALTO; a ordem é a do manifesto
  (o NN do nome do arquivo).
- Estado: algum `para` no recibo corrente = `parada`; algum `pergunta` =
  `aguardando-portao`; tudo `segue` = `completa`; nenhum recibo =
  `em-curso` (nada rodou ainda).
- `proxima_acao`: o `proximo` de quem reprovou, a `pergunta` do portão, ou
  a leitura dos recibos — sempre uma frase acionável.
- `--manifesto` (opcional) troca inferência por prova: `completa` passa a
  exigir recibo `segue` de TODA etapa ligada do manifesto; etapa ligada sem
  recibo vira `em-curso`, com a lista do que falta na `proxima_acao`.
- Limites confessados: leitura no meio de uma execução fotografa a onda
  parcial (releia); SEM o manifesto, corrente morta sem deixar recibo não
  se distingue de completa — o exit de quem executou é a fonte; recibo
  ilegível vira aviso e conta como `para`, igual ao motor.

Rode os testes com:  python .agents/encadeador/encadeador.py --testar
"""

import argparse
import concurrent.futures
import contextlib
import io
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def _achar_camada() -> Path:
    """A pasta .agents que tem recibo/ e conferir/ — a camada do destino.

    Instalado, é a irmã direta (.agents/encadeador → .agents/recibo). No
    repositório de origem, o módulo mora em modulos/encadeador/.agents/…,
    então sobe até achar a raiz que tem .agents/recibo. Sem camada, o
    módulo não funciona — e diz isso, em vez de quebrar longe.
    """
    for base in (AQUI.parent, *AQUI.parents):
        if (base / "recibo" / "recibo.py").is_file():
            return base
        if (base / ".agents" / "recibo" / "recibo.py").is_file():
            return base / ".agents"
    print("erro de ambiente: não achei a camada (.agents/recibo/recibo.py) — "
          "o módulo encadeador exige a camada montada no repositório.",
          file=sys.stderr)
    sys.exit(2)


CAMADA = _achar_camada()
sys.path.insert(0, str(CAMADA / "recibo"))
import recibo as _recibo  # noqa: E402 — o contrato e o validador moram lá

RECIBO = CAMADA / "recibo" / "recibo.py"
CONFERIR = CAMADA / "conferir" / "conferir.py"

TIPOS = ("codigo", "sessao", "conferencia", "portao")
SOZINHAS = ("conferencia", "portao")
TEMPO_CODIGO = 600
TEMPO_SESSAO = 3600


# ---------------------------------------------------------------------------
# O manifesto: validação na fronteira e as ondas do fork/join.
# ---------------------------------------------------------------------------

def _inteiro_sao(valor, minimo=1) -> bool:
    # bool é subclasse de int — a lição do recibo.py vale aqui também.
    return isinstance(valor, int) and not isinstance(valor, bool) \
        and valor >= minimo


def validar_manifesto(manifesto, esquema: dict) -> list:
    """Todos os defeitos do manifesto; lista vazia = são.

    Tipo errado é recusa na fronteira, nunca traceback lá dentro: raiz que
    não é objeto, depende que não é lista de nomes e comando-lista (que o
    shell rodaria pela metade, em silêncio) foram todos medidos.
    """
    if not isinstance(manifesto, dict):
        return ["manifesto: a raiz precisa ser um objeto JSON"]
    erros = []
    # A régua do degrau 1 (additionalProperties false) vale aqui: um typo
    # ("dependee") apagava a dependência em silêncio e forkava etapas que
    # o manifesto quis serializar (medido).
    for sobra in sorted(set(manifesto) - {"teto", "ambiente", "etapas"}):
        erros.append(f"manifesto: campo desconhecido {sobra!r}")
    for sobra in sorted(set(manifesto.get("ambiente", {}) or {})
                        - {"venv", "env"}):
        erros.append(f"ambiente: campo desconhecido {sobra!r}")
    etapas = manifesto.get("etapas")
    if not isinstance(etapas, list) or not etapas:
        return ["manifesto sem lista de etapas"]
    if not _inteiro_sao(manifesto.get("teto", 3)):
        erros.append("teto precisa ser inteiro >= 1")

    nomes = []
    regra_nome = esquema["properties"]["etapa"]
    for n, etapa in enumerate(etapas, start=1):
        if not isinstance(etapa, dict):
            erros.append(f"etapa {n}: não é um objeto")
            continue
        nome = etapa.get("nome", "")
        erros += _recibo._erros(regra_nome, nome, f"etapa {n} (nome)")
        if nome in nomes:
            erros.append(f"etapa {n}: nome duplicado {nome!r}")
        nomes.append(nome)
        tipo = etapa.get("tipo", "")
        if tipo not in TIPOS:
            erros.append(f"etapa {nome!r}: tipo desconhecido {tipo!r} "
                         f"(vale: {', '.join(TIPOS)})")
        for campo, quando in (("comando", "codigo"), ("prompt", "sessao"),
                              ("aprovacao", "portao")):
            if tipo == quando and (not isinstance(etapa.get(campo), str)
                                   or not etapa.get(campo, "").strip()):
                erros.append(f"etapa {nome!r}: tipo {quando} exige o campo "
                             f"{campo} (texto)")
        for sobra in sorted(set(etapa) - {"nome", "tipo", "comando", "prompt",
                                          "aprovacao", "depende", "ligada",
                                          "tempo-limite", "max-turnos"}):
            erros.append(f"etapa {nome!r}: campo desconhecido {sobra!r}")
        if "ligada" in etapa and not isinstance(etapa["ligada"], bool):
            # "false" (texto) é verdadeiro em Python: a etapa que o operador
            # quis desligar rodava (medido).
            erros.append(f"etapa {nome!r}: ligada precisa ser true ou false "
                         "(booleano, sem aspas)")
        if "tempo-limite" in etapa and not _inteiro_sao(etapa["tempo-limite"]):
            erros.append(f"etapa {nome!r}: tempo-limite precisa ser "
                         "inteiro >= 1")
        if "max-turnos" in etapa and not _inteiro_sao(etapa["max-turnos"]):
            erros.append(f"etapa {nome!r}: max-turnos precisa ser inteiro >= 1")
        depende = etapa.get("depende", [])
        if not isinstance(depende, list) \
                or any(not isinstance(d, str) for d in depende):
            erros.append(f"etapa {nome!r}: depende precisa ser lista de nomes")
            continue
        for dependencia in depende:
            if dependencia not in [e.get("nome") for e in etapas
                                   if isinstance(e, dict)]:
                erros.append(f"etapa {nome!r}: depende de {dependencia!r}, "
                             "que não existe no manifesto")

    if not erros and _tem_ciclo(etapas):
        erros.append("o grafo de dependências tem ciclo — nada teria vez")
    return erros


def _tem_ciclo(etapas: list) -> bool:
    pendentes = {e["nome"]: set(e.get("depende", [])) for e in etapas}
    while pendentes:
        livres = [nome for nome, deps in pendentes.items() if not deps]
        if not livres:
            return True
        for nome in livres:
            del pendentes[nome]
        for deps in pendentes.values():
            deps.difference_update(livres)
    return False


def ondas_de(etapas: list) -> list:
    """As ondas do fork/join, na ordem do manifesto.

    Quem está pronto junto roda junto — MENOS conferência e portão, que
    ganham onda própria, sempre. A ordem do manifesto desempata: se a
    primeira etapa pronta é uma solitária, a onda é só dela.
    """
    feitas, ondas = set(), []
    pendentes = list(etapas)
    while pendentes:
        prontas = [e for e in pendentes
                   if set(e.get("depende", [])) <= feitas]
        if not prontas:
            sys.exit("defeito no encadeador: grafo validado travou")
        if prontas[0]["tipo"] in SOZINHAS:
            onda = [prontas[0]]
        else:
            onda = [e for e in prontas if e["tipo"] not in SOZINHAS]
        ondas.append(onda)
        for etapa in onda:
            feitas.add(etapa["nome"])
            pendentes.remove(etapa)
    return ondas


# ---------------------------------------------------------------------------
# O ambiente — a parte herdada do executar.sh, lida por este processo.
# ---------------------------------------------------------------------------

def montar_ambiente(manifesto: dict, cwd: str, base: dict) -> dict:
    """PATH do venv e variáveis do arquivo de ambiente, sem ecoar valor."""
    ambiente = dict(base)
    bloco = manifesto.get("ambiente", {})
    venv = bloco.get("venv")
    if venv:
        caminho = Path(cwd) / venv
        if (caminho / "bin").is_dir():
            ambiente["PATH"] = f"{caminho / 'bin'}:{ambiente.get('PATH', '')}"
            ambiente["VIRTUAL_ENV"] = str(caminho)
        else:
            print(f"AVISO: venv não encontrado em {caminho}; sigo sem ele.",
                  file=sys.stderr)
    arquivo = bloco.get("env")
    if arquivo:
        caminho = Path(cwd) / arquivo
        if caminho.is_file():
            for linha in caminho.read_text(encoding="utf-8").splitlines():
                linha = linha.strip()
                if not linha or linha.startswith("#") or "=" not in linha:
                    continue
                chave, valor = linha.removeprefix("export ").split("=", 1)
                valor = valor.strip()
                # A semântica do source, no subconjunto que a receita usa:
                # aspas envolventes caem, comentário após espaço-# cai —
                # sem isto a credencial chegava corrompida (medido). $()
                # NÃO expande, de propósito.
                if len(valor) >= 2 and valor[0] == valor[-1] \
                        and valor[0] in "\"'":
                    valor = valor[1:-1]
                else:
                    valor = re.split(r"\s+#", valor, maxsplit=1)[0].strip()
                ambiente[chave.strip()] = valor
        else:
            print(f"AVISO: arquivo de ambiente não encontrado em {caminho}; "
                  "sigo sem ele.", file=sys.stderr)
    # O systemd não herda o PATH do shell de login — o remendo da receita.
    # No FIM do PATH, de propósito: o remendo garante ACHAR o claude quando
    # falta, nunca sobrepor um claude legítimo do PATH nem o venv declarado
    # (prepend sobrepunha os dois — medido).
    local_bin = str(Path.home() / ".local" / "bin")
    if local_bin not in ambiente.get("PATH", "").split(":"):
        ambiente["PATH"] = f"{ambiente.get('PATH', '')}:{local_bin}"
    return ambiente


class TempoEstourado(Exception):
    def __init__(self, tempo):
        super().__init__(f"tempo-limite de {tempo}s estourado")
        self.tempo = tempo


def _rodar_processo(comando, *, shell, cwd, env, entrada, tempo):
    """Roda num grupo de processos próprio e, no estouro, mata o GRUPO.

    O subprocess.run com timeout mata só o filho direto: o `sh -c` morria
    e o `sleep 300` de dentro sobrevivia órfão (medido pelo refutador).
    """
    processo = subprocess.Popen(
        comando, shell=shell, cwd=cwd, env=env,
        stdin=subprocess.PIPE if entrada is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True)
    try:
        saida, erro = processo.communicate(entrada, timeout=tempo)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(processo.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        processo.wait()
        raise TempoEstourado(tempo) from None
    return processo.returncode, saida, erro


# ---------------------------------------------------------------------------
# Rodar uma etapa e materializar o recibo dela — sempre por código.
# ---------------------------------------------------------------------------

def _cli_recibo(argumentos, entrada=None):
    return subprocess.run([sys.executable, str(RECIBO)] + argumentos,
                          input=entrada, capture_output=True, text=True,
                          timeout=120)


def _guia_da_sessao() -> str:
    return _cli_recibo(["esquema-sessao"]).stdout.strip()


TETO_CONFIGURACAO = 64_000


def _bloco_de_regras(cwd) -> str:
    """As frases das regras da camada, entregues por código — ou nada.

    A fonte é `conhecimento/regras.json` (camada 0.87+): só as frases
    imperativas entram — o porquê mora nas páginas de procedência e não cabe
    em todo prompt de etapa. Entrega determinística de propósito: regra dura
    que depende de o modelo lembrar de buscar já custou caro no sistema
    estudado. Fonte ausente é silêncio (casa sem a camada nova); ilegível
    avisa e segue — nenhuma etapa derruba a corrente por causa de aviso.
    Cada frase vira linha única citada (`> `), pela mesma razão da moldura
    da configuração.
    """
    fonte = Path(cwd) / "conhecimento" / "regras.json"
    try:
        texto = fonte.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    try:
        regras = json.loads(texto)["regras"]
        frases = [" ".join(f"{regra['id']}. {regra['regra']}".split())
                  for regra in regras]
    except (json.JSONDecodeError, KeyError, TypeError):
        print(f"AVISO: {fonte} ilegível como fonte de regras; o prompt "
              "seguiu sem elas.", file=sys.stderr)
        return ""
    if not frases:
        return ""
    citado = "\n".join("> " + frase for frase in frases)
    if len(citado) > TETO_CONFIGURACAO:
        print(f"AVISO: {fonte} passou do teto ({TETO_CONFIGURACAO}); o "
              "prompt seguiu sem as regras.", file=sys.stderr)
        return ""
    return ("AS REGRAS DA CAMADA — as linhas citadas com '> ' logo abaixo "
            "valem em toda etapa; a lista completa, com o porquê, está em "
            "conhecimento/regras-da-camada.md:\n\n" + citado + "\n---\n\n")


def _bloco_de_configuracao(cwd) -> str:
    """A configuração da casa citada e emoldurada — ou nada.

    Três cuidados, os três refutados antes de escritos:

    - **Ilegível de qualquer natureza segue puro** — inclusive UTF-8
      quebrado: editor de Windows salva cp1252, `UnicodeDecodeError` não é
      `OSError`, e sem o pega a corrente inteira morria sem recibo (medido).
    - **Cada linha entra citada (`> `)**: config que imita o cabeçalho ou o
      separador viraria limite falso entre config e prompt; citada, só as
      linhas SEM o prefixo são a moldura de verdade (medido: duas molduras
      idênticas no mesmo prompt sem isso).
    - **Teto de sanidade**: config de casa é uma página; acima do teto o
      prompt segue puro com aviso no stderr — estourar o contexto da sessão
      longe da causa é o defeito mais caro de achar.
    """
    configuracao = Path(cwd) / "configuracao-da-casa.md"
    try:
        texto = configuracao.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    if len(texto) > TETO_CONFIGURACAO:
        print(f"AVISO: {configuracao} tem {len(texto)} caracteres (teto "
              f"{TETO_CONFIGURACAO}) — configuração de casa é uma página; "
              "o prompt seguiu sem ela.", file=sys.stderr)
        return ""
    citado = "\n".join("> " + linha for linha in texto.splitlines())
    return ("CONFIGURAÇÃO DA CASA — as linhas citadas com '> ' logo abaixo "
            "valem antes de criar issue ou escolher endereço de trabalho:\n\n"
            + citado + "\n---\n\n")


def _prompt_da_sessao(etapa: dict, cwd) -> str:
    """O prompt do manifesto, com as regras e a configuração na frente.

    A casa declara em `configuracao-da-casa.md` (raiz do `--cwd`) onde issue
    nasce, com que nome e em que fila — e a sessão da corrente não tem outra
    fonte: ela nasce sem contexto e decidiria de cabeça. O arquivo entra
    inteiro, não como endereço, porque a sessão pode rodar em worktree ou
    com leitura restrita — o que o manifesto quer que ela saiba viaja no
    prompt, como o contrato já viaja no `--json-schema`.

    A ordem é semântica: regras antes da configuração, configuração antes
    do pedido — regra dura chega primeiro, como conteúdo nenhum chega.
    """
    return (_bloco_de_regras(cwd) + _bloco_de_configuracao(cwd)
            + etapa["prompt"])


def _comando_sessao(etapa: dict) -> list:
    # O --dangerously-skip-permissions vem da receita (executar.sh): sessão
    # de rotina não tem quem responder prompt. Por isso o docstring manda
    # rodar a corrente em worktree ou clone descartável.
    #
    # O --bare é deliberado, e alinhado ao desenho: a doc o recomenda para
    # chamada em script (e anuncia que virará o default do -p). Tudo o que a
    # etapa precisa saber viaja no PROMPT, injetado por código — regras,
    # configuração da casa, pedido; gancho, plugin e MCP da casa onde a
    # corrente roda ficam de fora de propósito, determinismo antes de tudo.
    return ["claude", "-p", "--bare", "--output-format", "json",
            "--json-schema", _guia_da_sessao(),
            "--max-turns", str(etapa.get("max-turnos", 16)),
            "--dangerously-skip-permissions"]


def rodar_etapa(etapa, ordem, trabalho, dir_base, cwd, ambiente, teto,
                materializados=None):
    """Roda a etapa e devolve o caminho do recibo materializado."""
    base = ["--dir", dir_base, "--trabalho", trabalho,
            "--etapa", etapa["nome"], "--ordem", str(ordem), "--teto", str(teto)]

    if not etapa.get("ligada", True):
        feito = _cli_recibo(["sintetico"] + base + ["--motivo", "desligada"])
        return feito.stdout.strip()

    if etapa["tipo"] == "conferencia":
        return _rodar_conferencia(etapa, base, ordem, trabalho, dir_base, cwd,
                                  ambiente, materializados)
    if etapa["tipo"] == "portao":
        return _rodar_portao(etapa, base, cwd, dir_base, trabalho)

    # O log completo é herança da receita (ultima-execucao.log): stderr de
    # etapa boa não evapora, e o proximo do para sintético cita um log que
    # EXISTE (medido: antes citava log nenhum).
    previsto, _ = _recibo.caminho_do_recibo(dir_base, trabalho, ordem,
                                            etapa["nome"])
    log = previsto.with_suffix(".log")
    log.parent.mkdir(parents=True, exist_ok=True)

    try:
        if etapa["tipo"] == "codigo":
            codigo_saida, saida, erro = _rodar_processo(
                etapa["comando"], shell=True, cwd=cwd, env=ambiente,
                entrada=None, tempo=etapa.get("tempo-limite", TEMPO_CODIGO))
        else:  # sessao
            codigo_saida, saida, erro = _rodar_processo(
                _comando_sessao(etapa), shell=False, cwd=cwd, env=ambiente,
                entrada=_prompt_da_sessao(etapa, cwd),
                tempo=etapa.get("tempo-limite", TEMPO_SESSAO))
    except TempoEstourado as estouro:
        log.write_text(f"{estouro}\n", encoding="utf-8")
        feito = _cli_recibo(["sintetico"] + base +
                            ["--motivo", "morta",
                             "--detalhe", f"{estouro} — leia {log}"])
        return feito.stdout.strip()

    log.write_text(f"--- stdout ---\n{saida}\n--- stderr ---\n{erro}",
                   encoding="utf-8")
    if codigo_saida != 0:
        feito = _cli_recibo(["sintetico"] + base +
                            ["--motivo", "morta",
                             "--detalhe", f"exit {codigo_saida} — leia {log}"])
        return feito.stdout.strip()
    feito = _cli_recibo(["materializar"] + base, entrada=saida)
    return feito.stdout.strip()


def _rodar_conferencia(etapa, base, ordem, trabalho, dir_base, cwd, ambiente,
                       materializados):
    """Confere os recibos DESTA execução e materializa o recibo da conferência.

    Só os desta execução, de propósito: recibo de ciclo anterior já foi
    conferido no tempo dele, e prova de git presa a ref móvel envelhece
    LEGITIMAMENTE quando a rodada é entregue (o merge move origin/homolog)
    — re-litigar ciclo antigo reprovava rodada sã (medido no ciclo 2 do
    primeiro pedido real). O contrato agora manda ancorar em SHA; a
    conferência da rodada confere a rodada.

    O log é a evidência: o provado do recibo cita `tail -n 1 <log>` — prova
    re-executável e estável. A conferência herda o MESMO ambiente das
    etapas (sem ele, prova com credencial do `ambiente.env` era acusada
    falsamente — medido).
    """
    previsto, _ = _recibo.caminho_do_recibo(dir_base, trabalho, ordem,
                                            etapa["nome"])
    log = previsto.with_suffix(".log")
    log.parent.mkdir(parents=True, exist_ok=True)

    alvos = list(materializados or [])
    if not alvos:
        log.write_text("nenhum recibo novo nesta execução — nada a conferir\n",
                       encoding="utf-8")
        envelope = {"veredito": "segue", "provado": [
            {"afirmacao": "nenhum recibo novo nesta execução",
             "comando": f"tail -n 1 {shlex.quote(str(log))}",
             "saida": "nenhum recibo novo nesta execução — nada a conferir"}],
            "suposto": [], "faltas": []}
        completo = {"etapa": "x", "trabalho": "x",
                    "quando": "2000-01-01T00:00:00Z",
                    "ciclo": {"i": 1, "teto": 1}, **envelope}
        feito = _cli_recibo(["materializar"] + base,
                            entrada=json.dumps(completo, ensure_ascii=False))
        return feito.stdout.strip()

    saidas, pior = [], 0
    for alvo in alvos:
        try:
            codigo_um, saida_um, erro_um = _rodar_processo(
                [sys.executable, str(CONFERIR), "recibo", str(alvo),
                 "--cwd", cwd], shell=False, cwd=None, env=ambiente,
                entrada=None, tempo=etapa.get("tempo-limite", TEMPO_CODIGO))
        except TempoEstourado as estouro:
            log.write_text("\n".join(saidas) + f"\n{estouro}\n",
                           encoding="utf-8")
            feito = _cli_recibo(["sintetico"] + base +
                                ["--motivo", "morta",
                                 "--detalhe", f"conferência: {estouro}"])
            return feito.stdout.strip()
        saidas.append(f"--- {Path(alvo).name}\n{saida_um}{erro_um}".strip())
        pior = max(pior, codigo_um)
    resumo = (f"conferidos {len(alvos)} recibos desta execução — "
              + ("nenhuma acusação" if pior == 0 else f"pior exit {pior}"))
    log.write_text("\n".join(saidas) + f"\n{resumo}\n", encoding="utf-8")
    codigo = 0 if pior == 0 else (4 if pior == 4 else 2)

    if codigo == 0:
        envelope = {"veredito": "segue", "provado": [
            {"afirmacao": "a conferência terminou sem acusações",
             # shlex.quote: caminho com espaço quebrava a re-execução da
             # evidência e a corrente honesta se autoacusava (medido).
             "comando": f"tail -n 1 {shlex.quote(str(log))}",
             "saida": resumo}],
            "suposto": [], "faltas": []}
    elif codigo == 4:
        acusacoes = [linha for linha in "\n".join(saidas).splitlines()
                     if linha.startswith("ACUSA")]
        envelope = {"veredito": "para", "provado": [], "suposto": [],
                    "faltas": acusacoes[:10] or ["conferência acusou"],
                    "proximo": (f"Leia {log}: corrija cada acusação (cada "
                                "uma nomeia o recibo e o motivo) e reexecute "
                                f"o trabalho {trabalho} a partir da etapa "
                                "acusada.")}
    else:
        feito = _cli_recibo(["sintetico"] + base +
                            ["--motivo", "morta",
                             "--detalhe", f"conferência com erro de ambiente "
                             f"(exit {codigo})"])
        return feito.stdout.strip()
    completo = {"etapa": "x", "trabalho": "x",
                "quando": "2000-01-01T00:00:00Z",
                "ciclo": {"i": 1, "teto": 1}, **envelope}
    feito = _cli_recibo(["materializar"] + base,
                        entrada=json.dumps(completo, ensure_ascii=False))
    return feito.stdout.strip()


def _rodar_portao(etapa, base, cwd, dir_base, trabalho):
    """Portão do dono: arquivo de aprovação presente segue; ausente pergunta."""
    arquivo = Path(cwd) / etapa["aprovacao"]
    if arquivo.is_file():
        envelope = {"veredito": "segue", "provado": [
            {"afirmacao": "a aprovação do dono está registrada",
             "comando": f"test -f {shlex.quote(str(arquivo))} && echo aprovado",
             "saida": "aprovado"}], "suposto": [], "faltas": []}
    else:
        pasta = Path(dir_base) / trabalho
        envelope = {"veredito": "pergunta", "provado": [], "suposto": [],
                    "faltas": [],
                    "pergunta": (f"Recomendo aprovar depois de ler os recibos "
                                 f"em {pasta}. Aprova a etapa "
                                 f"{etapa['nome']}? Para aprovar, crie o "
                                 f"arquivo {arquivo}.")}
    completo = {"etapa": "x", "trabalho": "x",
                "quando": "2000-01-01T00:00:00Z",
                "ciclo": {"i": 1, "teto": 1}, **envelope}
    feito = _cli_recibo(["materializar"] + base,
                        entrada=json.dumps(completo, ensure_ascii=False))
    return feito.stdout.strip()


# ---------------------------------------------------------------------------
# O ensaio e a execução.
# ---------------------------------------------------------------------------

def _rotulo(etapa, ordem):
    if not etapa.get("ligada", True):
        texto = f"{ordem:02d}-{etapa['nome']} [desligada — recibo de skip]"
    elif etapa["tipo"] == "codigo":
        texto = f"{ordem:02d}-{etapa['nome']} [codigo: {etapa['comando']}]"
    elif etapa["tipo"] == "sessao":
        texto = (f"{ordem:02d}-{etapa['nome']} "
                 f"[sessao: claude -p --bare --output-format json "
                 f"--json-schema <contrato sem allOf> --max-turns "
                 f"{etapa.get('max-turnos', 16)}]")
    elif etapa["tipo"] == "portao":
        texto = (f"{ordem:02d}-{etapa['nome']} "
                 f"[portao: aprovação em {etapa['aprovacao']}]")
    else:
        texto = f"{ordem:02d}-{etapa['nome']} [conferencia]"
    # Quebra de linha embutida no comando forjava linha de onda na
    # listagem do ensaio (medido) — o rótulo é sempre uma linha só.
    return texto.replace("\r", "\\r").replace("\n", "\\n")


def ensaio(manifesto, trabalho, dir_base) -> int:
    """Lista a corrente inteira. NADA executa, NADA é lido além do manifesto."""
    etapas = manifesto["etapas"]
    ordem_de = {e["nome"]: n for n, e in enumerate(etapas, start=1)}
    print(f"ensaio do trabalho {trabalho} — nada será executado:")
    for n, onda in enumerate(ondas_de(etapas), start=1):
        marca = "[só]" if onda[0]["tipo"] in SOZINHAS else (
            f"[fork de {len(onda)}]" if len(onda) > 1 else "[uma]")
        nomes = ", ".join(_rotulo(e, ordem_de[e["nome"]]) for e in onda)
        print(f"  onda {n} {marca}: {nomes}")
    print(f"recibos iriam para: {Path(dir_base) / trabalho}/")
    return 0


def _contar_paras(pasta: Path) -> int:
    total = 0
    if not pasta.is_dir():
        return 0
    for arquivo in pasta.glob("*.json"):
        try:
            dado = json.loads(arquivo.read_text(encoding="utf-8"))
            if not isinstance(dado, dict):
                # JSON válido que não é objeto ([]) derrubava a contagem
                # com traceback (medido) — trata igual ao ilegível.
                raise ValueError("não é um objeto de recibo")
            if dado.get("veredito") == "para":
                total += 1
        except (OSError, ValueError):
            # Conservador de propósito: um recibo corrompido reabria a
            # corrente além do teto em silêncio (medido). Ilegível conta
            # como para — só pode parar mais cedo, nunca rodar demais.
            print(f"AVISO: recibo ilegível {arquivo.name} conta como para "
                  "no teto.", file=sys.stderr)
            total += 1
    return total


def executar(manifesto, trabalho, dir_base, cwd) -> int:
    etapas = manifesto["etapas"]
    teto = manifesto.get("teto", 3)
    ordem_de = {e["nome"]: n for n, e in enumerate(etapas, start=1)}
    pasta = Path(dir_base) / trabalho

    if _contar_paras(pasta) >= teto:
        primeira = etapas[0]
        feito = _cli_recibo(["sintetico", "--dir", dir_base, "--trabalho",
                             trabalho, "--etapa", primeira["nome"], "--ordem",
                             str(ordem_de[primeira["nome"]]), "--teto",
                             str(teto), "--motivo", "teto-esgotado"])
        print(feito.stdout.strip())
        print(f"teto de {teto} ciclos esgotado — nada rodou; a decisão é do dono.")
        return 5

    ambiente = montar_ambiente(manifesto, cwd, dict(os.environ))
    # O cheque precoce da receita: sem ele, a corrente executava meia onda
    # com efeito colateral antes de descobrir que a sessão não abriria.
    if any(e["tipo"] == "sessao" and e.get("ligada", True) for e in etapas) \
            and not shutil.which("claude", path=ambiente.get("PATH")):
        print("erro de ambiente: há etapa de sessão e o comando claude não "
              "está no PATH — nada rodou.", file=sys.stderr)
        return 2
    materializados = []
    for n, onda in enumerate(ondas_de(etapas), start=1):
        marca = "[só]" if onda[0]["tipo"] in SOZINHAS else (
            f"[fork de {len(onda)}]" if len(onda) > 1 else "[uma]")
        print(f"onda {n} {marca}: {', '.join(e['nome'] for e in onda)}")
        with concurrent.futures.ThreadPoolExecutor(len(onda)) as executor:
            caminhos = list(executor.map(
                lambda etapa: rodar_etapa(etapa, ordem_de[etapa["nome"]],
                                          trabalho, dir_base, cwd, ambiente,
                                          teto, materializados), onda))
        materializados.extend(caminho for caminho in caminhos if caminho)
        for caminho in caminhos:
            if not caminho or not Path(caminho).is_file():
                print("defeito no encadeador: uma etapa terminou sem recibo "
                      "no disco — corrija encadeador.py", file=sys.stderr)
                return 2
            recibo_dado = json.loads(Path(caminho).read_text(encoding="utf-8"))
            veredito = recibo_dado["veredito"]
            print(f"  {Path(caminho).name}: {veredito}")
            if veredito == "para":
                print(f"parou — o proximo de quem reprovou:\n"
                      f"  {recibo_dado.get('proximo', '')}")
                return 5
            if veredito == "pergunta":
                print(f"parou — aguardando o dono:\n"
                      f"  {recibo_dado.get('pergunta', '')}")
                return 6
    print(f"corrente completa: {len(etapas)} etapas, recibos em {pasta}/")
    return 0


# [0-9] e não \d: dígito Unicode no nome ('c１０') dirigiria a leitura do
# ciclo — a mesma emenda do recibo.py.
PADRAO_NOME_RECIBO = re.compile(r"^([0-9]+)-(.+)-c([0-9]+)\.json$")


def andamento(trabalho, dir_base, etapas_do_manifesto=None) -> int:
    """Fotografa os recibos do trabalho e imprime o JSON do contrato.

    Só leitura: nada roda, nada nasce. O contrato completo está no
    docstring do módulo; a régua do teto é a MESMA do motor: todo *.json da
    pasta conta — ilegível conta como para, com aviso. Só quem casa o padrão
    de nome vira etapa. Com o manifesto, `completa` é prova, não inferência.
    """
    pasta = Path(dir_base) / trabalho
    avisos = []
    correntes = {}
    paras, teto = 0, None
    if not pasta.is_dir():
        avisos.append(f"o diretório {pasta} não existe — o trabalho nunca "
                      "rodou aqui, ou o nome/--dir está errado")
    for arquivo in sorted(pasta.glob("*.json")) if pasta.is_dir() else []:
        try:
            dado = json.loads(arquivo.read_text(encoding="utf-8"))
            if not isinstance(dado, dict):
                raise ValueError("não é um objeto de recibo")
        except (OSError, ValueError):
            avisos.append(f"recibo ilegível: {arquivo.name} — conta como "
                          "para no teto")
            paras += 1
            continue
        if dado.get("veredito") == "para":
            paras += 1
        ciclo = dado.get("ciclo", {})
        if isinstance(ciclo, dict) and _inteiro_sao(ciclo.get("teto", 0)):
            teto = ciclo["teto"]
        pedacos = PADRAO_NOME_RECIBO.match(arquivo.name)
        if not pedacos:
            avisos.append(f"{arquivo.name} não tem nome de recibo — lido "
                          "para o teto, fora das etapas")
            continue
        chave = (int(pedacos.group(1)), pedacos.group(2))
        vez = int(pedacos.group(3))
        if chave not in correntes or vez > correntes[chave][0]:
            correntes[chave] = (vez, dado)

    etapas = []
    for ordem, nome in sorted(correntes):
        _, dado = correntes[(ordem, nome)]
        etapas.append({"ordem": ordem, "nome": nome,
                       "veredito": dado.get("veredito"),
                       "ciclo": dado.get("ciclo"),
                       "faltas": dado.get("faltas", []),
                       "proximo": dado.get("proximo"),
                       "pergunta": dado.get("pergunta")})

    parado = next((e for e in etapas if e["veredito"] == "para"), None)
    aguarda = next((e for e in etapas if e["veredito"] == "pergunta"), None)
    sem_recibo = []
    if etapas_do_manifesto is not None:
        com_recibo = {nome for _, nome in correntes}
        sem_recibo = [e["nome"] for e in etapas_do_manifesto
                      if e.get("ligada", True) and e["nome"] not in com_recibo]
    if not etapas:
        estado = "em-curso"
        acao = (f"nada rodou ainda — rode: python "
                f".agents/encadeador/encadeador.py executar --manifesto <M> "
                f"--trabalho {trabalho} --dir {dir_base}")
    elif teto is not None and paras >= teto:
        estado = "parada"
        acao = (f"teto de {teto} ciclos esgotado — a decisão é do dono; "
                f"leia os recibos em {pasta}")
    elif parado:
        estado = "parada"
        acao = parado["proximo"] or (f"leia o recibo da etapa "
                                     f"{parado['nome']} em {pasta}")
    elif aguarda:
        estado = "aguardando-portao"
        acao = aguarda["pergunta"] or (f"leia o recibo da etapa "
                                       f"{aguarda['nome']} em {pasta}")
    elif sem_recibo:
        # A prova que o manifesto compra: etapa ligada sem recibo é corrente
        # por rodar — ou morta no meio, e "completa" aqui seria o zero que
        # mente do próprio instrumento.
        estado = "em-curso"
        acao = ("etapa ligada sem recibo: " + ", ".join(sem_recibo)
                + " — a corrente ainda não passou por ela (ou morreu antes; "
                "o exit de quem executou é a fonte)")
    else:
        estado = "completa"
        acao = f"nada a fazer — corrente completa; recibos em {pasta}"

    print(json.dumps({"trabalho": trabalho, "dir": dir_base,
                      "estado": estado, "etapas": etapas, "paras": paras,
                      "teto": teto, "avisos": avisos, "proxima_acao": acao},
                     ensure_ascii=False, indent=2))
    return 0


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="encadeador.py")
    sub = parser.add_subparsers(dest="comando", required=True)
    for nome_cmd, ajuda in (("ensaio", "lista a corrente sem executar nada"),
                            ("executar", "roda a corrente e deixa os recibos")):
        p = sub.add_parser(nome_cmd, help=ajuda)
        p.add_argument("--manifesto", required=True)
        p.add_argument("--trabalho", required=True)
        p.add_argument("--dir", default="recibos")
        p.add_argument("--cwd", default=".")
    p = sub.add_parser("andamento",
                       help="fotografa os recibos do trabalho em JSON")
    p.add_argument("--trabalho", required=True)
    p.add_argument("--dir", default="recibos")
    p.add_argument("--manifesto", help="opcional: torna `completa` prova, "
                   "não inferência")
    return parser


def main(argv) -> int:
    # Linha a linha mesmo com o stdout redirecionado: rodando destacado, o
    # buffer segurava as ondas até o fim e o acompanhamento ficava mudo
    # (medido no primeiro pedido real).
    sys.stdout.reconfigure(line_buffering=True)
    args = montar_parser().parse_args(argv)
    esquema = _recibo.carregar_esquema()

    if args.comando == "andamento":
        problemas = _recibo._erros(esquema["properties"]["trabalho"],
                                   args.trabalho, "argumento --trabalho")
        etapas_do_manifesto = None
        if args.manifesto:
            try:
                manifesto = json.loads(
                    Path(args.manifesto).read_text(encoding="utf-8"))
            except (OSError, ValueError) as erro:
                problemas.append(f"não li o manifesto {args.manifesto}: {erro}")
            else:
                problemas += validar_manifesto(manifesto, esquema)
                etapas_do_manifesto = manifesto.get("etapas") \
                    if not problemas else None
        if problemas:
            for problema in problemas:
                print(f"erro de uso: {problema}", file=sys.stderr)
            return 2
        return andamento(args.trabalho, str(Path(args.dir).resolve()),
                         etapas_do_manifesto)

    try:
        manifesto = json.loads(Path(args.manifesto).read_text(encoding="utf-8"))
    except (OSError, ValueError) as erro:
        print(f"erro de uso: não li o manifesto {args.manifesto}: {erro}",
              file=sys.stderr)
        return 2
    problemas = validar_manifesto(manifesto, esquema)
    problemas += _recibo._erros(esquema["properties"]["trabalho"],
                                args.trabalho, "argumento --trabalho")
    if not Path(args.cwd).is_dir():
        problemas.append(f"argumento --cwd: {args.cwd} não existe")
    if problemas:
        for problema in problemas:
            print(f"erro de uso: {problema}", file=sys.stderr)
        return 2

    # Caminhos ABSOLUTOS daqui em diante: evidência de conferência com
    # caminho relativo misturava dois referenciais no mesmo recibo (o cwd
    # de invocação e o --cwd da etapa) e fabricava acusação falsa (medido).
    dir_base = str(Path(args.dir).resolve())
    cwd = str(Path(args.cwd).resolve())

    if args.comando == "ensaio":
        return ensaio(manifesto, args.trabalho, dir_base)
    return executar(manifesto, args.trabalho, dir_base, cwd)


# ---------------------------------------------------------------------------
# Os testes: o que o encadeador faz e o que ele recusa — com a sentinela do
# ensaio e o fork provado por encontro marcado (rendezvous).
# ---------------------------------------------------------------------------

FANTOCHE_OK = ("python3 -c \"import json; print(json.dumps({'etapa':'x',"
               "'trabalho':'x','quando':'2000-01-01T00:00:00Z','veredito':"
               "'segue','provado':[{'afirmacao':'a fantoche rodou','comando':"
               "'true','saida':''}],'suposto':[],'faltas':[],'ciclo':"
               "{'i':1,'teto':1}}))\"")


def _manifesto(pasta, nome, conteudo):
    caminho = Path(pasta) / nome
    caminho.write_text(json.dumps(conteudo, ensure_ascii=False),
                       encoding="utf-8")
    return str(caminho)


def _cli(argumentos):
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve())] + argumentos,
        capture_output=True, text=True, timeout=300)


RECUSA = [
    ("ciclo no grafo", {"etapas": [
        {"nome": "a", "tipo": "codigo", "comando": "true", "depende": ["b"]},
        {"nome": "b", "tipo": "codigo", "comando": "true", "depende": ["a"]}]},
     "ciclo"),
    ("dependência fantasma", {"etapas": [
        {"nome": "a", "tipo": "codigo", "comando": "true",
         "depende": ["nao-existe"]}]}, "não existe no manifesto"),
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
    ("portao sem aprovacao", {"etapas": [
        {"nome": "a", "tipo": "portao"}]}, "exige o campo aprovacao"),
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
    ("campo desconhecido na raiz do manifesto", {"tetos": 3, "etapas": [
        {"nome": "a", "tipo": "codigo", "comando": "true"}]},
     "campo desconhecido"),
]


def _comportamento(pasta):
    resultados = []

    def caso(rotulo, condicao):
        resultados.append((rotulo, bool(condicao)))

    recibos = str(Path(pasta) / "recibos")

    # a) ensaio-sentinela: a corrente inteira listada, NADA executado
    sentinela = Path(pasta) / "sentinela.txt"
    manifesto = _manifesto(pasta, "m-sentinela.json", {"etapas": [
        {"nome": "grava", "tipo": "codigo",
         "comando": f"touch {sentinela} && {FANTOCHE_OK}"},
        {"nome": "confere", "tipo": "conferencia", "depende": ["grava"]},
    ]})
    resposta = _cli(["ensaio", "--manifesto", manifesto, "--trabalho",
                     "t-sentinela", "--dir", recibos, "--cwd", pasta])
    caso("ensaio lista as duas ondas e sai 0",
         resposta.returncode == 0 and "onda 1" in resposta.stdout
         and "onda 2 [só]" in resposta.stdout)
    caso("ensaio não executa nada: a sentinela NÃO existe",
         not sentinela.exists())
    caso("ensaio não escreve recibo nenhum",
         not (Path(recibos) / "t-sentinela").exists())

    # b) contraprova: executar grava a sentinela e materializa os recibos
    resposta = _cli(["executar", "--manifesto", manifesto, "--trabalho",
                     "t-sentinela", "--dir", recibos, "--cwd", pasta])
    caso("contraprova: sem ensaio a sentinela aparece e a corrente completa",
         resposta.returncode == 0 and sentinela.exists()
         and (Path(recibos) / "t-sentinela" / "01-grava-c1.json").exists()
         and (Path(recibos) / "t-sentinela" / "02-confere-c1.json").exists())

    # c) fork provado por encontro marcado: A e B esperam a marca um do outro
    marca_a, marca_b = Path(pasta) / "marca-a", Path(pasta) / "marca-b"

    def espera(minha, outra):
        return (f"touch {minha} && for i in $(seq 1 50); do "
                f"[ -f {outra} ] && break; sleep 0.1; done; "
                f"[ -f {outra} ] && " + FANTOCHE_OK)

    manifesto = _manifesto(pasta, "m-fork.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo",
         "comando": espera(marca_a, marca_b)},
        {"nome": "bb", "tipo": "codigo",
         "comando": espera(marca_b, marca_a)},
        {"nome": "cc", "tipo": "codigo", "comando": FANTOCHE_OK,
         "depende": ["aa", "bb"]},
    ]})
    resposta = _cli(["executar", "--manifesto", manifesto, "--trabalho",
                     "t-fork", "--dir", recibos, "--cwd", pasta])
    caso("fork real: as duas se veem rodando (encontro marcado) e o join vem",
         resposta.returncode == 0 and "fork de 2" in resposta.stdout
         and (Path(recibos) / "t-fork" / "03-cc-c1.json").exists())

    # d) conferência nunca em paralelo, mesmo sem dependência declarada
    manifesto = _manifesto(pasta, "m-solo.json", {"etapas": [
        {"nome": "confere", "tipo": "conferencia"},
        {"nome": "aa", "tipo": "codigo", "comando": FANTOCHE_OK},
    ]})
    resposta = _cli(["ensaio", "--manifesto", manifesto, "--trabalho",
                     "t-solo", "--dir", recibos, "--cwd", pasta])
    caso("conferência pronta junto ganha onda própria [só]",
         "onda 1 [só]: 01-confere" in resposta.stdout)

    # e) etapa desligada vira skip e a corrente segue
    manifesto = _manifesto(pasta, "m-skip.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo", "comando": FANTOCHE_OK},
        {"nome": "bb", "tipo": "codigo", "comando": FANTOCHE_OK,
         "ligada": False, "depende": ["aa"]},
        {"nome": "cc", "tipo": "codigo", "comando": FANTOCHE_OK,
         "depende": ["bb"]},
    ]})
    resposta = _cli(["executar", "--manifesto", manifesto, "--trabalho",
                     "t-skip", "--dir", recibos, "--cwd", pasta])
    meio = json.loads((Path(recibos) / "t-skip" / "02-bb-c1.json")
                      .read_text(encoding="utf-8"))
    caso("desligada registra o skip e não impede a terceira",
         resposta.returncode == 0 and meio["motivo"] == "desligada"
         and (Path(recibos) / "t-skip" / "03-cc-c1.json").exists())

    # f) etapa que morre para a corrente: quem depende dela não roda
    manifesto = _manifesto(pasta, "m-morte.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo", "comando": "exit 9"},
        {"nome": "bb", "tipo": "codigo", "comando": FANTOCHE_OK,
         "depende": ["aa"]},
    ]})
    resposta = _cli(["executar", "--manifesto", manifesto, "--trabalho",
                     "t-morte", "--dir", recibos, "--cwd", pasta])
    caso("morte vira para sintético, exit 5, e o dependente nem roda",
         resposta.returncode == 5
         and not (Path(recibos) / "t-morte" / "02-bb-c1.json").exists())

    # g) stdout que não é recibo vira para recibo-invalido e para a corrente
    manifesto = _manifesto(pasta, "m-lixo.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo", "comando": "echo isto-nao-e-recibo"},
        {"nome": "bb", "tipo": "codigo", "comando": FANTOCHE_OK,
         "depende": ["aa"]},
    ]})
    resposta = _cli(["executar", "--manifesto", manifesto, "--trabalho",
                     "t-lixo", "--dir", recibos, "--cwd", pasta])
    primeiro = json.loads((Path(recibos) / "t-lixo" / "01-aa-c1.json")
                          .read_text(encoding="utf-8"))
    caso("stdout-lixo vira para recibo-invalido e a corrente para",
         resposta.returncode == 5 and primeiro["motivo"] == "recibo-invalido")

    # h) teto pela contagem: com teto recibos para, nada roda
    manifesto = _manifesto(pasta, "m-teto.json", {"teto": 2, "etapas": [
        {"nome": "aa", "tipo": "codigo",
         "comando": f"touch {Path(pasta) / 'teto-rodou'} && {FANTOCHE_OK}"},
    ]})
    for _ in range(2):
        _cli_recibo(["sintetico", "--dir", recibos, "--trabalho", "t-teto",
                     "--etapa", "aa", "--ordem", "1", "--teto", "2",
                     "--motivo", "morta", "--detalhe", "plantado no teste"])
    resposta = _cli(["executar", "--manifesto", manifesto, "--trabalho",
                     "t-teto", "--dir", recibos, "--cwd", pasta])
    caso("teto esgotado: nada roda e nasce o para teto-esgotado",
         resposta.returncode == 5
         and not (Path(pasta) / "teto-rodou").exists()
         and "teto-esgotado" in
         (Path(recibos) / "t-teto" / "01-aa-c3.json")
         .read_text(encoding="utf-8"))

    # i) portão sem aprovação pergunta e para; com aprovação, segue
    aprovacao = Path(pasta) / "aprovacoes" / "pr.ok"
    manifesto = _manifesto(pasta, "m-portao.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo", "comando": FANTOCHE_OK},
        {"nome": "aprova", "tipo": "portao",
         "aprovacao": str(aprovacao), "depende": ["aa"]},
    ]})
    resposta = _cli(["executar", "--manifesto", manifesto, "--trabalho",
                     "t-portao", "--dir", recibos, "--cwd", pasta])
    caso("portão sem aprovação: veredito pergunta e exit 6",
         resposta.returncode == 6 and "Aprova a etapa" in resposta.stdout)
    aprovacao.parent.mkdir(parents=True, exist_ok=True)
    aprovacao.write_text("aprovado pelo dono\n", encoding="utf-8")
    resposta = _cli(["executar", "--manifesto", manifesto, "--trabalho",
                     "t-portao-2", "--dir", recibos, "--cwd", pasta])
    caso("portão com aprovação registrada segue",
         resposta.returncode == 0)

    # j) conferência acusa forja DESTA execução: para com o log de evidência
    FORJA = ("python3 -c \"import json; print(json.dumps({'etapa':'x',"
             "'trabalho':'x','quando':'2000-01-01T00:00:00Z','veredito':"
             "'segue','provado':[{'afirmacao':'eco','comando':'echo ola',"
             "'saida':'adeus'}],'suposto':[],'faltas':[],'ciclo':"
             "{'i':1,'teto':3}}))\"")
    manifesto = _manifesto(pasta, "m-confere.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo", "comando": FORJA},
        {"nome": "confere", "tipo": "conferencia", "depende": ["aa"]},
    ]})
    resposta = _cli(["executar", "--manifesto", manifesto, "--trabalho",
                     "t-forja", "--dir", recibos, "--cwd", pasta])
    recibo_conf = json.loads(
        (Path(recibos) / "t-forja" / "02-confere-c1.json")
        .read_text(encoding="utf-8"))
    caso("conferência acusa a forja: para com as acusações nas faltas",
         resposta.returncode == 5 and recibo_conf["veredito"] == "para"
         and any("diverge" in falta for falta in recibo_conf["faltas"])
         and (Path(recibos) / "t-forja" / "02-confere-c1.log").exists())

    # j2) recibo ENVELHECIDO de ciclo anterior não reprova rodada sã: a
    #     conferência da rodada confere a rodada (o achado do ciclo 2 real)
    envelhecido = {"etapa": "aa", "trabalho": "t-envelhecido",
                   "quando": "2026-08-16T12:00:00-03:00", "veredito": "segue",
                   "provado": [{"afirmacao": "a marca da rodada antiga existe",
                                "comando": "test -f marca-que-ja-foi && echo ok",
                                "saida": "ok"}],
                   "suposto": [], "faltas": [], "ciclo": {"i": 1, "teto": 3}}
    pasta_env = Path(recibos) / "t-envelhecido"
    pasta_env.mkdir(parents=True, exist_ok=True)
    (pasta_env / "01-aa-c1.json").write_text(
        json.dumps(envelhecido, ensure_ascii=False), encoding="utf-8")
    manifesto = _manifesto(pasta, "m-envelhecido.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo", "comando": FANTOCHE_OK},
        {"nome": "confere", "tipo": "conferencia", "depende": ["aa"]},
    ]})
    resposta = _cli(["executar", "--manifesto", manifesto, "--trabalho",
                     "t-envelhecido", "--dir", recibos, "--cwd", pasta])
    caso("prova envelhecida de ciclo anterior não reprova a rodada nova",
         resposta.returncode == 0)

    # k) o ambiente do manifesto chega à etapa (sem ecoar valor nenhum)
    arquivo_env = Path(pasta) / "fantoche.env"
    arquivo_env.write_text("# comentario\nVAR_FANTOCHE=chegou\n",
                           encoding="utf-8")
    manifesto = _manifesto(pasta, "m-env.json", {
        "ambiente": {"env": str(arquivo_env.name)},
        "etapas": [{"nome": "aa", "tipo": "codigo", "comando":
                    "python3 -c \"import json,os; print(json.dumps("
                    "{'etapa':'x','trabalho':'x',"
                    "'quando':'2000-01-01T00:00:00Z','veredito':'segue',"
                    "'provado':[],'suposto':["
                    "os.environ.get('VAR_FANTOCHE','ausente')],"
                    "'faltas':[],'ciclo':{'i':1,'teto':1}}))\""}]})
    resposta = _cli(["executar", "--manifesto", manifesto, "--trabalho",
                     "t-env", "--dir", recibos, "--cwd", pasta])
    escrito = json.loads((Path(recibos) / "t-env" / "01-aa-c1.json")
                         .read_text(encoding="utf-8"))
    caso("o arquivo de ambiente do manifesto chega à etapa",
         escrito["suposto"] == ["chegou"])

    # l) a sessão aparece no ensaio com o comando claude montado — sem rodar
    manifesto = _manifesto(pasta, "m-sessao.json", {"etapas": [
        {"nome": "pensa", "tipo": "sessao", "prompt": "pense"}]})
    resposta = _cli(["ensaio", "--manifesto", manifesto, "--trabalho",
                     "t-sessao", "--dir", recibos, "--cwd", pasta])
    caso("sessão listada no ensaio com claude -p, sem executar",
         resposta.returncode == 0 and "claude -p" in resposta.stdout
         and not (Path(recibos) / "t-sessao").exists())

    # m) estouro de tempo vira morta com log — e mata o grupo (sem órfão)
    manifesto = _manifesto(pasta, "m-tempo.json", {"etapas": [
        {"nome": "trava", "tipo": "codigo", "comando": "sleep 3737",
         "tempo-limite": 1},
        {"nome": "depois", "tipo": "codigo", "comando": FANTOCHE_OK,
         "depende": ["trava"]}]})
    resposta = _cli(["executar", "--manifesto", manifesto, "--trabalho",
                     "t-tempo", "--dir", recibos, "--cwd", pasta])
    recibo_tempo = json.loads(
        (Path(recibos) / "t-tempo" / "01-trava-c1.json")
        .read_text(encoding="utf-8"))
    orfaos = subprocess.run(["pgrep", "-f", "sleep 3737"],
                            capture_output=True, text=True)
    caso("estouro de tempo vira para morta, exit 5, com log",
         resposta.returncode == 5 and recibo_tempo["motivo"] == "morta"
         and "tempo-limite" in recibo_tempo["faltas"][0]
         and (Path(recibos) / "t-tempo" / "01-trava-c1.log").exists())
    caso("o grupo do processo morre junto — nenhum órfão",
         orfaos.returncode != 0)

    # n) o log da conferência leva o ciclo no nome: três rodadas, três logs
    manifesto = _manifesto(pasta, "m-ciclos.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo", "comando": FANTOCHE_OK},
        {"nome": "confere", "tipo": "conferencia", "depende": ["aa"]}]})
    for _ in range(3):
        resposta = _cli(["executar", "--manifesto", manifesto, "--trabalho",
                         "t-ciclos", "--dir", recibos, "--cwd", pasta])
    pasta_ciclos = Path(recibos) / "t-ciclos"
    caso("terceira rodada não se autoacusa e cada ciclo tem o próprio log",
         resposta.returncode == 0
         and (pasta_ciclos / "02-confere-c1.log").exists()
         and (pasta_ciclos / "02-confere-c2.log").exists()
         and (pasta_ciclos / "02-confere-c3.log").exists())

    # o) recibo para corrompido conta no teto (conservador)
    manifesto = _manifesto(pasta, "m-teto2.json", {"teto": 2, "etapas": [
        {"nome": "aa", "tipo": "codigo",
         "comando": f"touch {Path(pasta) / 'teto2-rodou'} && {FANTOCHE_OK}"}]})
    _cli_recibo(["sintetico", "--dir", recibos, "--trabalho", "t-teto2",
                 "--etapa", "aa", "--ordem", "1", "--teto", "2",
                 "--motivo", "morta", "--detalhe", "plantado"])
    (Path(recibos) / "t-teto2" / "01-aa-c9.json").write_text(
        "{ para corrompido", encoding="utf-8")
    resposta = _cli(["executar", "--manifesto", manifesto, "--trabalho",
                     "t-teto2", "--dir", recibos, "--cwd", pasta])
    caso("recibo corrompido conta no teto: nada roda",
         resposta.returncode == 5
         and not (Path(pasta) / "teto2-rodou").exists())

    # p) stderr de etapa boa fica no log (a herança do ultima-execucao.log)
    manifesto = _manifesto(pasta, "m-stderr.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo",
         "comando": f"echo aviso-no-stderr >&2; {FANTOCHE_OK}"}]})
    _cli(["executar", "--manifesto", manifesto, "--trabalho", "t-stderr",
          "--dir", recibos, "--cwd", pasta])
    caso("stderr de etapa boa não evapora: está no log",
         "aviso-no-stderr" in
         (Path(recibos) / "t-stderr" / "01-aa-c1.log")
         .read_text(encoding="utf-8"))

    # q) ambiente.env com aspas chega limpo (semântica do source)
    (Path(pasta) / "aspas.env").write_text(
        'VAR_ASPAS="entre aspas"\nVAR_COMENTARIO=valor # comentario\n',
        encoding="utf-8")
    manifesto = _manifesto(pasta, "m-aspas.json", {
        "ambiente": {"env": "aspas.env"},
        "etapas": [{"nome": "aa", "tipo": "codigo", "comando":
                    "python3 -c \"import json,os; print(json.dumps("
                    "{'etapa':'x','trabalho':'x',"
                    "'quando':'2000-01-01T00:00:00Z','veredito':'segue',"
                    "'provado':[],'suposto':["
                    "os.environ.get('VAR_ASPAS',''),"
                    "os.environ.get('VAR_COMENTARIO','')],"
                    "'faltas':[],'ciclo':{'i':1,'teto':1}}))\""}]})
    _cli(["executar", "--manifesto", manifesto, "--trabalho", "t-aspas",
          "--dir", recibos, "--cwd", pasta])
    escrito = json.loads((Path(recibos) / "t-aspas" / "01-aa-c1.json")
                         .read_text(encoding="utf-8"))
    caso("aspas envolventes e comentário caem como no source",
         escrito["suposto"] == ["entre aspas", "valor"])

    # s) JSON válido que não é objeto conta no teto sem traceback
    manifesto = _manifesto(pasta, "m-lista.json", {"teto": 1, "etapas": [
        {"nome": "aa", "tipo": "codigo",
         "comando": f"touch {Path(pasta) / 'lista-rodou'} && {FANTOCHE_OK}"}]})
    pasta_lista = Path(recibos) / "t-lista"
    pasta_lista.mkdir(parents=True, exist_ok=True)
    (pasta_lista / "01-aa-c9.json").write_text("[]", encoding="utf-8")
    resposta = _cli(["executar", "--manifesto", manifesto, "--trabalho",
                     "t-lista", "--dir", recibos, "--cwd", pasta])
    caso("JSON não-objeto no diretório conta no teto, sem traceback",
         resposta.returncode == 5
         and not (Path(pasta) / "lista-rodou").exists())

    # t) caminho com espaço: evidência citada com aspas re-executa limpa
    pasta_espaco = Path(pasta) / "com espaco"
    (pasta_espaco / "aprovacoes").mkdir(parents=True, exist_ok=True)
    (pasta_espaco / "aprovacoes" / "pr.ok").write_text("ok", encoding="utf-8")
    manifesto = _manifesto(pasta, "m-espaco.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo", "comando": FANTOCHE_OK},
        {"nome": "confere", "tipo": "conferencia", "depende": ["aa"]},
        {"nome": "aprova", "tipo": "portao",
         "aprovacao": "aprovacoes/pr.ok", "depende": ["confere"]}]})
    recibos_espaco = str(pasta_espaco / "recibos")
    exits = [_cli(["executar", "--manifesto", manifesto, "--trabalho",
                   "t-espaco", "--dir", recibos_espaco,
                   "--cwd", str(pasta_espaco)]).returncode
             for _ in range(2)]
    caso("caminho com espaço: dois ciclos completos sem autoacusação",
         exits == [0, 0])

    # u) a conferência herda o ambiente das etapas: prova que depende de
    #    variável do ambiente.env re-executa com ela (o defeito do primeiro
    #    pedido real: etapa provava com credencial, conferência rodava sem)
    (Path(pasta) / "herda.env").write_text("VAR_HERDA=confere\n",
                                           encoding="utf-8")
    manifesto = _manifesto(pasta, "m-herda.json", {
        "ambiente": {"env": "herda.env"},
        "etapas": [
            {"nome": "aa", "tipo": "codigo", "comando":
             "python3 -c \"import json; print(json.dumps("
             "{'etapa':'x','trabalho':'x',"
             "'quando':'2000-01-01T00:00:00Z','veredito':'segue',"
             "'provado':[{'afirmacao':'a variavel do ambiente chega',"
             "'comando':'test \\\\\\\"$VAR_HERDA\\\\\\\" = confere && echo ok',"
             "'saida':'ok'}],"
             "'suposto':[],'faltas':[],'ciclo':{'i':1,'teto':1}}))\""},
            {"nome": "confere", "tipo": "conferencia", "depende": ["aa"]}]})
    resposta = _cli(["executar", "--manifesto", manifesto, "--trabalho",
                     "t-herda", "--dir", recibos, "--cwd", pasta])
    caso("conferência herda o ambiente: prova com variável re-executa",
         resposta.returncode == 0)

    # v) a configuração da casa entra no prompt da sessão — e sem o arquivo
    #    o prompt segue puro (casa sem o molde ainda funciona)
    etapa_sessao = {"nome": "s", "tipo": "sessao", "prompt": "faça"}
    caso("sem configuracao-da-casa.md o prompt da sessão segue puro",
         _prompt_da_sessao(etapa_sessao, pasta) == "faça")
    (Path(pasta) / "configuracao-da-casa.md").write_text(
        "# Configuração da casa\nissues nascem em dono/repositorio\n",
        encoding="utf-8")
    montado = _prompt_da_sessao(etapa_sessao, pasta)
    caso("com o arquivo, a configuração da casa vem antes do prompt",
         montado.startswith("CONFIGURAÇÃO DA CASA")
         and "issues nascem em dono/repositorio" in montado
         and montado.endswith("faça"))
    caso("as linhas da configuração entram citadas",
         "> issues nascem em dono/repositorio" in montado)

    # v2) os três cuidados refutados: UTF-8 quebrado segue puro (editor de
    #     Windows salva cp1252 e UnicodeDecodeError não é OSError — a
    #     corrente morria sem recibo); imitação não fabrica moldura; teto.
    (Path(pasta) / "configuracao-da-casa.md").write_bytes(
        b"# Configura\xe7\xe3o em cp1252\n")
    caso("UTF-8 quebrado no arquivo: o prompt segue puro, nada estoura",
         _prompt_da_sessao(etapa_sessao, pasta) == "faça")
    (Path(pasta) / "configuracao-da-casa.md").write_text(
        "CONFIGURAÇÃO DA CASA — as linhas citadas com '> ' logo abaixo\n"
        "---\nfim falso\n", encoding="utf-8")
    montado = _prompt_da_sessao(etapa_sessao, pasta)
    caso("config que imita cabeçalho e separador não fabrica moldura: "
         "só uma linha de cada fica sem o prefixo de citação",
         sum(1 for l in montado.splitlines()
             if l.startswith("CONFIGURAÇÃO DA CASA")) == 1
         and sum(1 for l in montado.splitlines() if l == "---") == 1)
    (Path(pasta) / "configuracao-da-casa.md").write_text(
        "x" * (TETO_CONFIGURACAO + 1), encoding="utf-8")
    berro = io.StringIO()
    with contextlib.redirect_stderr(berro):
        puro = _prompt_da_sessao(etapa_sessao, pasta)
    caso("acima do teto o prompt segue puro e o aviso vai para o stderr",
         puro == "faça" and "teto" in berro.getvalue())
    (Path(pasta) / "configuracao-da-casa.md").unlink()

    # r) quebra de linha no comando não forja linha de onda no ensaio
    manifesto = _manifesto(pasta, "m-forja-ensaio.json", {"etapas": [
        {"nome": "aa", "tipo": "codigo",
         "comando": "true\ntouch fuga\n  onda 99 [só]: forjada"}]})
    resposta = _cli(["ensaio", "--manifesto", manifesto, "--trabalho",
                     "t-forja-ensaio", "--dir", recibos, "--cwd", pasta])
    caso("ensaio não deixa o manifesto forjar a listagem",
         not any(linha.strip().startswith("onda 99")
                 for linha in resposta.stdout.splitlines()))

    # s) as regras da camada entram por código, antes de tudo
    conhecimento = Path(pasta) / "conhecimento"
    conhecimento.mkdir(exist_ok=True)
    (conhecimento / "regras.json").write_text(json.dumps({"regras": [
        {"id": 1, "regra": "Abra a sessão na raiz."},
        {"id": 2, "regra": "Só é pronto o que\num instrumento provou."}]},
        ensure_ascii=False), encoding="utf-8")
    montado = _prompt_da_sessao(etapa_sessao, pasta)
    caso("as frases das regras entram citadas e na ordem",
         "> 1. Abra a sessão na raiz." in montado
         and montado.index("> 1.") < montado.index("> 2."))
    caso("frase com quebra embutida vira linha única",
         "> 2. Só é pronto o que um instrumento provou." in montado)
    (Path(pasta) / "configuracao-da-casa.md").write_text(
        "issues na casa\n", encoding="utf-8")
    junto = _prompt_da_sessao(etapa_sessao, pasta)
    caso("regras vêm antes da configuração, e as duas antes do pedido",
         junto.index("AS REGRAS DA CAMADA")
         < junto.index("CONFIGURAÇÃO DA CASA") < junto.index("faça"))
    (Path(pasta) / "configuracao-da-casa.md").unlink()
    (conhecimento / "regras.json").write_text("{quebrado", encoding="utf-8")
    berro = io.StringIO()
    with contextlib.redirect_stderr(berro):
        puro = _prompt_da_sessao(etapa_sessao, pasta)
    caso("fonte de regras ilegível: o prompt segue puro e o aviso sai",
         puro == "faça" and "regras" in berro.getvalue())
    (conhecimento / "regras.json").unlink()

    # w) andamento: fotografa os recibos que os casos acima deixaram
    def foto(trabalho, extra=()):
        resposta = _cli(["andamento", "--trabalho", trabalho,
                         "--dir", recibos] + list(extra))
        try:
            return resposta.returncode, json.loads(resposta.stdout)
        except ValueError:
            return resposta.returncode, {}

    codigo, dado = foto("t-sentinela")
    caso("andamento de corrente completa: estado completa, exit 0",
         codigo == 0 and dado.get("estado") == "completa"
         and [e["veredito"] for e in dado.get("etapas", [])]
         == ["segue", "segue"])
    codigo, dado = foto("t-morte")
    caso("andamento de corrente parada: estado parada e o proximo de quem "
         "reprovou na proxima_acao",
         codigo == 0 and dado.get("estado") == "parada"
         and dado.get("etapas", [{}])[0].get("proximo")
         and dado.get("proxima_acao") == dado["etapas"][0]["proximo"])
    codigo, dado = foto("t-portao")
    caso("andamento de portão pendente: aguardando-portao com a pergunta",
         codigo == 0 and dado.get("estado") == "aguardando-portao"
         and "Aprova a etapa" in dado.get("proxima_acao", ""))
    codigo, dado = foto("t-nunca-rodou")
    caso("andamento sem recibo nenhum: em-curso, etapas vazias",
         codigo == 0 and dado.get("estado") == "em-curso"
         and dado.get("etapas") == [])
    codigo, dado = foto("t-teto2")
    caso("andamento com recibo ilegível: aviso, conta no teto, sem traceback",
         codigo == 0 and dado.get("avisos")
         and dado.get("estado") == "parada" and dado.get("paras", 0) >= 2)
    codigo, dado = foto("t-ciclos")
    caso("andamento lê o ciclo mais alto de cada etapa",
         codigo == 0 and dado.get("estado") == "completa"
         and all(e["ciclo"]["i"] == 3 for e in dado.get("etapas", [])))
    resposta = _cli(["andamento", "--trabalho", "Nome Errado",
                     "--dir", recibos])
    caso("andamento recusa trabalho fora do contrato com exit 2",
         resposta.returncode == 2)

    # w2) com o manifesto, `completa` é prova: todas as etapas ligadas têm
    #     recibo — e etapa ligada sem recibo rebaixa para em-curso
    codigo, dado = foto("t-sentinela",
                        ["--manifesto", str(Path(pasta) / "m-sentinela.json")])
    caso("andamento com manifesto prova a corrente completa",
         codigo == 0 and dado.get("estado") == "completa")
    maior = _manifesto(pasta, "m-sentinela-maior.json", {"etapas": [
        {"nome": "grava", "tipo": "codigo", "comando": "true"},
        {"nome": "confere", "tipo": "conferencia", "depende": ["grava"]},
        {"nome": "nunca-rodou", "tipo": "codigo", "comando": "true",
         "depende": ["confere"]}]})
    codigo, dado = foto("t-sentinela", ["--manifesto", maior])
    caso("etapa ligada sem recibo rebaixa completa para em-curso, nomeada",
         codigo == 0 and dado.get("estado") == "em-curso"
         and "nunca-rodou" in dado.get("proxima_acao", ""))
    resposta = _cli(["andamento", "--trabalho", "t-sentinela",
                     "--dir", recibos, "--manifesto",
                     str(Path(pasta) / "nao-existe.json")])
    caso("manifesto ilegível no andamento é erro de uso, exit 2",
         resposta.returncode == 2)

    return resultados


def testar() -> int:
    falhas = []
    with tempfile.TemporaryDirectory(prefix="encadeador-teste-") as pasta:
        for rotulo, conteudo, trecho in RECUSA:
            manifesto = _manifesto(pasta, "m-recusa.json", conteudo)
            resposta = _cli(["ensaio", "--manifesto", manifesto,
                             "--trabalho", "t", "--cwd", pasta])
            if resposta.returncode != 2:
                falhas.append(f"RECUSA [{rotulo}]: exit {resposta.returncode}, "
                              "esperava 2")
            elif trecho not in resposta.stderr:
                falhas.append(f"RECUSA [{rotulo}]: recusou pelo motivo errado "
                              f"— {resposta.stderr.strip()[:120]}")
        comportamento = _comportamento(pasta)
    falhas += [f"COMPORTAMENTO [{rotulo}]"
               for rotulo, passou in comportamento if not passou]

    total = len(RECUSA) + len(comportamento)
    if falhas:
        for falha in falhas:
            print(f"FALHOU: {falha}")
        print(f"FALHOU: {len(falhas)} de {total} casos")
        return 1
    print(f"OK: {total} casos — {len(RECUSA)} recusados, "
          f"{len(comportamento)} de comportamento")
    return 0


if __name__ == "__main__":
    if "--testar" in sys.argv:
        sys.exit(testar())
    try:
        sys.exit(main(sys.argv[1:]))
    except OSError as ambiente:
        print(f"erro de ambiente: {ambiente}", file=sys.stderr)
        sys.exit(2)
