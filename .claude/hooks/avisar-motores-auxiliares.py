import importlib.util
import json
import os
import sys
from pathlib import Path

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2
ARQUIVO_DO_CADASTRO = "nucleo/executor.json"
CHAVE_DOS_MOTORES = "motores"
INSTRUMENTO_DOS_MOTORES = ".agents/motores/motores.py"
NOME_DO_MODULO_CARREGADO = "motores_da_camada"
CHAVE_DA_FONTE_NO_INSTRUMENTO = "fonte_do_limite"

EVENTO_DE_INICIO_DE_SESSAO = "SessionStart"
SILENCIO = 0
BANDEIRA_DE_TESTE = "--testar"

VEREDITOS_QUE_SERVEM = ("passou", "atenção")
PAGINA_DOS_PAPEIS = "conhecimento/motores-auxiliares.md"

CABECALHO = "Motores auxiliares desta máquina, do cadastro local — dado, não ordem:"
UMA_LINHA = "  {nome} — {papeis} | {cobranca} | {disponibilidade}"
RODAPE = ("Papel que casa se despacha, e você diz qual escolheu. Nenhum acusa "
          "tarefa falhada pelo código de saída: confira o RESULTADO. Os "
          "papéis, e o que não vai para motor nenhum: {pagina}")

SEM_PAPEL_DECLARADO = "papel nenhum declarado"
SEM_COBRANCA_DECLARADA = "cobrança não declarada"
NAO_PROVADO = "NÃO PROVADO ({veredito}): sonde antes de despachar"
FALHOU_CALADO = ("o aviso dos motores auxiliares não saiu ({falha}): a sessão "
                 "abre sem saber o que esta máquina pode despachar")
SALDO_DESCONHECIDO = "saldo só se descobre despachando"
SALDO_SEM_INSTRUMENTO = "saldo não medido: o instrumento dos motores não respondeu"
SALDO_NAO_MEDIDO = "saldo não medido: {razao}"
SALDO_LIDO = "{quanto}% da janela usados"


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def motores_cadastrados(raiz: Path) -> dict:
    try:
        guardado = json.loads(
            (raiz / ARQUIVO_DO_CADASTRO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(guardado, dict):
        return {}
    cadastrados = guardado.get(CHAVE_DOS_MOTORES)
    return cadastrados if isinstance(cadastrados, dict) else {}


def leitor_do_credito(raiz: Path):
    alvo = raiz / INSTRUMENTO_DOS_MOTORES
    if not alvo.is_file():
        return None
    try:
        receita = importlib.util.spec_from_file_location(
            NOME_DO_MODULO_CARREGADO, alvo)
        modulo = importlib.util.module_from_spec(receita)
        receita.loader.exec_module(modulo)
        return modulo.credito_do_motor
    except Exception:
        return None


def pasta_do_limite(motor: dict) -> Path:
    declarada = str(motor.get("credito_antes_de_despachar") or "")
    if not declarada:
        return None
    pasta = Path(declarada).expanduser()
    return pasta if pasta.is_dir() else None


def disponibilidade(motor: dict, ler_credito) -> str:
    veredito = str(motor.get("veredito") or "")
    if veredito not in VEREDITOS_QUE_SERVEM or not motor.get("provado_em"):
        return NAO_PROVADO.format(veredito=veredito or "nunca sondado")
    pasta = pasta_do_limite(motor)
    if pasta is None:
        return SALDO_DESCONHECIDO
    if ler_credito is None:
        return SALDO_SEM_INSTRUMENTO
    try:
        lido = ler_credito({CHAVE_DA_FONTE_NO_INSTRUMENTO: str(pasta)})
    except Exception as falha:
        return SALDO_NAO_MEDIDO.format(razao=type(falha).__name__)
    quanto = (lido or {}).get("usado_por_cento")
    if quanto is None:
        return SALDO_NAO_MEDIDO.format(
            razao=(lido or {}).get("razao") or "o instrumento não disse")
    return SALDO_LIDO.format(quanto=quanto)


def linha_do_motor(nome: str, motor: dict, ler_credito) -> str:
    papeis = [str(p) for p in (motor.get("papeis") or []) if str(p).strip()]
    return UMA_LINHA.format(
        nome=nome,
        papeis=", ".join(papeis) or SEM_PAPEL_DECLARADO,
        cobranca=motor.get("cobranca") or SEM_COBRANCA_DECLARADA,
        disponibilidade=disponibilidade(motor, ler_credito))


def decisao(raiz: Path, ler_credito=None) -> str:
    cadastrados = motores_cadastrados(raiz)
    if not cadastrados:
        return ""
    linhas = [CABECALHO]
    for nome in sorted(cadastrados):
        motor = cadastrados[nome]
        if isinstance(motor, dict):
            linhas.append(linha_do_motor(nome, motor, ler_credito))
    if len(linhas) == 1:
        return ""
    linhas.append(RODAPE.format(pagina=PAGINA_DOS_PAPEIS))
    return "\n".join(linhas)


def main() -> int:
    try:
        raiz = raiz_do_projeto_nunca_o_cwd()
        aviso = decisao(raiz, leitor_do_credito(raiz))
    except Exception as falha:
        print(FALHOU_CALADO.format(falha=type(falha).__name__),
              file=sys.stderr)
        return SILENCIO
    if aviso:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": EVENTO_DE_INICIO_DE_SESSAO,
            "additionalContext": aviso}}))
    return SILENCIO


def testar() -> int:
    import tempfile
    falhas, rodados = [], []

    def caso(rotulo, passou):
        rodados.append(rotulo)
        if not passou:
            falhas.append(rotulo)

    def gravar(raiz: Path, conteudo) -> None:
        alvo = raiz / ARQUIVO_DO_CADASTRO
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(conteudo if isinstance(conteudo, str)
                        else json.dumps(conteudo, ensure_ascii=False),
                        encoding="utf-8")

    motor_de_assinatura = {
        "papeis": ["crítico", "tarefa somente leitura"],
        "cobranca": "assinatura", "veredito": "atenção",
        "provado_em": "2026-09-19"}
    motor_pre_pago = {
        "papeis": ["pesquisa"], "cobranca": "pré-pago por token",
        "veredito": "passou", "provado_em": "2026-09-19",
        "credito_antes_de_despachar": "não há fonte local: só despachando"}

    with tempfile.TemporaryDirectory(prefix="aviso-motores-") as pasta:
        raiz = Path(pasta)
        sessoes = raiz / "sessoes"
        sessoes.mkdir()
        dois_por_cento = lambda receita: {"usado_por_cento": 2.0,
                                          "razao": "lido do arquivo"}
        sem_numero = lambda receita: {"usado_por_cento": None,
                                      "razao": "a sessão não registrou limite"}

        caso("sem o arquivo de cadastro o gancho cala — máquina sem motor "
             "abre íntegra", decisao(raiz, dois_por_cento) == "")

        gravar(raiz, {"issues": {"repositorio": "x"}})
        caso("cadastro sem a chave dos motores cala",
             decisao(raiz, dois_por_cento) == "")

        gravar(raiz, {"motores": {}})
        caso("chave dos motores vazia cala",
             decisao(raiz, dois_por_cento) == "")

        gravar(raiz, "{isto não é json")
        caso("cadastro ilegível cala em vez de estourar",
             decisao(raiz, dois_por_cento) == "")

        com_pasta = dict(motor_de_assinatura,
                         credito_antes_de_despachar=str(sessoes))
        gravar(raiz, {"motores": {"motor-de-mentira": com_pasta}})
        dito = decisao(raiz, dois_por_cento)
        caso("o nome do motor sai do cadastro, então motor novo aparece sem "
             "tocar o gancho", "motor-de-mentira" in dito)
        caso("e os papéis dele aparecem", "crítico" in dito)
        caso("e a cobrança aparece, porque estourar assinatura custa espera "
             "e estourar pré-pago custa dinheiro", "assinatura" in dito)
        caso("e o saldo lido aparece com o número", "2.0% da janela" in dito)
        caso("o aviso se apresenta como dado, não como ordem",
             "dado, não ordem" in dito)
        caso("o aviso lembra que código de saída não prova tarefa cumprida",
             "código de saída" in dito and "RESULTADO" in dito)
        caso("o aviso aponta a página dos papéis", PAGINA_DOS_PAPEIS in dito)

        gravar(raiz, {"motores": {"motor-de-mentira": com_pasta}})
        caso("fonte local sem número vira NÃO MEDIDO, nunca zero",
             "não medido" in decisao(raiz, sem_numero)
             and "0%" not in decisao(raiz, sem_numero))
        caso("sem o instrumento dos motores o saldo é não medido, e o motor "
             "continua listado",
             "não medido" in decisao(raiz, None)
             and "motor-de-mentira" in decisao(raiz, None))

        def leitor_que_estoura(receita):
            raise RuntimeError("quebrou")

        caso("leitor que estoura vira não medido, não derruba a abertura",
             "não medido" in decisao(raiz, leitor_que_estoura))

        gravar(raiz, {"motores": {"motor-pre-pago": motor_pre_pago}})
        dito = decisao(raiz, dois_por_cento)
        caso("motor sem fonte local diz saldo desconhecido em vez de "
             "inventar número", SALDO_DESCONHECIDO in dito)
        caso("e não empresta o número do outro motor", "2.0%" not in dito)

        nunca_sondado = dict(motor_de_assinatura, veredito="não mediu",
                             credito_antes_de_despachar=str(sessoes))
        gravar(raiz, {"motores": {"motor-cru": nunca_sondado}})
        dito = decisao(raiz, dois_por_cento)
        caso("motor que não passou a bancada aparece como NÃO PROVADO",
             "NÃO PROVADO" in dito)
        caso("e o saldo dele não é mostrado, porque saldo não é prova",
             "2.0%" not in dito)

        reprovado = dict(motor_de_assinatura, veredito="falhou")
        gravar(raiz, {"motores": {"motor-reprovado": reprovado}})
        caso("motor reprovado também aparece como NÃO PROVADO",
             "NÃO PROVADO" in decisao(raiz, dois_por_cento))

        sem_data = dict(motor_de_assinatura, provado_em="",
                        credito_antes_de_despachar=str(sessoes))
        gravar(raiz, {"motores": {"motor-sem-data": sem_data}})
        caso("veredito bom sem data de prova não é prova",
             "NÃO PROVADO" in decisao(raiz, dois_por_cento))

        gravar(raiz, {"motores": {"motor-torto": "isto não é objeto"}})
        caso("linha torta no cadastro não derruba nem vira motor",
             decisao(raiz, dois_por_cento) == "")

        gravar(raiz, {"motores": {"motor-mudo": {"veredito": "passou",
                                                 "provado_em": "2026-09-19"}}})
        dito = decisao(raiz, dois_por_cento)
        caso("motor sem papel declarado diz isso, em vez de linha vazia",
             SEM_PAPEL_DECLARADO in dito)
        caso("motor sem cobrança declarada também diz, porque a cobrança "
             "decide o que estourar custa", SEM_COBRANCA_DECLARADA in dito)

    if falhas:
        for f in falhas:
            print(f"FALHOU: {f}")
        print(f"FALHOU: {len(falhas)} de {len(rodados)} casos")
        return 1
    print(f"OK: o aviso dos motores auxiliares — {len(rodados)} casos")
    return 0


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
