"""Gancho de início de sessão: injeta o padrão de qualidade de código.

Skill de padrão não dispara sozinha (medido: zero em 160 tentativas). Este
gancho entrega o corpo dela ao agente em toda sessão — três em três, medido.

O frontmatter fica de fora: nome e descrição já chegam ao agente pelo catálogo
de skills, e injetá-los de novo é contexto pago duas vezes por sessão.
"""

import json
import sys
from pathlib import Path

skill = Path(__file__).resolve().parents[1] / "skills/qualidade/SKILL.md"
try:
    corpo = skill.read_text(encoding="utf-8")
except OSError:
    sys.exit(0)  # falha aberto: a sessão nunca fica presa por causa do gancho

if corpo.startswith("---"):
    _, _, resto = corpo.partition("\n---\n")
    corpo = resto.lstrip() or corpo  # frontmatter torto: manda o arquivo todo

print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": corpo,
}}))
sys.exit(0)
