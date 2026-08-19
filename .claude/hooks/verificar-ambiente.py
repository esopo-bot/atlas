import json
import os
import re
import shutil
import sys
from pathlib import Path

ARQUIVO_MCP = ".mcp.json"
ARQUIVO_AMBIENTE = "nucleo/ambiente.json"
ARQUIVO_ANTIGO = "ambiente.txt"

TIPO_RECEITA = "receita"
TIPO_COMANDO = "comando"
TIPO_PASTA = "pasta"
TIPO_ARQUIVO = "arquivo"
TIPO_VARIAVEL = "variavel"
TIPOS = (TIPO_RECEITA, TIPO_COMANDO, TIPO_PASTA, TIPO_ARQUIVO, TIPO_VARIAVEL)

VARIAVEL_COM_PADRAO_OPCIONAL = re.compile(
    r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-[^}]*)?\}")

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

EVENTO_DE_INICIO_DE_SESSAO = "SessionStart"
BANDEIRA_DE_TESTE = "--testar"
SILENCIO = 0
FALHA_ABERTO = 0

ERRO_TOPO_NAO_E_OBJETO = "o topo tem de ser um objeto"
PROBLEMA_VARIAVEL_DO_MCP_AUSENTE = (
    "- variável `{}` ausente do ambiente (o .mcp.json a usa)")
PROBLEMA_DECLARACAO_ILEGIVEL = (
    "- `{}` ilegível ({}) — nenhuma exigência do repositório foi verificada")
PROBLEMA_ENDERECO_ANTIGO = (
    "- `{}` virou `{}`: mova as declarações para lá — o gancho não lê mais "
    "o .txt")
PROBLEMA_POR_TIPO = {
    TIPO_RECEITA: "- a própria receita `{}` não existe no disco",
    TIPO_COMANDO: "- comando `{}` não está no PATH",
    TIPO_PASTA: "- pasta `{}` não existe",
    TIPO_ARQUIVO: "- arquivo `{}` não está no disco",
    TIPO_VARIAVEL: "- variável `{}` ausente do ambiente",
}

FECHO_COM_RECEITA = "A receita para repor: {}"
FECHO_SEM_RECEITA = (
    "Nenhuma receita declarada — a chave `receita` do {} pode apontar a "
    "página que ensina a repor.")
AVISO = (
    "AVISO do gancho verificar-ambiente: esta máquina não tem tudo o que o "
    "repositório declara precisar. Perda de migração é silenciosa — este é o "
    "aviso que não existiu na mudança.\n{}\n{}\n"
    "Avise o dono antes de precisar, não depois de faltar. Nome se "
    "verifica; valor não se imprime nem se procura."
)

FALHA_DEVIA_ACUSAR = "  DEVIA ACUSAR e calou — {}"
FALHA_DEVIA_CALAR = "  DEVIA CALAR e acusou — {}: {}"
RESUMO_FALHOU = "FALHOU: {} de {} casos"
RESUMO_OK = "OK: {} casos — {} acusados, {} calados"


def variaveis_exigidas_sem_padrao(texto: str) -> list:
    vistos, nomes = set(), []
    for nome, padrao_que_cobre_a_ausencia in (
            VARIAVEL_COM_PADRAO_OPCIONAL.findall(texto)):
        if padrao_que_cobre_a_ausencia or nome in vistos:
            continue
        vistos.add(nome)
        nomes.append(nome)
    return nomes


def declaracoes(dados: dict) -> list:
    pares = []
    for tipo in TIPOS:
        valores = dados.get(tipo) or []
        if isinstance(valores, str):
            valores = [valores]
        if not isinstance(valores, list):
            continue
        for valor in valores:
            if isinstance(valor, str) and valor.strip():
                pares.append((tipo, valor.strip()))
    return pares


def alvo_no_disco(raiz: Path, valor: str) -> Path:
    caminho = Path(valor.replace("\\", "/")).expanduser()
    return caminho if caminho.is_absolute() else raiz / caminho


def variaveis_do_mcp_que_faltam(raiz: Path, env) -> list:
    mcp = raiz / ARQUIVO_MCP
    if not mcp.is_file():
        return []
    return [nome for nome in
            variaveis_exigidas_sem_padrao(mcp.read_text(encoding="utf-8"))
            if nome not in env]


def ler_declaracao(caminho: Path) -> tuple:
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as erro:
        return {}, str(erro)
    if not isinstance(dados, dict):
        return {}, ERRO_TOPO_NAO_E_OBJETO
    return dados, ""


def declaracao_atendida(tipo: str, valor: str, raiz: Path, env,
                        caminho_path) -> bool:
    if tipo in (TIPO_RECEITA, TIPO_ARQUIVO):
        return alvo_no_disco(raiz, valor).is_file()
    if tipo == TIPO_COMANDO:
        return bool(shutil.which(valor, path=caminho_path))
    if tipo == TIPO_PASTA:
        return alvo_no_disco(raiz, valor).is_dir()
    return valor in env


def faltas(raiz: Path, env=None, caminho_path=None) -> tuple:
    env = os.environ if env is None else env
    problemas, receita = [], None

    variaveis_ja_acusadas = set()
    for nome in variaveis_do_mcp_que_faltam(raiz, env):
        problemas.append(PROBLEMA_VARIAVEL_DO_MCP_AUSENTE.format(nome))
        variaveis_ja_acusadas.add(nome)

    declarado = raiz / ARQUIVO_AMBIENTE
    if declarado.is_file():
        dados, motivo_de_ilegivel = ler_declaracao(declarado)
        if motivo_de_ilegivel:
            problemas.append(PROBLEMA_DECLARACAO_ILEGIVEL.format(
                ARQUIVO_AMBIENTE, motivo_de_ilegivel))
        for tipo, valor in declaracoes(dados):
            if tipo == TIPO_RECEITA:
                receita = valor
            if tipo == TIPO_VARIAVEL and valor in variaveis_ja_acusadas:
                continue
            if not declaracao_atendida(tipo, valor, raiz, env, caminho_path):
                problemas.append(PROBLEMA_POR_TIPO[tipo].format(valor))

    if (raiz / ARQUIVO_ANTIGO).is_file():
        problemas.append(PROBLEMA_ENDERECO_ANTIGO.format(
            ARQUIVO_ANTIGO, ARQUIVO_AMBIENTE))
    return problemas, receita


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def main() -> int:
    try:
        problemas, receita = faltas(raiz_do_projeto_nunca_o_cwd())
    except Exception:
        return FALHA_ABERTO

    if not problemas:
        return SILENCIO

    fecho = (FECHO_COM_RECEITA.format(receita) if receita
             else FECHO_SEM_RECEITA.format(ARQUIVO_AMBIENTE))
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_DE_INICIO_DE_SESSAO,
        "additionalContext": AVISO.format("\n".join(problemas), fecho),
    }}))
    return SILENCIO


ACUSA = [
    ("variável do .mcp.json ausente",
     dict(mcp='{"x": "${TAMBOR_MAIOR}"}')),
    ("variável declarada ausente",
     dict(declarado={"variavel": ["CAIXA_DE_MUSICA"]})),
    ("comando fora do PATH",
     dict(declarado={"comando": ["regador-automatico"]})),
    ("pasta que não existe",
     dict(declarado={"pasta": ["estufa/inverno"]})),
    ("arquivo que não existe",
     dict(declarado={"arquivo": ["estufa/inventario.md"]})),
    ("receita apontando página morta",
     dict(declarado={"receita": "cadernos/plantio.md"})),
    ("declaração ilegível não passa batido",
     dict(declarado="{quebrado")),
    ("o endereço velho ainda no disco acusa a mudança",
     dict(antigo="comando prensa-de-flores\n")),
]

CALA = [
    ("variável presente no ambiente",
     dict(mcp='{"x": "${SINO_DE_VENTO_TOKEN}"}')),
    ("variável com padrão se vira sem valor",
     dict(mcp='{"x": "${TAMBOR_MAIOR:-surdo}"}')),
    ("comando que está no PATH",
     dict(declarado={"comando": ["prensa-de-flores"]})),
    ("pasta que existe",
     dict(declarado={"pasta": ["estufa"]})),
    ("arquivo que existe",
     dict(declarado={"arquivo": ["estufa/regras.md"]})),
    ("receita que existe",
     dict(declarado={"receita": "estufa/regras.md"})),
    ("sem declaração nenhuma", dict()),
    ("comentário do repositório e chave desconhecida ficam de fora",
     dict(declarado={"comentario": "nota do repositório",
                     "receita": None})),
    ("lista vazia não inventa exigência",
     dict(declarado={"comando": [], "pasta": [], "variavel": []})),
]


def testar() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        caixa_de_ferramentas = raiz / "caixa-de-ferramentas"
        caixa_de_ferramentas.mkdir()
        util = caixa_de_ferramentas / "prensa-de-flores"
        util.write_text("#!/bin/sh\n", encoding="utf-8")
        util.chmod(0o755)

        (raiz / "estufa").mkdir()
        (raiz / "estufa/regras.md").write_text("", encoding="utf-8")

        ambiente = {"SINO_DE_VENTO_TOKEN": "presente"}

        def faltas_do_caso(mcp=None, declarado=None, antigo=None):
            for nome, conteudo in ((ARQUIVO_MCP, mcp),
                                   (ARQUIVO_AMBIENTE, declarado),
                                   (ARQUIVO_ANTIGO, antigo)):
                alvo = raiz / nome
                alvo.parent.mkdir(parents=True, exist_ok=True)
                if conteudo is None:
                    alvo.unlink(missing_ok=True)
                elif isinstance(conteudo, str):
                    alvo.write_text(conteudo, encoding="utf-8")
                else:
                    alvo.write_text(json.dumps(conteudo, ensure_ascii=False),
                                    encoding="utf-8")
            return faltas(raiz, env=ambiente,
                          caminho_path=str(caixa_de_ferramentas))

        falhas = []
        for rotulo, caso in ACUSA:
            problemas, _ = faltas_do_caso(**caso)
            if not problemas:
                falhas.append(FALHA_DEVIA_ACUSAR.format(rotulo))
        for rotulo, caso in CALA:
            problemas, _ = faltas_do_caso(**caso)
            if problemas:
                falhas.append(FALHA_DEVIA_CALAR.format(rotulo, problemas))

        total = len(ACUSA) + len(CALA)
        if falhas:
            print(RESUMO_FALHOU.format(len(falhas), total))
            print("\n".join(falhas))
            return 1
        print(RESUMO_OK.format(total, len(ACUSA), len(CALA)))
        return 0


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
