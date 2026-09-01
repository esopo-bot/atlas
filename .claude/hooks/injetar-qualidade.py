import json
import sys
import tempfile
from pathlib import Path

CAMINHO_DA_SKILL_DE_QUALIDADE = "skills/qualidade/SKILL.md"
NIVEIS_DO_GANCHO_ATE_A_PASTA_CLAUDE = 1
ABERTURA_DO_FRONTMATTER = "---"
FECHAMENTO_DO_FRONTMATTER = "\n---\n"
EVENTO_DE_INICIO_DE_SESSAO = "SessionStart"
BANDEIRA_DE_TESTE = "--testar"
FALHA_ABERTO = 0
FIM_NORMAL = 0

RESUMO_OK = "OK: {} casos — {} de corpo, {} de leitura, {} de recado"
RESUMO_FALHOU = "FALHOU: {} de {} casos"
FALHA = "  [{}]"


def caminho_da_skill() -> Path:
    pasta_claude = Path(__file__).resolve().parents[
        NIVEIS_DO_GANCHO_ATE_A_PASTA_CLAUDE]
    return pasta_claude / CAMINHO_DA_SKILL_DE_QUALIDADE


def corpo_sem_o_frontmatter(texto: str) -> str:
    if not texto.startswith(ABERTURA_DO_FRONTMATTER):
        return texto
    _, _, depois_do_frontmatter = texto.partition(FECHAMENTO_DO_FRONTMATTER)
    return depois_do_frontmatter.lstrip() or texto


def ler_a_skill(caminho: Path):
    try:
        return caminho.read_text(encoding="utf-8")
    except OSError:
        return None


def recado(corpo: str) -> str:
    return json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_DE_INICIO_DE_SESSAO,
        "additionalContext": corpo,
    }})


def main() -> int:
    skill = ler_a_skill(caminho_da_skill())
    if skill is None:
        return FALHA_ABERTO
    print(recado(corpo_sem_o_frontmatter(skill)))
    return FIM_NORMAL


def testar() -> int:
    CORPO = [
        ("frontmatter sai e o corpo fica",
         "---\nname: q\n---\n\n# Título\n\ntexto\n", "# Título\n\ntexto\n"),
        ("sem frontmatter, o texto passa inteiro",
         "# Título\n\ntexto\n", "# Título\n\ntexto\n"),
        ("frontmatter sem fechamento não come o arquivo",
         "---\nname: q\nsem fim\n", "---\nname: q\nsem fim\n"),
        ("frontmatter que fecha sem corpo devolve o original",
         "---\nname: q\n---\n", "---\nname: q\n---\n"),
        ("três traços no meio do texto não são frontmatter",
         "texto\n\n---\n\nmais\n", "texto\n\n---\n\nmais\n"),
    ]

    falhas = []
    for rotulo, entrada, esperado in CORPO:
        if corpo_sem_o_frontmatter(entrada) != esperado:
            falhas.append(rotulo)

    with tempfile.TemporaryDirectory() as pasta:
        ausente = Path(pasta) / "nao-existe.md"
        if ler_a_skill(ausente) is not None:
            falhas.append("skill ausente devia devolver None")
        presente = Path(pasta) / "existe.md"
        presente.write_text("---\na: b\n---\n\ncorpo\n", encoding="utf-8")
        if ler_a_skill(presente) != "---\na: b\n---\n\ncorpo\n":
            falhas.append("skill presente devia voltar inteira")
        pasta_no_lugar_do_arquivo = Path(pasta) / "pasta"
        pasta_no_lugar_do_arquivo.mkdir()
        if ler_a_skill(pasta_no_lugar_do_arquivo) is not None:
            falhas.append("pasta no lugar do arquivo devia falhar aberto")

    saida = json.loads(recado("corpo"))["hookSpecificOutput"]
    if saida["hookEventName"] != EVENTO_DE_INICIO_DE_SESSAO:
        falhas.append("o recado tem de nomear o evento de início de sessão")
    if saida["additionalContext"] != "corpo":
        falhas.append("o recado tem de levar o corpo")

    DE_LEITURA, DE_RECADO = 3, 2
    total = len(CORPO) + DE_LEITURA + DE_RECADO
    if falhas:
        print(RESUMO_FALHOU.format(len(falhas), total))
        for falha in falhas:
            print(FALHA.format(falha))
        return 1
    print(RESUMO_OK.format(total, len(CORPO), DE_LEITURA, DE_RECADO))
    return 0


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
