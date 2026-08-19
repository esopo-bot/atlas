#!/usr/bin/env python3
"""evidência — escreve e valida a evidência que toda etapa do executor de
roteiros deixa.

O contrato é o recibo.schema.json ao lado deste script. A regra de fundação
(a emenda do degrau 1): **evidência é materializada só por código**. A etapa de
sessão devolve o conteúdo em structured_output; quem escreve o arquivo é o
encadeador, chamando este script. Os campos que identificam a evidência nunca
vêm do modelo:

- `etapa` e `trabalho` vêm dos argumentos (o roteiro);
- `quando` vem do relógio daqui;
- `ciclo.i` vem da contagem de arquivos no diretório, nunca do JSON;
- `origem`/`motivo` são reservados à evidência sintética — se o modelo os
  mandar, são descartados antes da validação.

O que este script FAZ: valida contra o contrato (com erro dizendo onde);
materializa evidência de etapa a partir do stdout da sessão; escreve atômico
(tmp + rename no mesmo diretório); sintetiza evidência de etapa desligada
(skip), morta, inválida ou de teto esgotado — inválida/ausente vira `para`.

O que ele NÃO FAZ: não roda etapa nenhuma (o encadeador é o degrau 3); não
re-executa comando de `provado` (a verificação é o degrau 2); não impõe o
teto de ciclos (é do encadeador, contando evidências `para`); não escreve
colheita; não toca rede nem API; e não aceita dois escritores — a regra do
desenho é UM escritor só (o encadeador): evidência da mesma etapa escrita em
paralelo colide e falha alto, nunca sobrescreve.

Uso:
    evidencia.py validar <arquivo.json | ->
    evidencia.py materializar --dir D --trabalho T --etapa E --ordem N --teto K [--entrada ARQ]
    evidencia.py sintetico   --dir D --trabalho T --etapa E --ordem N --teto K --motivo M [--detalhe TEXTO]
    evidencia.py esquema-sessao

`esquema-sessao` imprime o contrato sem o allOf de topo, para passar ao
`claude -p --json-schema`: medido em 16/08/2026, a API recusou o condicional
de topo (400 citando "oneOf, allOf..."). Nuance da doc vigente: `allOf` em si
é aceito com limitações — o que ela não lista é o `if/then/else`, que é
exatamente o que o nosso allOf de topo carrega; tirar o bloco segue sendo o
caminho. Junto com o allOf saem os `$comment` (arqueologia escrita para
humano) e, de `required`, os quatro campos que o código sobrescreve — eles
continuam em `properties`. O guia da sessão perde as condicionais; a LEI
continua inteira aqui — quem materializa valida contra o contrato completo,
e violação vira `para` sintético.

Saída: 0 = evidência válida/da etapa escrita; 3 = sintética escrita no lugar
(o chamador lê o veredito no arquivo); 2 = erro de uso, de ambiente ou
colisão de escritor — em regra nada foi escrito; a exceção é falha de
stdout DEPOIS da escrita, e aí o stderr diz o caminho da evidência que já
existe. Antes de re-executar por um exit 2, confira o diretório.

Rode os testes com:  python .agents/evidencia/evidencia.py --testar
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ESQUEMA_PADRAO = AQUI / "recibo.schema.json"

MOTIVOS = ("desligada", "morta", "recibo-invalido", "teto-esgotado")

# ---------------------------------------------------------------------------
# O validador. Cobre só o que o contrato usa — e recusa alto o que não
# conhece: palavra nova no esquema sem suporte aqui viraria validação que
# ignora em silêncio, o mesmo furo do painel de controle que morreu por um
# P maiúsculo.
# ---------------------------------------------------------------------------

SUPORTADAS = {"type", "required", "properties", "additionalProperties", "enum",
              "const", "pattern", "minimum", "minLength", "maxLength", "items",
              "allOf", "if", "then", "else", "not"}
ANOTACOES = {"$schema", "$id", "title", "$comment", "description"}

TIPOS = {"object": dict, "array": list, "string": str,
         "integer": int, "boolean": bool}


def _casa_padrao(padrao: str, dado: str) -> bool:
    """O pattern do JSON Schema tem semântica ECMA: `$` é fim de verdade.

    O `$` do Python casa antes de um `\\n` final — por ele, "cetico\\n"
    validaria e viraria arquivo com quebra de linha no nome (medido pelo
    refutador). A tradução para `\\Z` fecha o furo.
    """
    if padrao.endswith("$") and not padrao.endswith(r"\$"):
        padrao = padrao[:-1] + r"\Z"
    return re.search(padrao, dado) is not None


def _erros(esquema: dict, dado, caminho: str) -> list:
    desconhecidas = set(esquema) - SUPORTADAS - ANOTACOES
    if desconhecidas:
        return [f"{caminho}: o validador não conhece {sorted(desconhecidas)} "
                "— atualize evidencia.py junto com o contrato"]

    tipo = esquema.get("type")
    if tipo:
        certo = isinstance(dado, TIPOS[tipo])
        # bool é subclasse de int em Python; sem o corte, true passaria por inteiro.
        if tipo == "integer" and isinstance(dado, bool):
            certo = False
        # draft-07: inteiro é número de fração zero — 1.0 vale (medido no
        # jsonschema de referência pelo refutador).
        if tipo == "integer" and isinstance(dado, float) and dado.is_integer():
            certo = True
        if not certo:
            return [f"{caminho}: deveria ser {tipo}"]

    erros = []
    if "enum" in esquema and dado not in esquema["enum"]:
        erros.append(f"{caminho}: {dado!r} não está em {esquema['enum']}")
    if "const" in esquema and dado != esquema["const"]:
        erros.append(f"{caminho}: deveria ser {esquema['const']!r}")
    if "pattern" in esquema and isinstance(dado, str) \
            and not _casa_padrao(esquema["pattern"], dado):
        erros.append(f"{caminho}: {dado!r} não casa com {esquema['pattern']}")
    if "minLength" in esquema and isinstance(dado, str) \
            and len(dado) < esquema["minLength"]:
        erros.append(f"{caminho}: precisa de ao menos "
                     f"{esquema['minLength']} caractere")
    if "maxLength" in esquema and isinstance(dado, str) \
            and len(dado) > esquema["maxLength"]:
        erros.append(f"{caminho}: passa de {esquema['maxLength']} caracteres")
    if "minimum" in esquema and isinstance(dado, (int, float)) \
            and not isinstance(dado, bool) and dado < esquema["minimum"]:
        erros.append(f"{caminho}: {dado} é menor que o mínimo {esquema['minimum']}")

    if isinstance(dado, dict):
        for exigido in esquema.get("required", []):
            if exigido not in dado:
                erros.append(f"{caminho}: falta o campo obrigatório {exigido!r}")
        propriedades = esquema.get("properties", {})
        if esquema.get("additionalProperties") is False:
            sobras = sorted(set(dado) - set(propriedades))
            if sobras:
                erros.append(f"{caminho}: campo fora do contrato: {sobras}")
        for nome, sub in propriedades.items():
            if nome in dado:
                erros += _erros(sub, dado[nome], f"{caminho}.{nome}")

    if isinstance(dado, list) and "items" in esquema:
        for n, item in enumerate(dado):
            erros += _erros(esquema["items"], item, f"{caminho}[{n}]")

    for sub in esquema.get("allOf", []):
        erros += _erros(sub, dado, caminho)

    if "if" in esquema:
        casa = not _erros(esquema["if"], dado, caminho)
        ramo = esquema.get("then") if casa else esquema.get("else")
        if ramo:
            erros += _erros(ramo, dado, caminho)

    if "not" in esquema:
        proibido = esquema["not"]
        if not _erros(proibido, dado, caminho):
            if set(proibido) == {"required"}:
                erros.append(f"{caminho}: campo proibido neste contexto: "
                             f"{proibido['required']}")
            else:
                erros.append(f"{caminho}: casa com um esquema proibido")
    return erros


def carregar_esquema(caminho: Path = ESQUEMA_PADRAO) -> dict:
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        print(f"não consegui ler o contrato em {caminho}: {erro}",
              file=sys.stderr)
        sys.exit(2)


CAMPOS_DO_CODIGO = ("etapa", "trabalho", "quando", "ciclo")

# Campos que o allOf libera ou proíbe conforme o veredito e a origem. A
# projeção não leva o allOf, então a regra de cada um viaja como `description`
# — senão a sessão é julgada por lei que não recebeu.
CAMPOS_CONDICIONAIS = ("proximo", "pergunta", "motivo", "origem")
# O `provado` entra na mesma lista, e por um motivo medido: em 18/08/2026,
# 10 de 11 acusações de uma execução real foram prova mal ESCRITA — prosa no
# campo `comando`, saída redigida à mão, ausência declarada entre parênteses.
# A regra que julga tudo isso morava só no $comment, que a projeção descarta:
# a sessão era reprovada por norma que ninguém lhe mostrava. É o defeito 11
# de novo, noutro campo.
CAMPOS_CONDICIONAIS = CAMPOS_CONDICIONAIS + ("provado",)


def _sem_comentario(no):
    """O esquema sem nenhum $comment, em qualquer profundidade."""
    if isinstance(no, dict):
        return {chave: _sem_comentario(valor) for chave, valor in no.items()
                if chave != "$comment"}
    if isinstance(no, list):
        return [_sem_comentario(item) for item in no]
    return no


def projetar_para_sessao(esquema: dict) -> dict:
    """O contrato como a sessão o recebe — o mesmo contrato, mais enxuto.

    Sai o allOf de topo (a API recusa o if/then/else que ele carrega), sai a
    arqueologia dos $comment (escrita para humano, e este texto viaja em TODO
    prompt de etapa) e saem de `required` os quatro campos que o encadeador
    sobrescreve logo depois: pedir ao modelo o que vai ser descartado só
    gasta contexto e convida a inventar relógio e contagem. Os quatro
    continuam em `properties`, então mandá-los segue sendo válido.

    O que NÃO sai é a regra condicional. Tirar o allOf tira o enunciado de
    "proximo só existe no para" — e `proximo` continua visível em
    `properties`, com `additionalProperties: false`. A sessão via um campo
    legítimo, sem nada dizendo quando vale, e apanhava de uma regra que
    nunca lhe foi mostrada: medido em 18/08/2026, a etapa que fundiu
    `fluxos/` fez o trabalho inteiro e foi reprovada por anexar um `proximo`
    prestativo a um `veredito: segue`. Enquanto os $comment viajavam, a
    regra chegava em prosa por acaso; agora ela chega de propósito, como
    `description` — que é campo de contrato, não arqueologia, e a API aceita.

    A LEI é o recibo.schema.json e continua inteira: quem materializa valida
    contra o contrato completo, e violação vira `para` sintético. O arquivo
    ao lado não muda um byte — a regra é promovida aqui, na projeção.
    """
    guia = _sem_comentario({chave: valor for chave, valor in esquema.items()
                            if chave != "allOf"})
    guia["required"] = [campo for campo in guia["required"]
                        if campo not in CAMPOS_DO_CODIGO]
    for campo in CAMPOS_CONDICIONAIS:
        regra = esquema["properties"].get(campo, {}).get("$comment")
        if regra:
            guia["properties"][campo]["description"] = regra
    return guia


def validar_evidencia(dado, esquema: dict) -> list:
    """Erros da evidência contra o contrato; lista vazia = válido."""
    erros = _erros(esquema, dado, "evidência")
    if not erros:
        # O padrão do esquema aceita 2026-13-99; só o relógio sabe que não existe.
        try:
            datetime.fromisoformat(dado["quando"])
        except ValueError:
            erros.append(f"evidencia.quando: {dado['quando']!r} não existe no "
                         "calendário real (regra escrita no contrato: "
                         "fromisoformat além do padrão)")
    return erros


# ---------------------------------------------------------------------------
# A materialização — o lado do encadeador.
# ---------------------------------------------------------------------------

def agora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def caminho_da_evidencia(dir_base: str, trabalho: str, ordem: int, etapa: str):
    """O arquivo da próxima evidência desta etapa, com o ciclo pela contagem.

    `c<i>` vem das evidências desta etapa já no diretório — nunca do campo do
    JSON, que a etapa poderia congelar em 1 para sempre. A conta é máximo+1
    com casamento exato, nunca len(): len fura com buraco na sequência
    (evidência removida faria a conta reusar um nome existente) e glob por
    prefixo confundiria a etapa "a" com a etapa "a-c1" (os dois medidos
    pelos refutadores).
    """
    pasta = Path(dir_base) / trabalho
    # [0-9] e não \d: o \d do Python casa dígito Unicode, e um arquivo
    # intruso "01-alfa-c１０.json" dirigiria a contagem (medido).
    padrao = re.compile(rf"{ordem:02d}-{re.escape(etapa)}-c([0-9]+)\.json\Z")
    existentes = [int(casado.group(1)) for arquivo in pasta.glob("*.json")
                  if (casado := padrao.fullmatch(arquivo.name))]
    i = 1 + max(existentes, default=0)
    return pasta / f"{ordem:02d}-{etapa}-c{i}.json", i


def escrever_atomico(caminho: Path, evidencia: dict) -> Path:
    """tmp + rename no mesmo diretório: quem lê em polling nunca vê metade."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(evidencia, ensure_ascii=False, indent=2) + "\n"
    descritor, tmp = tempfile.mkstemp(dir=caminho.parent,
                                      prefix=".evidencia-", suffix=".tmp")
    try:
        with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
            arquivo.write(texto)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        # link exclusivo, nunca replace: se o caminho já existe, sobrescrever
        # seria perda silenciosa de evidência (dois escritores, ou contagem
        # furada) — medido pelo refutador. Colisão falha ALTO.
        os.link(tmp, caminho)
        os.unlink(tmp)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return caminho


def sintetizar(dir_base, trabalho, etapa, ordem, teto, motivo, detalhe, esquema):
    """A evidência que o encadeador escreve quando a etapa não deixou o dela.

    `desligada` registra o skip e deixa o executor de roteiros seguir
    (skip simétrico: nada executou, nada se colhe). Os outros três motivos
    param — e o `proximo` diz o que houve e por onde recomeçar, nunca
    "tente de novo".
    """
    if motivo not in MOTIVOS:
        sys.exit(f"motivo desconhecido: {motivo!r} (vale: {', '.join(MOTIVOS)})")
    caminho, i = caminho_da_evidencia(dir_base, trabalho, ordem, etapa)
    evidencia = {
        "etapa": etapa,
        "trabalho": trabalho,
        "quando": agora(),
        "veredito": "segue" if motivo == "desligada" else "para",
        "provado": [],
        "suposto": [],
        "faltas": [],
        "origem": "encadeador",
        "motivo": motivo,
        "ciclo": {"i": i, "teto": teto},
    }
    if motivo == "desligada":
        evidencia["faltas"] = ["etapa desligada no roteiro — nada executou, "
                            "nada foi colhido (skip simétrico)"]
    elif motivo == "morta":
        evidencia["faltas"] = [f"a etapa morreu sem deixar evidência: "
                            f"{detalhe or 'sem detalhe registrado'}"]
        evidencia["proximo"] = (
            f"A etapa {etapa} terminou sem evidência "
            f"({detalhe or 'sem detalhe registrado'}). Leia o log da etapa, "
            f"corrija a causa e reexecute o trabalho {trabalho} a partir dela.")
    elif motivo == "recibo-invalido":
        evidencia["faltas"] = [f"a evidência devolvida não segue o contrato: "
                            f"{detalhe or 'sem detalhe registrado'}"]
        evidencia["proximo"] = (
            f"A etapa {etapa} devolveu evidência fora do contrato "
            f"({detalhe or 'sem detalhe registrado'}). Corrija a etapa para "
            f"devolver o structured_output no contrato recibo.schema.json e "
            f"reexecute o trabalho {trabalho} a partir dela.")
    else:  # teto-esgotado
        evidencia["faltas"] = [f"o teto de {teto} ciclos esgotou"]
        evidencia["proximo"] = (
            f"O teto de {teto} ciclos esgotou no trabalho {trabalho}. Este "
            f"para é do dono: releia as evidências para anteriores e decida se "
            f"o trabalho continua, muda de rumo ou morre.")

    erros = validar_evidencia(evidencia, esquema)
    if erros:
        # Com os argumentos validados na fronteira do main(), chegar aqui é
        # defeito DESTE script — nunca da etapa nem do chamador.
        print("defeito na evidência sintética — corrija evidencia.py: "
              + "; ".join(erros), file=sys.stderr)
        sys.exit(2)
    return escrever_atomico(caminho, evidencia)


def materializar(dir_base, trabalho, etapa, ordem, teto, texto, esquema):
    """Do stdout da sessão ao arquivo. Devolve (caminho, código de saída).

    Aceita o envelope do `claude -p --output-format json` (pega o
    structured_output) ou a evidência pura. Entrada vazia, JSON quebrado ou
    evidência fora do contrato viram `para` sintético com o erro registrado —
    a invariante "falha vira para" com dono. `morta` não nasce aqui: quem
    conhece exit code e timeout da sessão é o encadeador, que chama
    `sintetico --motivo morta`.
    """
    candidato, erro = None, ""
    texto = (texto or "").strip()
    if not texto:
        erro = "entrada vazia — a etapa não devolveu evidência nenhuma"
    else:
        try:
            bruto = json.loads(texto)
            if isinstance(bruto, dict) and "structured_output" in bruto:
                bruto = bruto["structured_output"]
            if isinstance(bruto, dict):
                candidato = bruto
            else:
                erro = "a entrada não é um objeto JSON de evidência"
        except (ValueError, RecursionError) as decodificacao:
            # RecursionError entra junto: JSON fundo demais derrubaria o
            # materializar sem evidência nenhuma — e o stdout é terreno da etapa.
            erro = f"JSON quebrado: {decodificacao}"

    if candidato is not None:
        for reservado in ("origem", "motivo"):
            candidato.pop(reservado, None)
        caminho, i = caminho_da_evidencia(dir_base, trabalho, ordem, etapa)
        candidato["etapa"] = etapa
        candidato["trabalho"] = trabalho
        candidato["quando"] = agora()
        candidato["ciclo"] = {"i": i, "teto": teto}
        erros = validar_evidencia(candidato, esquema)
        if not erros:
            return escrever_atomico(caminho, candidato), 0
        erro = "; ".join(erros[:5])

    caminho = sintetizar(dir_base, trabalho, etapa, ordem, teto,
                         "recibo-invalido", erro, esquema)
    return caminho, 3


# ---------------------------------------------------------------------------
# A linha de comando.
# ---------------------------------------------------------------------------

def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evidencia.py", add_help=True)
    sub = parser.add_subparsers(dest="comando", required=True)

    valida = sub.add_parser("validar", help="valida uma evidência contra o contrato")
    valida.add_argument("arquivo", help="caminho do JSON, ou - para stdin")

    def comuns(p):
        p.add_argument("--dir", required=True, help="diretório-base das evidências")
        p.add_argument("--trabalho", required=True)
        p.add_argument("--etapa", required=True)
        p.add_argument("--ordem", required=True, type=int)
        p.add_argument("--teto", required=True, type=int)

    materializa = sub.add_parser(
        "materializar", help="escreve a evidência a partir do stdout da sessão")
    comuns(materializa)
    materializa.add_argument("--entrada", default="-",
                             help="arquivo com o stdout da sessão; - = stdin")

    sintetiza = sub.add_parser(
        "sintetico", help="escreve a evidência de etapa desligada/morta/teto")
    comuns(sintetiza)
    sintetiza.add_argument("--motivo", required=True, choices=MOTIVOS)
    sintetiza.add_argument("--detalhe", default="")

    sub.add_parser("esquema-sessao",
                   help="o contrato enxuto da sessão, para --json-schema")
    return parser


def main(argv) -> int:
    args = montar_parser().parse_args(argv)
    esquema = carregar_esquema()

    if args.comando == "esquema-sessao":
        guia = projetar_para_sessao(esquema)
        try:
            print(json.dumps(guia, ensure_ascii=False))
            sys.stdout.flush()
        except OSError as saida:
            print(f"o stdout falhou: {saida}", file=sys.stderr)
            _descartar_stdout()
            return 2
        return 0

    if args.comando == "validar":
        if args.arquivo == "-":
            texto = sys.stdin.read()
        else:
            try:
                texto = Path(args.arquivo).read_text(encoding="utf-8")
            except OSError as erro:
                print(f"não consegui ler {args.arquivo}: {erro}", file=sys.stderr)
                return 2
        try:
            dado = json.loads(texto)
        except (ValueError, RecursionError) as erro:
            print(f"JSON quebrado: {erro}", file=sys.stderr)
            return 2
        erros = validar_evidencia(dado, esquema)
        if erros:
            for linha in erros:
                print(linha, file=sys.stderr)
            return 2
        try:
            print("evidência válida")
            sys.stdout.flush()
        except OSError as saida:
            print(f"evidência válida, mas o stdout falhou: {saida}",
                  file=sys.stderr)
            _descartar_stdout()
            return 2
        return 0

    # Erro se trata na fronteira: argumento fora do contrato é erro de USO,
    # com exit 2 e nada escrito — nunca um traceback culpando o script
    # (medido pelos refutadores). A régua dos argumentos é o próprio
    # contrato, para não nascer segunda lista que dessincroniza.
    if args.comando in ("materializar", "sintetico"):
        problemas = _erros(esquema["properties"]["etapa"], args.etapa,
                           "argumento --etapa")
        problemas += _erros(esquema["properties"]["trabalho"], args.trabalho,
                            "argumento --trabalho")
        problemas += _erros(esquema["properties"]["ciclo"]["properties"]["teto"],
                            args.teto, "argumento --teto")
        if not 1 <= args.ordem <= 99:
            problemas.append(f"argumento --ordem: {args.ordem} fora de 1..99 "
                             "(vira o prefixo de dois dígitos do arquivo)")
        if not args.dir or "\n" in args.dir or "\r" in args.dir:
            problemas.append("argumento --dir: vazio ou com quebra de linha — "
                             "o caminho impresso no stdout é lido linha a linha")
        if problemas:
            for problema in problemas:
                print(f"erro de uso: {problema}", file=sys.stderr)
            return 2

    if args.comando == "materializar":
        if args.entrada == "-":
            texto = sys.stdin.read()
        else:
            try:
                texto = Path(args.entrada).read_text(encoding="utf-8")
            except FileNotFoundError:
                # Entrada que NÃO EXISTE = a etapa não deixou saída: vira
                # sintético. Qualquer outro erro é do AMBIENTE (permissão,
                # diretório no lugar do arquivo...) e não pode virar
                # diagnóstico falso da etapa num evidência permanente (medido).
                texto = ""
            except OSError as ambiente:
                print(f"erro de ambiente ao ler --entrada {args.entrada}: "
                      f"{ambiente} — nada escrito", file=sys.stderr)
                return 2
        try:
            caminho, codigo = materializar(args.dir, args.trabalho, args.etapa,
                                           args.ordem, args.teto, texto, esquema)
        except FileExistsError as colisao:
            print("colisão de evidência — o arquivo já existe, e sobrescrever "
                  "seria perder evidência em silêncio (a regra é um escritor "
                  f"só): {colisao}", file=sys.stderr)
            return 2
        except OSError as ambiente:
            print(f"erro de ambiente — nada escrito: {ambiente}",
                  file=sys.stderr)
            return 2
        return _dizer_caminho(caminho, codigo)

    # sintetico
    try:
        caminho = sintetizar(args.dir, args.trabalho, args.etapa, args.ordem,
                             args.teto, args.motivo, args.detalhe, esquema)
    except FileExistsError as colisao:
        print("colisão de evidência — o arquivo já existe, e sobrescrever seria "
              f"perder evidência em silêncio (a regra é um escritor só): {colisao}",
              file=sys.stderr)
        return 2
    except OSError as ambiente:
        print(f"erro de ambiente — nada escrito: {ambiente}", file=sys.stderr)
        return 2
    return _dizer_caminho(caminho, 0)


def _descartar_stdout():
    """Aponta o fd 1 para /dev/null depois de uma falha de stdout.

    O buffer ainda guarda o que não coube; sem isto, o flush da saída do
    interpretador falharia DE NOVO e trocaria o exit 2 por 120 (medido).
    """
    try:
        os.dup2(os.open(os.devnull, os.O_WRONLY), 1)
    except OSError:
        pass


def _dizer_caminho(caminho: Path, codigo: int) -> int:
    """Imprime o caminho e só então devolve o código.

    Se o stdout falhar DEPOIS da escrita, a evidência já existe no disco — o
    exit 2 sem esta distinção mandaria o chamador re-executar e fabricar um
    ciclo a mais (medido). O flush explícito força o erro para dentro deste
    guarda.
    """
    try:
        print(caminho)
        sys.stdout.flush()
    except OSError as saida:
        print(f"evidência escrita em {caminho}, mas o stdout falhou: {saida}",
              file=sys.stderr)
        _descartar_stdout()
        return 2
    return codigo


# ---------------------------------------------------------------------------
# Os testes: as duas listas (o que o contrato aceita, o que ele recusa) e o
# comportamento do script — incluindo as três fantoches encadeadas.
# ---------------------------------------------------------------------------

# O exemplo do corpo da issue, tal e qual: é caso de teste do contrato.
EXEMPLO_DA_ISSUE = r'''
{
  "etapa": "cetico",
  "trabalho": "issue-42",
  "quando": "2026-08-16T16:02:47-03:00",
  "veredito": "para",
  "provado": [
    { "afirmacao": "o endpoint responde 200 no ambiente de teste",
      "comando": "curl -s -o /dev/null -w '%{http_code}' \"$URL_HOMOLOG/relatorio\"",
      "saida": "200" }
  ],
  "suposto": [],
  "faltas": [
    "a issue pedia paginacao e a resposta veio inteira: 3.412 itens num corpo so"
  ],
  "proximo": "Implemente a paginacao pedida na issue-42: parametros pagina e tamanho, teto de 100. Prove com dois comandos: a pagina 2 vindo diferente da 1, e uma pagina alem do fim vindo vazia com 200.",
  "ciclo": { "i": 1, "teto": 3 }
}
'''


def _base(**troca):
    evidencia = {
        "etapa": "fantoche", "trabalho": "issue-0",
        "quando": "2026-08-16T12:00:00-03:00", "veredito": "segue",
        "provado": [], "suposto": [], "faltas": [],
        "ciclo": {"i": 1, "teto": 3},
    }
    evidencia.update(troca)
    return {chave: valor for chave, valor in evidencia.items() if valor is not ...}


ACEITA = [
    ("o exemplo do corpo da issue", json.loads(EXEMPLO_DA_ISSUE)),
    ("segue mínimo, listas vazias", _base()),
    ("pergunta com o campo pergunta", _base(
        veredito="pergunta",
        pergunta="Recomendo A porque custa um comando; a alternativa B refaz "
                 "a etapa. Sigo com A?")),
    ("skip sintético da etapa desligada", _base(
        origem="encadeador", motivo="desligada",
        faltas=["etapa desligada no roteiro — nada executou"])),
    ("para sintético de etapa morta", _base(
        veredito="para", origem="encadeador", motivo="morta",
        faltas=["a etapa morreu sem deixar evidência: timeout"],
        proximo="A etapa fantoche terminou sem evidência (timeout). Leia o log, "
                "corrija a causa e reexecute a partir dela.")),
    ("provado com comando e saída", _base(provado=[
        {"afirmacao": "o teste passa", "comando": "pytest -q", "saida": "3 passed"}])),
    ("ciclo 1.0 — draft-07 aceita inteiro de fração zero",
     _base(ciclo={"i": 1.0, "teto": 3})),
]

RECUSA = [
    ("veredito fora dos 3 valores", _base(veredito="quase"), "não está em"),
    ("provado sem saida desce para suposto", _base(provado=[
        {"afirmacao": "funciona", "comando": "pytest -q"}]), "obrigatório 'saida'"),
    ("proximo em veredito segue", _base(proximo="faça X"), "proibido"),
    ("para sem proximo", {**_base(veredito="para")}, "obrigatório 'proximo'"),
    ("pergunta sem o campo pergunta", _base(veredito="pergunta"),
     "obrigatório 'pergunta'"),
    ("pergunta em veredito segue", _base(pergunta="sigo?"), "proibido"),
    ("etapa com maiúscula (a lição do painel de controle)",
     _base(etapa="Cetico"),
     "não casa"),
    ("etapa com quebra de linha no fim (o $ do ECMA não casa)",
     _base(etapa="cetico\n"), "não casa"),
    ("etapa de 65 caracteres (viraria nome de arquivo)",
     _base(etapa="a" * 65), "passa de 64"),
    ("trabalho com barra (viraria travessia de pasta)",
     _base(trabalho="a/b"), "não casa"),
    ("campo fora do contrato", _base(cor="verde"), "fora do contrato"),
    ("ciclo.i zero", _base(ciclo={"i": 0, "teto": 3}), "menor que o mínimo"),
    ("ciclo sem teto", _base(ciclo={"i": 1}), "obrigatório 'teto'"),
    ("quando fora do ISO", _base(quando="16/08/2026 16:02"), "não casa"),
    ("quando com mês 13", _base(quando="2026-13-01T00:00:00-03:00"),
     "calendário"),
    ("motivo sem origem encadeador", _base(motivo="morta"), "proibido"),
    ("morta que segue (motivo de parada com veredito segue)",
     _base(origem="encadeador", motivo="morta"), "deveria ser 'para'"),
    ("desligada que para",
     _base(veredito="para", proximo="x", origem="encadeador",
           motivo="desligada"), "deveria ser 'segue'"),
    ("origem encadeador sem motivo", _base(origem="encadeador"),
     "obrigatório 'motivo'"),
    ("provado como texto solto", _base(provado="tudo certo"),
     "deveria ser array"),
    ("suposto com item não-texto", _base(suposto=[{"x": 1}]),
     "deveria ser string"),
]

FANTOCHE = """\
import json, sys
print(json.dumps({"structured_output": {
    "etapa": "mentira", "trabalho": "mentira",
    "quando": "1999-01-01T00:00:00Z", "veredito": "segue",
    "provado": [{"afirmacao": "a fantoche rodou",
                 "comando": "python fantoche.py", "saida": "ok"}],
    "suposto": [], "faltas": [], "ciclo": {"i": 99, "teto": 99}}}))
"""

FANTOCHE_QUEBRADA = 'print("{ isto nao e json")\n'


def _cli(argumentos, entrada=None):
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve())] + argumentos,
        input=entrada, capture_output=True, text=True, timeout=60)


def _encadear(pasta, trabalho, etapas):
    """O encadeador mínimo da prova: roda fantoches e materializa evidências.

    `etapas` é uma lista de (ordem, nome, script | None); None = desligada.
    É de propósito um laço burro: o encadeador de verdade é o degrau 3.
    """
    resultados = []
    for ordem, nome, script in etapas:
        base = ["--dir", str(pasta), "--trabalho", trabalho, "--etapa", nome,
                "--ordem", str(ordem), "--teto", "3"]
        if script is None:
            saida = _cli(["sintetico"] + base + ["--motivo", "desligada"])
        else:
            arquivo = Path(pasta) / f"fantoche-{nome}.py"
            arquivo.write_text(script, encoding="utf-8")
            fantoche = subprocess.run([sys.executable, str(arquivo)],
                                      capture_output=True, text=True, timeout=60)
            if fantoche.returncode != 0:
                saida = _cli(["sintetico"] + base +
                             ["--motivo", "morta",
                              "--detalhe", f"exit {fantoche.returncode}"])
            else:
                saida = _cli(["materializar"] + base, entrada=fantoche.stdout)
        resultados.append(saida)
    return resultados


def _ler(pasta, trabalho, nome_arquivo):
    return json.loads((Path(pasta) / trabalho / nome_arquivo)
                      .read_text(encoding="utf-8"))


def _comportamento(pasta, esquema):
    """Casos de comportamento; devolve a lista de (rótulo, passou).

    O total sai do que RODOU — caso condicional (como o do /dev/full) que
    não roda não conta, em vez de virar passe fabricado.
    """
    resultados = []

    def caso(rotulo, condicao):
        resultados.append((rotulo, bool(condicao)))

    # a) o modelo não manda nos campos do código
    _cli(["materializar", "--dir", pasta, "--trabalho", "t-campos",
          "--etapa", "alfa", "--ordem", "1", "--teto", "3"],
         entrada=json.dumps({"structured_output": json.loads(EXEMPLO_DA_ISSUE)}))
    escrito = _ler(pasta, "t-campos", "01-alfa-c1.json")
    caso("etapa vem do argumento, não do modelo", escrito["etapa"] == "alfa")
    caso("trabalho vem do argumento", escrito["trabalho"] == "t-campos")
    caso("quando vem do relógio daqui", escrito["quando"] != "2026-08-16T16:02:47-03:00")
    caso("ciclo vem da contagem, não do JSON", escrito["ciclo"]["i"] == 1)
    caso("veredito do modelo é preservado", escrito["veredito"] == "para")

    # b) segunda materialização da mesma etapa vira c2
    _cli(["materializar", "--dir", pasta, "--trabalho", "t-campos",
          "--etapa", "alfa", "--ordem", "1", "--teto", "3"],
         entrada=json.dumps({"structured_output": json.loads(EXEMPLO_DA_ISSUE)}))
    caso("contagem de ciclo: segundo evidência é c2",
         (Path(pasta) / "t-campos" / "01-alfa-c2.json").exists())

    # c) origem/motivo vindos do modelo são descartados
    forjado = _base(origem="encadeador", motivo="desligada")
    resposta = _cli(["materializar", "--dir", pasta, "--trabalho", "t-forja",
                     "--etapa", "alfa", "--ordem", "1", "--teto", "3"],
                    entrada=json.dumps(forjado))
    escrito = _ler(pasta, "t-forja", "01-alfa-c1.json")
    caso("modelo não forja evidência sintética",
         resposta.returncode == 0 and "origem" not in escrito)

    # d) entrada quebrada vira para sintético, exit 3
    resposta = _cli(["materializar", "--dir", pasta, "--trabalho", "t-quebra",
                     "--etapa", "alfa", "--ordem", "1", "--teto", "3"],
                    entrada="{ isto nao e json")
    escrito = _ler(pasta, "t-quebra", "01-alfa-c1.json")
    caso("JSON quebrado vira para sintético com exit 3",
         resposta.returncode == 3 and escrito["veredito"] == "para"
         and escrito["motivo"] == "recibo-invalido")

    # e) entrada vazia (evidência ausente) vira para sintético
    resposta = _cli(["materializar", "--dir", pasta, "--trabalho", "t-vazio",
                     "--etapa", "alfa", "--ordem", "1", "--teto", "3"],
                    entrada="")
    escrito = _ler(pasta, "t-vazio", "01-alfa-c1.json")
    caso("evidência ausente vira para sintético",
         resposta.returncode == 3 and escrito["motivo"] == "recibo-invalido")

    # f) evidência fora do contrato vira para sintético com o erro registrado
    resposta = _cli(["materializar", "--dir", pasta, "--trabalho", "t-contrato",
                     "--etapa", "alfa", "--ordem", "1", "--teto", "3"],
                    entrada=json.dumps(_base(veredito="quase")))
    escrito = _ler(pasta, "t-contrato", "01-alfa-c1.json")
    caso("evidência fora do contrato vira para sintético",
         resposta.returncode == 3 and escrito["motivo"] == "recibo-invalido"
         and "veredito" in escrito["faltas"][0])

    # g) escrita atômica: nenhum temporário sobra
    caso("nenhum temporário sobra no diretório",
         not list(Path(pasta).rglob("*.tmp")))

    # h) o sintético que o script escreve passa no próprio validador
    resposta = _cli(["validar", str(Path(pasta) / "t-quebra" / "01-alfa-c1.json")])
    caso("sintético passa no próprio validador", resposta.returncode == 0)

    # i) TRÊS fantoches encadeadas, a do meio desligada: a terceira roda,
    #    a evidência do meio registra o skip
    _encadear(pasta, "t-skip", [(1, "alfa", FANTOCHE),
                                (2, "bravo", None),
                                (3, "charlie", FANTOCHE)])
    meio = _ler(pasta, "t-skip", "02-bravo-c1.json")
    fim = _ler(pasta, "t-skip", "03-charlie-c1.json")
    caso("desligar a do meio não impede a terceira",
         fim["veredito"] == "segue" and "origem" not in fim)
    caso("a evidência do meio registra o skip",
         meio["origem"] == "encadeador" and meio["motivo"] == "desligada"
         and meio["veredito"] == "segue")

    # j) fantoche do meio devolvendo lixo: a evidência dela é para sintético
    _encadear(pasta, "t-lixo", [(1, "alfa", FANTOCHE),
                                (2, "bravo", FANTOCHE_QUEBRADA),
                                (3, "charlie", FANTOCHE)])
    meio = _ler(pasta, "t-lixo", "02-bravo-c1.json")
    caso("fantoche que devolve lixo vira para sintético",
         meio["veredito"] == "para" and meio["motivo"] == "recibo-invalido")

    # k2) o guia da sessão sai sem allOf; a lei continua com ele
    resposta = _cli(["esquema-sessao"])
    guia = json.loads(resposta.stdout)
    caso("esquema-sessao tira o allOf e mantém o resto",
         "allOf" not in guia and "properties" in guia
         and "allOf" in carregar_esquema())

    # k3) o guia é enxuto: sem a arqueologia e sem exigir do modelo os quatro
    # campos que o código sobrescreve — eles ficam em properties, saem de
    # required. A LEI segue inteira: o contrato ao lado não muda um byte.
    do_codigo = ("etapa", "trabalho", "quando", "ciclo")
    lei = carregar_esquema()
    caso("esquema-sessao não manda $comment nem exige campo do código",
         '"$comment"' not in resposta.stdout
         and not set(do_codigo) & set(guia["required"])
         and all(campo in guia["properties"] for campo in do_codigo)
         and "$comment" in lei
         and set(do_codigo) <= set(lei["required"]))

    # k2b) o contrato que a sessão VÊ tem de enunciar a regra que a JULGA.
    # A projeção tira o allOf (a API recusa if/then/else), e é lá que mora
    # "proximo só existe no para". Enquanto os $comment viajavam, a regra
    # chegava em prosa. Sem eles, a sessão via `proximo` em properties e
    # nada dizendo quando vale — medido em 18/08/2026: a etapa que fundiu
    # `fluxos/` fez o trabalho inteiro, devolveu `veredito: segue` com um
    # `proximo` prestativo, e foi reprovada por uma regra que ninguém lhe
    # mostrou. Contrato que julga por regra escondida é armadilha.
    condicionais = ("proximo", "pergunta", "motivo", "origem")
    caso("o contrato da sessão diz QUANDO cada campo condicional vale",
         all(guia["properties"][campo].get("description")
             for campo in condicionais))
    caso("a regra do proximo chega na sessão, não só no allOf",
         "para" in guia["properties"]["proximo"].get("description", ""))

    # A mesma armadilha, noutro campo: como SE ESCREVE a prova era regra que
    # só a verificação conhecia. Medido em 18/08/2026, numa execução real:
    # 10 de 11 acusações foram prova mal escrita — prosa no campo `comando`,
    # saída redigida à mão, ausência declarada entre parênteses. A sessão não
    # tinha onde aprender nenhuma das três.
    regra_da_prova = guia["properties"]["provado"].get("description", "")
    caso("a sessão recebe COMO se escreve a prova, não só o que provar",
         bool(regra_da_prova))
    caso("e a regra chega inteira, as seis frases",
         all(m in regra_da_prova for m in ("(1)", "(2)", "(3)", "(4)",
                                           "(5)", "(6)")))
    caso("comando é comando: a regra diz isso com todas as letras",
         "nunca prosa" in regra_da_prova)
    caso("e o marcador de corte é ensinado onde a sessão o lê",
         "(...)" in regra_da_prova)

    # k) fantoche que morre (exit != 0): o encadeador registra morta
    _encadear(pasta, "t-morte", [(1, "alfa", FANTOCHE),
                                 (2, "bravo", "import sys; sys.exit(9)\n"),
                                 (3, "charlie", FANTOCHE)])
    meio = _ler(pasta, "t-morte", "02-bravo-c1.json")
    caso("fantoche morta vira para sintético com motivo morta",
         meio["veredito"] == "para" and meio["motivo"] == "morta"
         and "exit 9" in meio["proximo"])

    # l) JSON fundo demais não derruba o materializar: vira para sintético
    resposta = _cli(["materializar", "--dir", pasta, "--trabalho", "t-fundo",
                     "--etapa", "alfa", "--ordem", "1", "--teto", "3"],
                    entrada="[" * 100000)
    escrito = _ler(pasta, "t-fundo", "01-alfa-c1.json")
    caso("JSON fundo demais vira para sintético, nunca traceback",
         resposta.returncode == 3 and escrito["motivo"] == "recibo-invalido")

    # m) argumento fora do contrato é erro de USO: exit 2, nada escrito
    resposta = _cli(["materializar", "--dir", pasta, "--trabalho", "t-uso",
                     "--etapa", "Alfa", "--ordem", "1", "--teto", "3"],
                    entrada="{}")
    caso("etapa maiúscula no argumento: exit 2 e nada escrito",
         resposta.returncode == 2 and "erro de uso" in resposta.stderr
         and not (Path(pasta) / "t-uso").exists())
    resposta = _cli(["sintetico", "--dir", pasta, "--trabalho", "t-uso",
                     "--etapa", "alfa", "--ordem", "1", "--teto", "0",
                     "--motivo", "morta"])
    caso("teto zero no argumento: exit 2", resposta.returncode == 2)
    resposta = _cli(["materializar", "--dir", pasta, "--trabalho", "t-uso",
                     "--etapa", "alfa", "--ordem", "0", "--teto", "3"],
                    entrada="{}")
    caso("ordem fora de 1..99: exit 2", resposta.returncode == 2)

    # n) contagem por máximo: buraco na sequência não sobrescreve ninguém
    for _ in range(2):
        _cli(["sintetico", "--dir", pasta, "--trabalho", "t-buraco",
              "--etapa", "alfa", "--ordem", "1", "--teto", "3",
              "--motivo", "desligada"])
    (Path(pasta) / "t-buraco" / "01-alfa-c1.json").unlink()
    intacto = _ler(pasta, "t-buraco", "01-alfa-c2.json")
    _cli(["sintetico", "--dir", pasta, "--trabalho", "t-buraco",
          "--etapa", "alfa", "--ordem", "1", "--teto", "3",
          "--motivo", "desligada"])
    caso("buraco na sequência vira c3 e o c2 fica intacto",
         (Path(pasta) / "t-buraco" / "01-alfa-c3.json").exists()
         and _ler(pasta, "t-buraco", "01-alfa-c2.json") == intacto)

    # o) contagem não cruza etapas de prefixo parecido ("a" versus "a-c1")
    _cli(["sintetico", "--dir", pasta, "--trabalho", "t-prefixo",
          "--etapa", "a-c1", "--ordem", "1", "--teto", "3",
          "--motivo", "desligada"])
    _cli(["sintetico", "--dir", pasta, "--trabalho", "t-prefixo",
          "--etapa", "a", "--ordem", "1", "--teto", "3",
          "--motivo", "desligada"])
    caso("contagem não cruza etapas de prefixo parecido",
         (Path(pasta) / "t-prefixo" / "01-a-c1.json").exists())

    # p) sobrescrever evidência falha ALTO — um escritor só
    alvo = Path(pasta) / "t-colisao" / "01-alfa-c1.json"
    escrever_atomico(alvo, json.loads(EXEMPLO_DA_ISSUE))
    try:
        escrever_atomico(alvo, json.loads(EXEMPLO_DA_ISSUE))
        caso("colisão de caminho falha alto, nunca sobrescreve", False)
    except FileExistsError:
        caso("colisão de caminho falha alto, nunca sobrescreve", True)
    caso("colisão não deixa temporário para trás",
         not list((Path(pasta) / "t-colisao").glob("*.tmp")))

    # q) --entrada apontando para diretório é erro de AMBIENTE: exit 2 e
    #    NENHUM evidência com diagnóstico falso sobre a etapa
    resposta = _cli(["materializar", "--dir", pasta, "--trabalho", "t-eisdir",
                     "--etapa", "alfa", "--ordem", "1", "--teto", "3",
                     "--entrada", pasta])
    caso("entrada ilegível é erro de ambiente, sem evidência de diagnóstico falso",
         resposta.returncode == 2 and not (Path(pasta) / "t-eisdir").exists())

    # r) --entrada que não existe segue sendo etapa-sem-saída: sintético
    resposta = _cli(["materializar", "--dir", pasta, "--trabalho", "t-enoent",
                     "--etapa", "alfa", "--ordem", "1", "--teto", "3",
                     "--entrada", str(Path(pasta) / "nao-existe.json")])
    caso("entrada inexistente vira para sintético (etapa sem saída)",
         resposta.returncode == 3)

    # s) intruso com dígito não-ASCII no nome não dirige a contagem
    pasta_intruso = Path(pasta) / "t-intruso"
    pasta_intruso.mkdir()
    (pasta_intruso / "01-alfa-c１０.json").write_text("{}", encoding="utf-8")
    _cli(["sintetico", "--dir", pasta, "--trabalho", "t-intruso",
          "--etapa", "alfa", "--ordem", "1", "--teto", "3",
          "--motivo", "desligada"])
    caso("intruso com dígito não-ASCII não dirige a contagem",
         (pasta_intruso / "01-alfa-c1.json").exists())

    # t) --dir com quebra de linha é erro de uso (stdout lido linha a linha)
    resposta = _cli(["sintetico", "--dir", f"{pasta}/qu\nebra",
                     "--trabalho", "t-dir", "--etapa", "alfa", "--ordem", "1",
                     "--teto", "3", "--motivo", "desligada"])
    caso("--dir com quebra de linha é erro de uso", resposta.returncode == 2)

    # u) stdout quebrado DEPOIS da escrita: exit 2 e o stderr diz o caminho
    if os.path.exists("/dev/full"):
        with open("/dev/full", "w") as ralo:
            resposta = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "sintetico",
                 "--dir", pasta, "--trabalho", "t-ralo", "--etapa", "alfa",
                 "--ordem", "1", "--teto", "3", "--motivo", "desligada"],
                stdout=ralo, stderr=subprocess.PIPE, text=True, timeout=60)
        caso("stdout quebrado pós-escrita: exit 2 e o stderr diz o caminho",
             resposta.returncode == 2
             and "evidência escrita em" in resposta.stderr
             and (Path(pasta) / "t-ralo" / "01-alfa-c1.json").exists())

    return resultados


def testar() -> int:
    esquema = carregar_esquema()
    falhas = []

    for rotulo, evidencia in ACEITA:
        erros = validar_evidencia(evidencia, esquema)
        if erros:
            falhas.append(f"ACEITA [{rotulo}]: recusou — {'; '.join(erros)}")

    for rotulo, evidencia, trecho in RECUSA:
        erros = validar_evidencia(evidencia, esquema)
        if not erros:
            falhas.append(f"RECUSA [{rotulo}]: aceitou o que devia recusar")
        elif not any(trecho in erro for erro in erros):
            falhas.append(f"RECUSA [{rotulo}]: recusou pelo motivo errado — "
                          f"{'; '.join(erros)}")

    with tempfile.TemporaryDirectory(prefix="evidencia-teste-") as pasta:
        comportamento = _comportamento(pasta, esquema)
    falhas += [f"COMPORTAMENTO [{rotulo}]"
               for rotulo, passou in comportamento if not passou]

    total = len(ACEITA) + len(RECUSA) + len(comportamento)
    if falhas:
        for falha in falhas:
            print(f"FALHOU: {falha}")
        print(f"FALHOU: {len(falhas)} de {total} casos")
        return 1
    print(f"OK: {total} casos — {len(ACEITA)} aceitos, {len(RECUSA)} "
          f"recusados, {len(comportamento)} de comportamento")
    return 0


if __name__ == "__main__":
    if "--testar" in sys.argv:
        sys.exit(testar())
    try:
        sys.exit(main(sys.argv[1:]))
    except OSError as ambiente:
        # Última rede: as escritas já têm guarda própria lá dentro, então
        # aqui não se afirma "nada escrito" — só o erro, honesto.
        print(f"erro de ambiente: {ambiente}", file=sys.stderr)
        sys.exit(2)
