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

MOTIVO_DESLIGADA = "desligada"
MOTIVO_MORTA = "morta"
MOTIVO_RECIBO_INVALIDO = "recibo-invalido"
MOTIVO_TETO_ESGOTADO = "teto-esgotado"
MOTIVOS = (MOTIVO_DESLIGADA, MOTIVO_MORTA, MOTIVO_RECIBO_INVALIDO,
           MOTIVO_TETO_ESGOTADO)

VEREDITO_SEGUE = "segue"
VEREDITO_PARA = "para"
ORIGEM_ENCADEADOR = "encadeador"

SUPORTADAS = {"type", "required", "properties", "additionalProperties", "enum",
              "const", "pattern", "minimum", "minLength", "maxLength", "items",
              "allOf", "if", "then", "else", "not"}
ANOTACOES = {"$schema", "$id", "title", "$comment", "description"}
TIPOS = {"object": dict, "array": list, "string": str,
         "integer": int, "boolean": bool}

CAMPOS_DO_CODIGO = ("etapa", "trabalho", "quando", "ciclo")
CAMPOS_CONDICIONAIS = ("proximo", "pergunta", "motivo", "origem", "provado")
CAMPOS_RESERVADOS_AO_SINTETICO = ("origem", "motivo")

ORDEM_MINIMA = 1
ORDEM_MAXIMA = 99
QUANTOS_ERROS_NO_DETALHE = 5
PREFIXO_TEMPORARIO = ".evidencia-"
SUFIXO_TEMPORARIO = ".tmp"

ROTULO_DA_EVIDENCIA = "evidência"
ROTULO_ARG_ETAPA = "argumento --etapa"
ROTULO_ARG_TRABALHO = "argumento --trabalho"
ROTULO_ARG_TETO = "argumento --teto"

ERRO_PALAVRA_DESCONHECIDA = ("{}: o validador não conhece {} — atualize "
                             "evidencia.py junto com o contrato")
ERRO_TIPO = "{}: deveria ser {}"
ERRO_ENUM = "{}: {!r} não está em {}"
ERRO_CONST = "{}: deveria ser {!r}"
ERRO_PATTERN = "{}: {!r} não casa com {}"
ERRO_MIN_LENGTH = "{}: precisa de ao menos {} caractere"
ERRO_MAX_LENGTH = "{}: passa de {} caracteres"
ERRO_MINIMO = "{}: {} é menor que o mínimo {}"
ERRO_CAMPO_OBRIGATORIO = "{}: falta o campo obrigatório {!r}"
ERRO_CAMPO_FORA_DO_CONTRATO = "{}: campo fora do contrato: {}"
ERRO_CAMPO_PROIBIDO = "{}: campo proibido neste contexto: {}"
ERRO_ESQUEMA_PROIBIDO = "{}: casa com um esquema proibido"
ERRO_CALENDARIO = ("evidencia.quando: {!r} não existe no calendário real "
                   "(regra escrita no contrato: fromisoformat além do "
                   "padrão)")

DETALHE_AUSENTE = "sem detalhe registrado"
FALTA_DESLIGADA = ("etapa desligada no roteiro — nada executou, nada foi "
                   "colhido (skip simétrico)")
FALTA_MORTA = "a etapa morreu sem deixar evidência: {}"
PROXIMO_MORTA = ("A etapa {} terminou sem evidência ({}). Leia o log da "
                 "etapa, corrija a causa e reexecute o trabalho {} a partir "
                 "dela.")
FALTA_RECIBO_INVALIDO = "a evidência devolvida não segue o contrato: {}"
PROXIMO_RECIBO_INVALIDO = ("A etapa {} devolveu evidência fora do contrato "
                           "({}). Corrija a etapa para devolver o "
                           "structured_output no contrato recibo.schema.json "
                           "e reexecute o trabalho {} a partir dela.")
FALTA_TETO_ESGOTADO = "o teto de {} ciclos esgotou"
PROXIMO_TETO_ESGOTADO = ("O teto de {} ciclos esgotou no trabalho {}. Este "
                         "para é do dono: releia as evidências para "
                         "anteriores e decida se o trabalho continua, muda de "
                         "rumo ou morre.")

ERRO_MOTIVO_DESCONHECIDO = "motivo desconhecido: {!r} (vale: {})"
ERRO_DEFEITO_NO_SINTETICO = ("defeito na evidência sintética — corrija "
                             "evidencia.py: {}")
ERRO_ENTRADA_VAZIA = "entrada vazia — a etapa não devolveu evidência nenhuma"
ERRO_NAO_E_OBJETO = "a entrada não é um objeto JSON de evidência"
ERRO_JSON_QUEBRADO = "JSON quebrado: {}"

ERRO_CONTRATO_ILEGIVEL = "não consegui ler o contrato em {}: {}"
ERRO_LEITURA = "não consegui ler {}: {}"
ERRO_STDOUT = "o stdout falhou: {}"
ERRO_STDOUT_APOS_VALIDA = "evidência válida, mas o stdout falhou: {}"
ERRO_STDOUT_APOS_ESCRITA = "evidência escrita em {}, mas o stdout falhou: {}"
ERRO_DE_USO = "erro de uso: {}"
PROBLEMA_ORDEM = ("argumento --ordem: {} fora de 1..99 (vira o prefixo de "
                  "dois dígitos do arquivo)")
PROBLEMA_DIR = ("argumento --dir: vazio ou com quebra de linha — o caminho "
                "impresso no stdout é lido linha a linha")
ERRO_AMBIENTE_NA_ENTRADA = ("erro de ambiente ao ler --entrada {}: {} — nada "
                            "escrito")
ERRO_COLISAO = ("colisão de evidência — o arquivo já existe, e sobrescrever "
                "seria perder evidência em silêncio (a regra é um escritor "
                "só): {}")
ERRO_AMBIENTE_NADA_ESCRITO = "erro de ambiente — nada escrito: {}"
ERRO_DE_AMBIENTE = "erro de ambiente: {}"
OK_EVIDENCIA_VALIDA = "evidência válida"

AJUDA_VALIDAR = "valida uma evidência contra o contrato"
AJUDA_ARQUIVO = "caminho do JSON, ou - para stdin"
AJUDA_DIR = "diretório-base das evidências"
AJUDA_MATERIALIZAR = "escreve a evidência a partir do stdout da sessão"
AJUDA_ENTRADA = "arquivo com o stdout da sessão; - = stdin"
AJUDA_SINTETICO = "escreve a evidência de etapa desligada/morta/teto"
AJUDA_ESQUEMA_SESSAO = "o contrato enxuto da sessão, para --json-schema"

DETALHE_EXIT = "exit {}"
TESTE_ACEITA_RECUSOU = "ACEITA [{}]: recusou — {}"
TESTE_RECUSA_ACEITOU = "RECUSA [{}]: aceitou o que devia recusar"
TESTE_RECUSA_MOTIVO_ERRADO = "RECUSA [{}]: recusou pelo motivo errado — {}"
TESTE_COMPORTAMENTO = "COMPORTAMENTO [{}]"
TESTE_FALHA = "FALHOU: {}"
TESTE_RESUMO_FALHA = "FALHOU: {} de {} casos"
TESTE_RESUMO_OK = ("OK: {} casos — {} aceitos, {} recusados, {} de "
                   "comportamento")


def _casa_padrao(padrao: str, dado: str) -> bool:
    if padrao.endswith("$") and not padrao.endswith(r"\$"):
        padrao = padrao[:-1] + r"\Z"
    return re.search(padrao, dado) is not None


def _tipo_certo(tipo: str, dado) -> bool:
    if tipo == "integer":
        if isinstance(dado, bool):
            return False
        if isinstance(dado, float):
            return dado.is_integer()
    return isinstance(dado, TIPOS[tipo])


def _erros_de_valor(esquema: dict, dado, caminho: str) -> list:
    erros = []
    if "enum" in esquema and dado not in esquema["enum"]:
        erros.append(ERRO_ENUM.format(caminho, dado, esquema["enum"]))
    if "const" in esquema and dado != esquema["const"]:
        erros.append(ERRO_CONST.format(caminho, esquema["const"]))
    if "pattern" in esquema and isinstance(dado, str) \
            and not _casa_padrao(esquema["pattern"], dado):
        erros.append(ERRO_PATTERN.format(caminho, dado, esquema["pattern"]))
    if "minLength" in esquema and isinstance(dado, str) \
            and len(dado) < esquema["minLength"]:
        erros.append(ERRO_MIN_LENGTH.format(caminho, esquema["minLength"]))
    if "maxLength" in esquema and isinstance(dado, str) \
            and len(dado) > esquema["maxLength"]:
        erros.append(ERRO_MAX_LENGTH.format(caminho, esquema["maxLength"]))
    if "minimum" in esquema and isinstance(dado, (int, float)) \
            and not isinstance(dado, bool) and dado < esquema["minimum"]:
        erros.append(ERRO_MINIMO.format(caminho, dado, esquema["minimum"]))
    return erros


def _erros_de_objeto(esquema: dict, dado, caminho: str) -> list:
    if not isinstance(dado, dict):
        return []
    erros = []
    for exigido in esquema.get("required", []):
        if exigido not in dado:
            erros.append(ERRO_CAMPO_OBRIGATORIO.format(caminho, exigido))
    propriedades = esquema.get("properties", {})
    if esquema.get("additionalProperties") is False:
        sobras = sorted(set(dado) - set(propriedades))
        if sobras:
            erros.append(ERRO_CAMPO_FORA_DO_CONTRATO.format(caminho, sobras))
    for nome, sub in propriedades.items():
        if nome in dado:
            erros += _erros(sub, dado[nome], f"{caminho}.{nome}")
    return erros


def _erros_de_lista(esquema: dict, dado, caminho: str) -> list:
    if not isinstance(dado, list) or "items" not in esquema:
        return []
    erros = []
    for n, item in enumerate(dado):
        erros += _erros(esquema["items"], item, f"{caminho}[{n}]")
    return erros


def _erros_do_proibido(proibido: dict, dado, caminho: str) -> list:
    if _erros(proibido, dado, caminho):
        return []
    if set(proibido) == {"required"}:
        return [ERRO_CAMPO_PROIBIDO.format(caminho, proibido["required"])]
    return [ERRO_ESQUEMA_PROIBIDO.format(caminho)]


def _erros_de_combinacao(esquema: dict, dado, caminho: str) -> list:
    erros = []
    for sub in esquema.get("allOf", []):
        erros += _erros(sub, dado, caminho)
    if "if" in esquema:
        casa = not _erros(esquema["if"], dado, caminho)
        ramo = esquema.get("then") if casa else esquema.get("else")
        if ramo:
            erros += _erros(ramo, dado, caminho)
    if "not" in esquema:
        erros += _erros_do_proibido(esquema["not"], dado, caminho)
    return erros


def _erros(esquema: dict, dado, caminho: str) -> list:
    desconhecidas = set(esquema) - SUPORTADAS - ANOTACOES
    if desconhecidas:
        return [ERRO_PALAVRA_DESCONHECIDA.format(caminho,
                                                 sorted(desconhecidas))]
    tipo = esquema.get("type")
    if tipo and not _tipo_certo(tipo, dado):
        return [ERRO_TIPO.format(caminho, tipo)]
    return (_erros_de_valor(esquema, dado, caminho)
            + _erros_de_objeto(esquema, dado, caminho)
            + _erros_de_lista(esquema, dado, caminho)
            + _erros_de_combinacao(esquema, dado, caminho))


def carregar_esquema(caminho: Path = ESQUEMA_PADRAO) -> dict:
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        print(ERRO_CONTRATO_ILEGIVEL.format(caminho, erro), file=sys.stderr)
        sys.exit(2)


def _sem_comentario(no):
    if isinstance(no, dict):
        return {chave: _sem_comentario(valor) for chave, valor in no.items()
                if chave != "$comment"}
    if isinstance(no, list):
        return [_sem_comentario(item) for item in no]
    return no


def projetar_para_sessao(esquema: dict) -> dict:
    guia = _sem_comentario({chave: valor for chave, valor in esquema.items()
                            if chave != "allOf"})
    guia["required"] = [campo for campo in guia["required"]
                        if campo not in CAMPOS_DO_CODIGO]
    for campo in CAMPOS_CONDICIONAIS:
        regra = esquema["properties"].get(campo, {}).get("$comment")
        if regra:
            guia["properties"][campo]["description"] = regra
    return guia


def _data_existe_no_calendario(quando: str) -> bool:
    try:
        datetime.fromisoformat(quando)
    except ValueError:
        return False
    return True


def validar_evidencia(dado, esquema: dict) -> list:
    erros = _erros(esquema, dado, ROTULO_DA_EVIDENCIA)
    if not erros and not _data_existe_no_calendario(dado["quando"]):
        erros.append(ERRO_CALENDARIO.format(dado["quando"]))
    return erros


def agora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def caminho_da_evidencia(dir_base: str, trabalho: str, ordem: int, etapa: str):
    pasta = Path(dir_base) / trabalho
    padrao = re.compile(rf"{ordem:02d}-{re.escape(etapa)}-c([0-9]+)\.json\Z")
    existentes = [int(casado.group(1)) for arquivo in pasta.glob("*.json")
                  if (casado := padrao.fullmatch(arquivo.name))]
    i = 1 + max(existentes, default=0)
    return pasta / f"{ordem:02d}-{etapa}-c{i}.json", i


def escrever_atomico(caminho: Path, evidencia: dict) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(evidencia, ensure_ascii=False, indent=2) + "\n"
    descritor, tmp = tempfile.mkstemp(dir=caminho.parent,
                                      prefix=PREFIXO_TEMPORARIO,
                                      suffix=SUFIXO_TEMPORARIO)
    try:
        with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
            arquivo.write(texto)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.link(tmp, caminho)
        os.unlink(tmp)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return caminho


def _corpo_do_motivo(motivo, etapa, trabalho, teto, detalhe) -> dict:
    dito = detalhe or DETALHE_AUSENTE
    if motivo == MOTIVO_DESLIGADA:
        return {"faltas": [FALTA_DESLIGADA]}
    if motivo == MOTIVO_MORTA:
        return {"faltas": [FALTA_MORTA.format(dito)],
                "proximo": PROXIMO_MORTA.format(etapa, dito, trabalho)}
    if motivo == MOTIVO_RECIBO_INVALIDO:
        return {"faltas": [FALTA_RECIBO_INVALIDO.format(dito)],
                "proximo": PROXIMO_RECIBO_INVALIDO.format(etapa, dito,
                                                          trabalho)}
    return {"faltas": [FALTA_TETO_ESGOTADO.format(teto)],
            "proximo": PROXIMO_TETO_ESGOTADO.format(teto, trabalho)}


def sintetizar(dir_base, trabalho, etapa, ordem, teto, motivo, detalhe,
               esquema):
    if motivo not in MOTIVOS:
        sys.exit(ERRO_MOTIVO_DESCONHECIDO.format(motivo, ", ".join(MOTIVOS)))
    caminho, i = caminho_da_evidencia(dir_base, trabalho, ordem, etapa)
    evidencia = {
        "etapa": etapa,
        "trabalho": trabalho,
        "quando": agora(),
        "veredito": (VEREDITO_SEGUE if motivo == MOTIVO_DESLIGADA
                     else VEREDITO_PARA),
        "provado": [],
        "suposto": [],
        "faltas": [],
        "origem": ORIGEM_ENCADEADOR,
        "motivo": motivo,
        "ciclo": {"i": i, "teto": teto},
    }
    evidencia.update(_corpo_do_motivo(motivo, etapa, trabalho, teto, detalhe))

    erros = validar_evidencia(evidencia, esquema)
    if erros:
        print(ERRO_DEFEITO_NO_SINTETICO.format("; ".join(erros)),
              file=sys.stderr)
        sys.exit(2)
    return escrever_atomico(caminho, evidencia)


def _candidato_da_entrada(texto: str):
    texto = (texto or "").strip()
    if not texto:
        return None, ERRO_ENTRADA_VAZIA
    try:
        bruto = json.loads(texto)
    except (ValueError, RecursionError) as decodificacao:
        return None, ERRO_JSON_QUEBRADO.format(decodificacao)
    if isinstance(bruto, dict) and "structured_output" in bruto:
        bruto = bruto["structured_output"]
    if isinstance(bruto, dict):
        return bruto, ""
    return None, ERRO_NAO_E_OBJETO


def materializar(dir_base, trabalho, etapa, ordem, teto, texto, esquema):
    candidato, erro = _candidato_da_entrada(texto)
    if candidato is not None:
        for reservado in CAMPOS_RESERVADOS_AO_SINTETICO:
            candidato.pop(reservado, None)
        caminho, i = caminho_da_evidencia(dir_base, trabalho, ordem, etapa)
        candidato["etapa"] = etapa
        candidato["trabalho"] = trabalho
        candidato["quando"] = agora()
        candidato["ciclo"] = {"i": i, "teto": teto}
        erros = validar_evidencia(candidato, esquema)
        if not erros:
            return escrever_atomico(caminho, candidato), 0
        erro = "; ".join(erros[:QUANTOS_ERROS_NO_DETALHE])

    caminho = sintetizar(dir_base, trabalho, etapa, ordem, teto,
                         MOTIVO_RECIBO_INVALIDO, erro, esquema)
    return caminho, 3


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evidencia.py", add_help=True)
    sub = parser.add_subparsers(dest="comando", required=True)

    valida = sub.add_parser("validar", help=AJUDA_VALIDAR)
    valida.add_argument("arquivo", help=AJUDA_ARQUIVO)

    def comuns(p):
        p.add_argument("--dir", required=True, help=AJUDA_DIR)
        p.add_argument("--trabalho", required=True)
        p.add_argument("--etapa", required=True)
        p.add_argument("--ordem", required=True, type=int)
        p.add_argument("--teto", required=True, type=int)

    materializa = sub.add_parser("materializar", help=AJUDA_MATERIALIZAR)
    comuns(materializa)
    materializa.add_argument("--entrada", default="-", help=AJUDA_ENTRADA)

    sintetiza = sub.add_parser("sintetico", help=AJUDA_SINTETICO)
    comuns(sintetiza)
    sintetiza.add_argument("--motivo", required=True, choices=MOTIVOS)
    sintetiza.add_argument("--detalhe", default="")

    sub.add_parser("esquema-sessao", help=AJUDA_ESQUEMA_SESSAO)
    return parser


def _descartar_stdout():
    try:
        os.dup2(os.open(os.devnull, os.O_WRONLY), 1)
    except OSError:
        pass


def _dizer_caminho(caminho: Path, codigo: int) -> int:
    try:
        print(caminho)
        sys.stdout.flush()
    except OSError as saida:
        print(ERRO_STDOUT_APOS_ESCRITA.format(caminho, saida), file=sys.stderr)
        _descartar_stdout()
        return 2
    return codigo


def _imprimir_esquema_da_sessao(esquema: dict) -> int:
    guia = projetar_para_sessao(esquema)
    try:
        print(json.dumps(guia, ensure_ascii=False))
        sys.stdout.flush()
    except OSError as saida:
        print(ERRO_STDOUT.format(saida), file=sys.stderr)
        _descartar_stdout()
        return 2
    return 0


def _validar_arquivo(pedido: str, esquema: dict) -> int:
    if pedido == "-":
        texto = sys.stdin.read()
    else:
        try:
            texto = Path(pedido).read_text(encoding="utf-8")
        except OSError as erro:
            print(ERRO_LEITURA.format(pedido, erro), file=sys.stderr)
            return 2
    try:
        dado = json.loads(texto)
    except (ValueError, RecursionError) as erro:
        print(ERRO_JSON_QUEBRADO.format(erro), file=sys.stderr)
        return 2
    erros = validar_evidencia(dado, esquema)
    if erros:
        for linha in erros:
            print(linha, file=sys.stderr)
        return 2
    try:
        print(OK_EVIDENCIA_VALIDA)
        sys.stdout.flush()
    except OSError as saida:
        print(ERRO_STDOUT_APOS_VALIDA.format(saida), file=sys.stderr)
        _descartar_stdout()
        return 2
    return 0


def _problemas_dos_argumentos(args, esquema: dict) -> list:
    problemas = _erros(esquema["properties"]["etapa"], args.etapa,
                       ROTULO_ARG_ETAPA)
    problemas += _erros(esquema["properties"]["trabalho"], args.trabalho,
                        ROTULO_ARG_TRABALHO)
    problemas += _erros(esquema["properties"]["ciclo"]["properties"]["teto"],
                        args.teto, ROTULO_ARG_TETO)
    if not ORDEM_MINIMA <= args.ordem <= ORDEM_MAXIMA:
        problemas.append(PROBLEMA_ORDEM.format(args.ordem))
    if not args.dir or "\n" in args.dir or "\r" in args.dir:
        problemas.append(PROBLEMA_DIR)
    return problemas


def _texto_da_entrada(entrada: str):
    if entrada == "-":
        return sys.stdin.read()
    try:
        return Path(entrada).read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except OSError as ambiente:
        print(ERRO_AMBIENTE_NA_ENTRADA.format(entrada, ambiente),
              file=sys.stderr)
        return None


def _materializar_pela_linha_de_comando(args, esquema: dict) -> int:
    texto = _texto_da_entrada(args.entrada)
    if texto is None:
        return 2
    try:
        caminho, codigo = materializar(args.dir, args.trabalho, args.etapa,
                                       args.ordem, args.teto, texto, esquema)
    except FileExistsError as colisao:
        print(ERRO_COLISAO.format(colisao), file=sys.stderr)
        return 2
    except OSError as ambiente:
        print(ERRO_AMBIENTE_NADA_ESCRITO.format(ambiente), file=sys.stderr)
        return 2
    return _dizer_caminho(caminho, codigo)


def _sintetizar_pela_linha_de_comando(args, esquema: dict) -> int:
    try:
        caminho = sintetizar(args.dir, args.trabalho, args.etapa, args.ordem,
                             args.teto, args.motivo, args.detalhe, esquema)
    except FileExistsError as colisao:
        print(ERRO_COLISAO.format(colisao), file=sys.stderr)
        return 2
    except OSError as ambiente:
        print(ERRO_AMBIENTE_NADA_ESCRITO.format(ambiente), file=sys.stderr)
        return 2
    return _dizer_caminho(caminho, 0)


def main(argv) -> int:
    args = montar_parser().parse_args(argv)
    esquema = carregar_esquema()

    if args.comando == "esquema-sessao":
        return _imprimir_esquema_da_sessao(esquema)
    if args.comando == "validar":
        return _validar_arquivo(args.arquivo, esquema)

    problemas = _problemas_dos_argumentos(args, esquema)
    if problemas:
        for problema in problemas:
            print(ERRO_DE_USO.format(problema), file=sys.stderr)
        return 2

    if args.comando == "materializar":
        return _materializar_pela_linha_de_comando(args, esquema)
    return _sintetizar_pela_linha_de_comando(args, esquema)


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
    return {chave: valor for chave, valor in evidencia.items()
            if valor is not ...}


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
FANTOCHE_QUE_MORRE = "import sys; sys.exit(9)\n"
ETAPA_DESLIGADA = None


def _cli(argumentos, entrada=None):
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve())] + argumentos,
        input=entrada, capture_output=True, text=True, timeout=60)


def _rodar_fantoche(pasta, nome, script):
    arquivo = Path(pasta) / f"fantoche-{nome}.py"
    arquivo.write_text(script, encoding="utf-8")
    return subprocess.run([sys.executable, str(arquivo)],
                          capture_output=True, text=True, timeout=60)


def _encadear(pasta, trabalho, etapas):
    resultados = []
    for ordem, nome, script in etapas:
        base = ["--dir", str(pasta), "--trabalho", trabalho, "--etapa", nome,
                "--ordem", str(ordem), "--teto", "3"]
        if script is ETAPA_DESLIGADA:
            saida = _cli(["sintetico"] + base + ["--motivo", "desligada"])
        else:
            fantoche = _rodar_fantoche(pasta, nome, script)
            if fantoche.returncode != 0:
                saida = _cli(["sintetico"] + base +
                             ["--motivo", "morta", "--detalhe",
                              DETALHE_EXIT.format(fantoche.returncode)])
            else:
                saida = _cli(["materializar"] + base, entrada=fantoche.stdout)
        resultados.append(saida)
    return resultados


def _ler(pasta, trabalho, nome_arquivo):
    return json.loads((Path(pasta) / trabalho / nome_arquivo)
                      .read_text(encoding="utf-8"))


def _o_codigo_manda_nos_campos(pasta, caso):
    _cli(["materializar", "--dir", pasta, "--trabalho", "t-campos",
          "--etapa", "alfa", "--ordem", "1", "--teto", "3"],
         entrada=json.dumps({"structured_output": json.loads(EXEMPLO_DA_ISSUE)}))
    escrito = _ler(pasta, "t-campos", "01-alfa-c1.json")
    caso("etapa vem do argumento, não do modelo", escrito["etapa"] == "alfa")
    caso("trabalho vem do argumento", escrito["trabalho"] == "t-campos")
    caso("quando vem do relógio daqui", escrito["quando"] != "2026-08-16T16:02:47-03:00")
    caso("ciclo vem da contagem, não do JSON", escrito["ciclo"]["i"] == 1)
    caso("veredito do modelo é preservado", escrito["veredito"] == "para")

    _cli(["materializar", "--dir", pasta, "--trabalho", "t-campos",
          "--etapa", "alfa", "--ordem", "1", "--teto", "3"],
         entrada=json.dumps({"structured_output": json.loads(EXEMPLO_DA_ISSUE)}))
    caso("contagem de ciclo: segundo evidência é c2",
         (Path(pasta) / "t-campos" / "01-alfa-c2.json").exists())

    forjado = _base(origem="encadeador", motivo="desligada")
    resposta = _cli(["materializar", "--dir", pasta, "--trabalho", "t-forja",
                     "--etapa", "alfa", "--ordem", "1", "--teto", "3"],
                    entrada=json.dumps(forjado))
    escrito = _ler(pasta, "t-forja", "01-alfa-c1.json")
    caso("modelo não forja evidência sintética",
         resposta.returncode == 0 and "origem" not in escrito)


def _entrada_ruim_vira_para_sintetico(pasta, caso):
    resposta = _cli(["materializar", "--dir", pasta, "--trabalho", "t-quebra",
                     "--etapa", "alfa", "--ordem", "1", "--teto", "3"],
                    entrada="{ isto nao e json")
    escrito = _ler(pasta, "t-quebra", "01-alfa-c1.json")
    caso("JSON quebrado vira para sintético com exit 3",
         resposta.returncode == 3 and escrito["veredito"] == "para"
         and escrito["motivo"] == "recibo-invalido")

    resposta = _cli(["materializar", "--dir", pasta, "--trabalho", "t-vazio",
                     "--etapa", "alfa", "--ordem", "1", "--teto", "3"],
                    entrada="")
    escrito = _ler(pasta, "t-vazio", "01-alfa-c1.json")
    caso("evidência ausente vira para sintético",
         resposta.returncode == 3 and escrito["motivo"] == "recibo-invalido")

    resposta = _cli(["materializar", "--dir", pasta, "--trabalho", "t-contrato",
                     "--etapa", "alfa", "--ordem", "1", "--teto", "3"],
                    entrada=json.dumps(_base(veredito="quase")))
    escrito = _ler(pasta, "t-contrato", "01-alfa-c1.json")
    caso("evidência fora do contrato vira para sintético",
         resposta.returncode == 3 and escrito["motivo"] == "recibo-invalido"
         and "veredito" in escrito["faltas"][0])


def _a_escrita_nao_deixa_temporario(pasta, caso):
    caso("nenhum temporário sobra no diretório",
         not list(Path(pasta).rglob("*.tmp")))
    resposta = _cli(["validar", str(Path(pasta) / "t-quebra" / "01-alfa-c1.json")])
    caso("sintético passa no próprio validador", resposta.returncode == 0)


def _tres_fantoches_encadeadas(pasta, caso):
    _encadear(pasta, "t-skip", [(1, "alfa", FANTOCHE),
                                (2, "bravo", ETAPA_DESLIGADA),
                                (3, "charlie", FANTOCHE)])
    meio = _ler(pasta, "t-skip", "02-bravo-c1.json")
    fim = _ler(pasta, "t-skip", "03-charlie-c1.json")
    caso("desligar a do meio não impede a terceira",
         fim["veredito"] == "segue" and "origem" not in fim)
    caso("a evidência do meio registra o skip",
         meio["origem"] == "encadeador" and meio["motivo"] == "desligada"
         and meio["veredito"] == "segue")

    _encadear(pasta, "t-lixo", [(1, "alfa", FANTOCHE),
                                (2, "bravo", FANTOCHE_QUEBRADA),
                                (3, "charlie", FANTOCHE)])
    meio = _ler(pasta, "t-lixo", "02-bravo-c1.json")
    caso("fantoche que devolve lixo vira para sintético",
         meio["veredito"] == "para" and meio["motivo"] == "recibo-invalido")


def _o_guia_da_sessao_carrega_a_lei_que_julga(caso):
    resposta = _cli(["esquema-sessao"])
    guia = json.loads(resposta.stdout)
    caso("esquema-sessao tira o allOf e mantém o resto",
         "allOf" not in guia and "properties" in guia
         and "allOf" in carregar_esquema())

    lei = carregar_esquema()
    caso("esquema-sessao não manda $comment nem exige campo do código",
         '"$comment"' not in resposta.stdout
         and not set(CAMPOS_DO_CODIGO) & set(guia["required"])
         and all(campo in guia["properties"] for campo in CAMPOS_DO_CODIGO)
         and "$comment" in lei
         and set(CAMPOS_DO_CODIGO) <= set(lei["required"]))

    condicionais = ("proximo", "pergunta", "motivo", "origem")
    caso("o contrato da sessão diz QUANDO cada campo condicional vale",
         all(guia["properties"][campo].get("description")
             for campo in condicionais))
    caso("a regra do proximo chega na sessão, não só no allOf",
         "para" in guia["properties"]["proximo"].get("description", ""))

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


def _fantoche_morta_e_json_fundo(pasta, caso):
    _encadear(pasta, "t-morte", [(1, "alfa", FANTOCHE),
                                 (2, "bravo", FANTOCHE_QUE_MORRE),
                                 (3, "charlie", FANTOCHE)])
    meio = _ler(pasta, "t-morte", "02-bravo-c1.json")
    caso("fantoche morta vira para sintético com motivo morta",
         meio["veredito"] == "para" and meio["motivo"] == "morta"
         and "exit 9" in meio["proximo"])

    resposta = _cli(["materializar", "--dir", pasta, "--trabalho", "t-fundo",
                     "--etapa", "alfa", "--ordem", "1", "--teto", "3"],
                    entrada="[" * 100000)
    escrito = _ler(pasta, "t-fundo", "01-alfa-c1.json")
    caso("JSON fundo demais vira para sintético, nunca traceback",
         resposta.returncode == 3 and escrito["motivo"] == "recibo-invalido")


def _argumento_fora_do_contrato_e_erro_de_uso(pasta, caso):
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


def _a_contagem_de_ciclo_nao_sobrescreve(pasta, caso):
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

    _cli(["sintetico", "--dir", pasta, "--trabalho", "t-prefixo",
          "--etapa", "a-c1", "--ordem", "1", "--teto", "3",
          "--motivo", "desligada"])
    _cli(["sintetico", "--dir", pasta, "--trabalho", "t-prefixo",
          "--etapa", "a", "--ordem", "1", "--teto", "3",
          "--motivo", "desligada"])
    caso("contagem não cruza etapas de prefixo parecido",
         (Path(pasta) / "t-prefixo" / "01-a-c1.json").exists())


def _a_colisao_de_caminho_falha_alto(pasta, caso):
    alvo = Path(pasta) / "t-colisao" / "01-alfa-c1.json"
    escrever_atomico(alvo, json.loads(EXEMPLO_DA_ISSUE))
    try:
        escrever_atomico(alvo, json.loads(EXEMPLO_DA_ISSUE))
        caso("colisão de caminho falha alto, nunca sobrescreve", False)
    except FileExistsError:
        caso("colisão de caminho falha alto, nunca sobrescreve", True)
    caso("colisão não deixa temporário para trás",
         not list((Path(pasta) / "t-colisao").glob("*.tmp")))


def _a_entrada_separa_ambiente_de_etapa_sem_saida(pasta, caso):
    resposta = _cli(["materializar", "--dir", pasta, "--trabalho", "t-eisdir",
                     "--etapa", "alfa", "--ordem", "1", "--teto", "3",
                     "--entrada", pasta])
    caso("entrada ilegível é erro de ambiente, sem evidência de diagnóstico falso",
         resposta.returncode == 2 and not (Path(pasta) / "t-eisdir").exists())

    resposta = _cli(["materializar", "--dir", pasta, "--trabalho", "t-enoent",
                     "--etapa", "alfa", "--ordem", "1", "--teto", "3",
                     "--entrada", str(Path(pasta) / "nao-existe.json")])
    caso("entrada inexistente vira para sintético (etapa sem saída)",
         resposta.returncode == 3)


def _o_intruso_e_a_quebra_de_linha(pasta, caso):
    pasta_intruso = Path(pasta) / "t-intruso"
    pasta_intruso.mkdir()
    (pasta_intruso / "01-alfa-c１０.json").write_text("{}", encoding="utf-8")
    _cli(["sintetico", "--dir", pasta, "--trabalho", "t-intruso",
          "--etapa", "alfa", "--ordem", "1", "--teto", "3",
          "--motivo", "desligada"])
    caso("intruso com dígito não-ASCII não dirige a contagem",
         (pasta_intruso / "01-alfa-c1.json").exists())

    resposta = _cli(["sintetico", "--dir", f"{pasta}/qu\nebra",
                     "--trabalho", "t-dir", "--etapa", "alfa", "--ordem", "1",
                     "--teto", "3", "--motivo", "desligada"])
    caso("--dir com quebra de linha é erro de uso", resposta.returncode == 2)


def _o_stdout_quebrado_depois_da_escrita(pasta, caso):
    if not os.path.exists("/dev/full"):
        return
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


def _comportamento(pasta):
    resultados = []

    def caso(rotulo, condicao):
        resultados.append((rotulo, bool(condicao)))

    _o_codigo_manda_nos_campos(pasta, caso)
    _entrada_ruim_vira_para_sintetico(pasta, caso)
    _a_escrita_nao_deixa_temporario(pasta, caso)
    _tres_fantoches_encadeadas(pasta, caso)
    _o_guia_da_sessao_carrega_a_lei_que_julga(caso)
    _fantoche_morta_e_json_fundo(pasta, caso)
    _argumento_fora_do_contrato_e_erro_de_uso(pasta, caso)
    _a_contagem_de_ciclo_nao_sobrescreve(pasta, caso)
    _a_colisao_de_caminho_falha_alto(pasta, caso)
    _a_entrada_separa_ambiente_de_etapa_sem_saida(pasta, caso)
    _o_intruso_e_a_quebra_de_linha(pasta, caso)
    _o_stdout_quebrado_depois_da_escrita(pasta, caso)
    return resultados


def testar() -> int:
    esquema = carregar_esquema()
    falhas = []

    for rotulo, evidencia in ACEITA:
        erros = validar_evidencia(evidencia, esquema)
        if erros:
            falhas.append(TESTE_ACEITA_RECUSOU.format(rotulo,
                                                      "; ".join(erros)))

    for rotulo, evidencia, trecho in RECUSA:
        erros = validar_evidencia(evidencia, esquema)
        if not erros:
            falhas.append(TESTE_RECUSA_ACEITOU.format(rotulo))
        elif not any(trecho in erro for erro in erros):
            falhas.append(TESTE_RECUSA_MOTIVO_ERRADO.format(
                rotulo, "; ".join(erros)))

    with tempfile.TemporaryDirectory(prefix="evidencia-teste-") as pasta:
        comportamento = _comportamento(pasta)
    falhas += [TESTE_COMPORTAMENTO.format(rotulo)
               for rotulo, passou in comportamento if not passou]

    total = len(ACEITA) + len(RECUSA) + len(comportamento)
    if falhas:
        for falha in falhas:
            print(TESTE_FALHA.format(falha))
        print(TESTE_RESUMO_FALHA.format(len(falhas), total))
        return 1
    print(TESTE_RESUMO_OK.format(total, len(ACEITA), len(RECUSA),
                                 len(comportamento)))
    return 0


if __name__ == "__main__":
    if "--testar" in sys.argv:
        sys.exit(testar())
    try:
        sys.exit(main(sys.argv[1:]))
    except OSError as ambiente:
        print(ERRO_DE_AMBIENTE.format(ambiente), file=sys.stderr)
        sys.exit(2)
