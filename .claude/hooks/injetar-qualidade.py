import json
import sys
from pathlib import Path

CAMINHO_DA_SKILL_DE_QUALIDADE = "skills/qualidade/SKILL.md"
NIVEIS_DO_GANCHO_ATE_A_PASTA_CLAUDE = 1
ABERTURA_DO_FRONTMATTER = "---"
FECHAMENTO_DO_FRONTMATTER = "\n---\n"
EVENTO_DE_INICIO_DE_SESSAO = "SessionStart"
FALHA_ABERTO = 0
FIM_NORMAL = 0


def caminho_da_skill() -> Path:
    pasta_claude = Path(__file__).resolve().parents[
        NIVEIS_DO_GANCHO_ATE_A_PASTA_CLAUDE]
    return pasta_claude / CAMINHO_DA_SKILL_DE_QUALIDADE


def corpo_sem_o_frontmatter(texto: str) -> str:
    if not texto.startswith(ABERTURA_DO_FRONTMATTER):
        return texto
    _, _, depois_do_frontmatter = texto.partition(FECHAMENTO_DO_FRONTMATTER)
    return depois_do_frontmatter.lstrip() or texto


try:
    skill = caminho_da_skill().read_text(encoding="utf-8")
except OSError:
    sys.exit(FALHA_ABERTO)

print(json.dumps({"hookSpecificOutput": {
    "hookEventName": EVENTO_DE_INICIO_DE_SESSAO,
    "additionalContext": corpo_sem_o_frontmatter(skill),
}}))
sys.exit(FIM_NORMAL)
