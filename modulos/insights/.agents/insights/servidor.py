import json
import sys
from pathlib import Path

from mcp.server import MCPServer

FERRAMENTAS = Path(__file__).resolve().parent
sys.path.insert(0, str(FERRAMENTAS))
import insights

BANDEIRA_DE_TESTE = "--testar"

servidor = MCPServer(
    name="aws-logs-insights",
    version="1.0.0",
    instructions=(
        "Consulta somente leitura ao CloudWatch Logs Insights. Use sempre o grupo de log, "
        "a regiao e a janela informados. As credenciais vem da cadeia padrao da AWS."
    ),
)


def resposta_da_consulta(grupo: str, regiao: str, consulta: str, desde: str,
                         ate: str, teto: int) -> str:
    try:
        return consulta_em_colunas(grupo, regiao, consulta, desde, ate, teto)
    except SystemExit as recusa:
        return str(recusa)


def consulta_em_colunas(grupo: str, regiao: str, consulta: str, desde: str,
                        ate: str, teto: int) -> str:
    fim = insights.instante_em_epoch(ate, "ate")
    inicio = insights.instante_em_epoch(desde, "desde", referencia=fim)
    if inicio > fim:
        return insights.ERRO_INICIO_DEPOIS_DO_FIM.format(desde=desde, ate=ate)
    for aviso in insights.avisos_da_consulta(consulta):
        print(aviso, file=sys.stderr)
    resultado = insights.disparar(grupo, regiao, consulta, inicio, fim, teto)
    return json.dumps(insights.linhas_do_resultado(resultado),
                      ensure_ascii=False, indent=2)


@servidor.tool(
    title="Consultar logs AWS",
    description=(
        "Executa uma consulta somente leitura no CloudWatch Logs Insights. Informe o grupo "
        "de log, a regiao, a consulta e a janela desde. O fim padrao e agora."
    ),
)
def consultar_logs(grupo: str, regiao: str, consulta: str, desde: str, ate: str = "agora", teto: int = 60) -> str:
    return resposta_da_consulta(grupo, regiao, consulta, desde, ate, teto)


def testar() -> int:
    falhas = []

    def caso(rotulo, condicao):
        if not condicao:
            falhas.append(rotulo)

    recusa = "o aws não respondeu: Unable to locate credentials"
    disparo_verdadeiro = insights.disparar

    def disparo_sem_credencial(*argumentos, **nomeados):
        raise SystemExit(recusa)

    insights.disparar = disparo_sem_credencial
    try:
        devolvido = resposta_da_consulta("/g", "us-east-1", "fields @timestamp",
                                         "1h", "agora", 60)
        caso("credencial ausente volta como texto, e o servidor continua vivo",
             devolvido == recusa)
    except SystemExit:
        caso("credencial ausente volta como texto, e o servidor continua vivo",
             False)
    finally:
        insights.disparar = disparo_verdadeiro

    try:
        devolvido = resposta_da_consulta("/g", "us-east-1", "fields @timestamp",
                                         "ontem de manhã", "agora", 60)
        caso("janela inválida volta como texto, e o servidor continua vivo",
             devolvido.startswith(insights.ERRO_JANELA.split("{")[0]))
    except SystemExit:
        caso("janela inválida volta como texto, e o servidor continua vivo",
             False)

    if falhas:
        print("FALHOU: " + "; ".join(falhas))
        return 1
    print("OK: 2 casos — recusa do instrumento vira texto devolvido, nunca "
          "morte do servidor")
    return 0


if __name__ == "__main__":
    for canal in (sys.stdin, sys.stdout, sys.stderr):
        if not getattr(canal, "closed", True) and hasattr(canal, "reconfigure"):
            canal.reconfigure(encoding="utf-8", errors="replace")
    if BANDEIRA_DE_TESTE in sys.argv[1:2]:
        sys.exit(testar())
    servidor.run("stdio")
