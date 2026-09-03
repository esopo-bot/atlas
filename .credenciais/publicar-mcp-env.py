import os
import subprocess
import sys
from pathlib import Path

ENVFILE = Path(__file__).with_name("mcp.env")
SEM_COFRE = "mcp.env não existe ao lado deste script."
FALHA_AO_PUBLICAR = "FALHA ao publicar {}: {}"
MARCA_QUE_TORNA_A_LINHA_IDEMPOTENTE = (
    "# carrega os nomes do mcp.env no shell (publicar-mcp-env.py)")
LINHA_QUE_CALA_SE_O_COFRE_SUMIR = (
    '[ -f "%s" ] && { set -a; . "%s"; set +a; }  %s\n')
PERFIS_DO_SHELL = (".profile", ".bashrc")
PASTA_DO_CANAL_DA_SESSAO_GRAFICA = (".config", "environment.d")
ARQUIVO_DO_CANAL_DA_SESSAO_GRAFICA = "90-mcp.conf"
SO_O_DONO_LE = 0o600
AVISO_DE_SESSAO_ABERTA = ("Sessão aberta não enxerga variável nova: feche e "
                          "abra o terminal ou o VS Code.")
AVISO_DOS_DOIS_CANAIS = ("Terminal novo já os enxerga; o ícone (sessão "
                         "gráfica), só depois de deslogar e logar.")

if not ENVFILE.exists():
    sys.exit(SEM_COFRE)

nomes = []
for linha in ENVFILE.read_text(encoding="utf-8").splitlines():
    if not linha or linha.startswith("#") or "=" not in linha:
        continue
    nome, _, valor = linha.partition("=")
    nomes.append((nome.strip(), valor))

if os.name == "nt":
    for nome, valor in nomes:
        publicou = subprocess.run(["setx", nome, valor],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace")
        if publicou.returncode != 0:
            sys.exit(FALHA_AO_PUBLICAR.format(
                nome, publicou.stderr.strip()[:100]))
    print("Publicadas:", ", ".join(n for n, _ in nomes))
    print(AVISO_DE_SESSAO_ABERTA)
else:
    carrega = LINHA_QUE_CALA_SE_O_COFRE_SUMIR % (
        ENVFILE, ENVFILE, MARCA_QUE_TORNA_A_LINHA_IDEMPOTENTE)
    for nome_do_perfil in PERFIS_DO_SHELL:
        perfil = Path.home() / nome_do_perfil
        texto = perfil.read_text(encoding="utf-8") if perfil.exists() else ""
        if MARCA_QUE_TORNA_A_LINHA_IDEMPOTENTE in texto:
            print(f"já instalado: {perfil}")
            continue
        with perfil.open("a", encoding="utf-8") as arquivo:
            if texto and not texto.endswith("\n"):
                arquivo.write("\n")
            arquivo.write(carrega)
        print(f"instalado:   {perfil}")

    pasta = Path.home().joinpath(*PASTA_DO_CANAL_DA_SESSAO_GRAFICA)
    pasta.mkdir(parents=True, exist_ok=True)
    canal_da_sessao_grafica = pasta / ARQUIVO_DO_CANAL_DA_SESSAO_GRAFICA
    canal_da_sessao_grafica.write_text(
        "".join(f"{n}={v}\n" for n, v in nomes), encoding="utf-8")
    canal_da_sessao_grafica.chmod(SO_O_DONO_LE)
    print(f"drop-in:     {canal_da_sessao_grafica}")
    print("Nomes no mcp.env:", ", ".join(n for n, _ in nomes))
    print(AVISO_DOS_DOIS_CANAIS)
