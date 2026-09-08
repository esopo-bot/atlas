import argparse
import json
import subprocess
import sys
from pathlib import Path

BANDEIRA_DE_TESTE = "--testar"
USO = ("sobe as duas peças do índice e liga a placa de vídeo quando houver "
       "uma que o docker entregue. Sem placa, sobe igual, em CPU — a decisão "
       "é medida, nunca perguntada a quem instala")

PASTA_DO_MODULO = ".agents/indice"
COMPOSE = "docker-compose.yml"
COMPOSE_COM_PLACA = "docker-compose.gpu.yml"
AJUSTE_LOCAL = "docker-compose.override.yml"
PROJETO = "indice"
SERVICO_DA_PLACA = "embeddings"
CONTAINER_DA_PLACA = "indice-embeddings-1"
MODELO_PADRAO = "nomic-embed-text"

DOCKER = "docker"
COMPOR = (DOCKER, "compose")
TEMPO_DA_SONDA = 120
TEMPO_DE_SUBIR = 900
TEMPO_DO_MODELO = 3600

RECUSA_SEM_COMPOSE = ("não achei {} — instale o módulo antes: "
                      "python montar.py --modulo indice")
RECUSA_SEM_DOCKER = ("o docker não respondeu: `{}`. O índice sobe em "
                     "contêiner, e sem o docker não há o que subir")
COM_PLACA = ("placa de vídeo ligada: {} — quem gera os vetores roda nela. "
             "Medido em 07/09/2026 numa placa de entrada: 232 pedaços por "
             "minuto contra 32 em CPU")
SEM_PLACA = ("sem placa que o docker entregue ({}) — sobe em CPU, que é o "
             "normal e funciona. Repare que placa nenhuma aparece aqui até "
             "o docker conseguir entregá-la, e não só existir na máquina")
COM_AJUSTE_LOCAL = ("ajuste local {} entra junto — arquivo com `-f` explícito "
                    "não carrega o ajuste sozinho, e por isso ele vai nomeado")
SUBINDO = "subindo {} com: {}"
MODELO_CHEGANDO = "baixando o modelo {} dentro do contêiner"
MODELO_JA_ESTAVA = "o modelo {} já estava no contêiner"
PRONTO = "índice de pé. Agora indexe: python {}/indexar.py"
FALHOU_SUBIR = "o docker compose não subiu: {}"
FALHOU_MODELO = ("o modelo {} não baixou: {}. As peças estão de pé; repita "
                 "o passo do modelo quando resolver")
ENSAIO = "ENSAIO — nada sobe. A decisão medida seria:"


def caminho_do_modulo(cwd: str) -> Path:
    return Path(cwd) / PASTA_DO_MODULO


def recusa_da_instalacao(pasta: Path) -> str:
    if not (pasta / COMPOSE).is_file():
        return RECUSA_SEM_COMPOSE.format(pasta / COMPOSE)
    return ""


def rodar(comando, teto: int):
    """Devolve (deu_certo, saida). Falha do docker é dado, nunca exceção
    solta: quem chama decide o que fazer com ela."""
    try:
        pronto = subprocess.run(comando, capture_output=True, text=True,
                                timeout=teto, encoding="utf-8",
                                errors="replace")
    except (OSError, subprocess.SubprocessError) as erro:
        return False, str(erro)
    saida = (pronto.stdout or "") + (pronto.stderr or "")
    return pronto.returncode == 0, saida.strip()


def docker_responde(executor=rodar) -> tuple:
    return executor((DOCKER, "version", "--format", "{{.Server.Version}}"),
                    TEMPO_DA_SONDA)


def imagem_de_quem_gera_os_vetores(pasta: Path, executor=rodar) -> str:
    """Lê a imagem do próprio compose, para sondar a placa com ela em vez de
    baixar uma imagem só para a sonda."""
    deu, saida = executor(COMPOR + ("-f", str(pasta / COMPOSE),
                                    "config", "--format", "json"),
                          TEMPO_DA_SONDA)
    if not deu:
        return ""
    try:
        dado = json.loads(saida)
    except ValueError:
        return ""
    servico = (dado.get("services") or {}).get(SERVICO_DA_PLACA) or {}
    return servico.get("image") or ""


def a_placa_chega_no_conteiner(imagem: str, executor=rodar) -> tuple:
    """A pergunta certa não é se a máquina tem placa, e sim se o docker
    consegue entregá-la: runtime registrado e driver respondendo são coisas
    diferentes, e só o contêiner de verdade separa as duas."""
    if not imagem:
        return False, "não consegui ler a imagem do compose"
    return executor((DOCKER, "run", "--rm", "--gpus", "all",
                     "--entrypoint", "nvidia-smi", imagem,
                     "--query-gpu=name", "--format=csv,noheader"),
                    TEMPO_DA_SONDA)


def arquivos_do_compose(pasta: Path, com_placa: bool) -> list:
    escolhidos = [pasta / COMPOSE]
    if com_placa:
        escolhidos.append(pasta / COMPOSE_COM_PLACA)
    if (pasta / AJUSTE_LOCAL).is_file():
        escolhidos.append(pasta / AJUSTE_LOCAL)
    return escolhidos


def comando_de_subir(arquivos: list) -> tuple:
    nomeados = ()
    for arquivo in arquivos:
        nomeados += ("-f", str(arquivo))
    return COMPOR + nomeados + ("-p", PROJETO, "up", "-d")


def modelo_ja_esta(modelo: str, executor=rodar) -> bool:
    deu, saida = executor((DOCKER, "exec", CONTAINER_DA_PLACA,
                           "ollama", "list"), TEMPO_DA_SONDA)
    return deu and modelo.split(":")[0] in saida


def baixar_o_modelo(modelo: str, executor=rodar) -> tuple:
    return executor((DOCKER, "exec", CONTAINER_DA_PLACA, "ollama", "pull",
                     modelo), TEMPO_DO_MODELO)


def subir(cwd: str, modelo: str, ensaio: bool, executor=rodar) -> int:
    pasta = caminho_do_modulo(cwd)
    if (recusa := recusa_da_instalacao(pasta)):
        print(recusa, file=sys.stderr)
        return 2
    deu, dito = docker_responde(executor)
    if not deu:
        print(RECUSA_SEM_DOCKER.format(dito), file=sys.stderr)
        return 2
    imagem = imagem_de_quem_gera_os_vetores(pasta, executor)
    com_placa, dito = a_placa_chega_no_conteiner(imagem, executor)
    print(COM_PLACA.format(dito.splitlines()[0]) if com_placa
          else SEM_PLACA.format(dito.splitlines()[-1][:120] if dito else "-"))
    arquivos = arquivos_do_compose(pasta, com_placa)
    if (pasta / AJUSTE_LOCAL) in arquivos:
        print(COM_AJUSTE_LOCAL.format(AJUSTE_LOCAL))
    comando = comando_de_subir(arquivos)
    if ensaio:
        print(ENSAIO)
        print("  " + " ".join(comando))
        return 0
    print(SUBINDO.format(PROJETO, " ".join(comando)))
    deu, dito = executor(comando, TEMPO_DE_SUBIR)
    if not deu:
        print(FALHOU_SUBIR.format(dito), file=sys.stderr)
        return 1
    if modelo_ja_esta(modelo, executor):
        print(MODELO_JA_ESTAVA.format(modelo))
    else:
        print(MODELO_CHEGANDO.format(modelo))
        deu, dito = baixar_o_modelo(modelo, executor)
        if not deu:
            print(FALHOU_MODELO.format(modelo, dito), file=sys.stderr)
            return 1
    print(PRONTO.format(PASTA_DO_MODULO))
    return 0


def testar() -> int:
    import tempfile
    passou = falhou = 0

    def caso(nome: str, condicao: bool) -> None:
        nonlocal passou, falhou
        if condicao:
            passou += 1
        else:
            falhou += 1
            print(f"FALHOU: {nome}")

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        modulo = raiz / PASTA_DO_MODULO
        modulo.mkdir(parents=True)

        caso("sem o modulo instalado ele recusa e ensina o comando de "
             "instalar, em vez de subir contêiner do nada",
             "montar.py --modulo indice" in recusa_da_instalacao(modulo))
        (modulo / COMPOSE).write_text("services:\n", encoding="utf-8")
        (modulo / COMPOSE_COM_PLACA).write_text("services:\n",
                                                encoding="utf-8")
        caso("com o compose no lugar, nao recusa",
             recusa_da_instalacao(modulo) == "")

        caso("sem placa, o compose vai sozinho",
             arquivos_do_compose(modulo, False) == [modulo / COMPOSE])
        caso("com placa, o arquivo da placa entra DEPOIS do compose — "
             "ordem e o que decide quem sobrescreve quem",
             arquivos_do_compose(modulo, True)
             == [modulo / COMPOSE, modulo / COMPOSE_COM_PLACA])
        (modulo / AJUSTE_LOCAL).write_text("services:\n", encoding="utf-8")
        caso("o ajuste local entra NOMEADO e por ultimo: compose com `-f` "
             "explicito nao carrega o override sozinho, e quem seguiu a "
             "receita do proxy ficaria sem ele calado",
             arquivos_do_compose(modulo, True)[-1] == modulo / AJUSTE_LOCAL)
        caso("cada arquivo entra com seu proprio -f",
             comando_de_subir([modulo / COMPOSE]).count("-f") == 1
             and comando_de_subir(
                 [modulo / COMPOSE, modulo / COMPOSE_COM_PLACA]
             ).count("-f") == 2)
        caso("o comando termina em up -d, no projeto nomeado",
             comando_de_subir([modulo / COMPOSE])[-4:]
             == ("-p", PROJETO, "up", "-d"))

        falas = []

        def executor_de_prova(roteiro, placa_chega=True, sobe=True):
            def executor(comando, teto):
                falas.append(comando)
                if comando[:2] == (DOCKER, "version"):
                    return True, "29.1.3"
                if comando[:3] == COMPOR + ("-f",) and "config" in comando:
                    return True, json.dumps(
                        {"services": {SERVICO_DA_PLACA:
                                      {"image": "ollama/ollama:latest"}}})
                if "nvidia-smi" in comando:
                    return placa_chega, ("NVIDIA GeForce GTX 1650"
                                         if placa_chega
                                         else "could not select device driver")
                if "up" in comando:
                    return sobe, "Started" if sobe else "no such device"
                if comando[-1:] == ("list",):
                    return True, roteiro
                return True, "ok"
            return executor

        falas.clear()
        saida = subir(str(raiz), MODELO_PADRAO, ensaio=True,
                      executor=executor_de_prova("nomic-embed-text  274 MB"))
        caso("o ensaio decide e mostra o comando, sem subir nada",
             saida == 0 and not any("up" in c for c in falas))

        falas.clear()
        import io, contextlib
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            saida = subir(str(raiz), MODELO_PADRAO, ensaio=False,
                          executor=executor_de_prova("nomic-embed-text"))
        subiu = [c for c in falas if "up" in c][0]
        caso("com placa entregue, o arquivo da placa entra no comando de "
             "subir — e o numero medido aparece, para ninguem achar que e "
             "promessa",
             saida == 0 and COMPOSE_COM_PLACA in " ".join(subiu)
             and "232" in dito.getvalue())
        caso("modelo que ja esta nao e baixado de novo",
             not any("pull" in c for c in falas))

        falas.clear()
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            subir(str(raiz), MODELO_PADRAO, ensaio=False,
                  executor=executor_de_prova("outro-modelo"))
        caso("modelo que falta e baixado",
             any("pull" in c for c in falas))

        falas.clear()
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            saida = subir(str(raiz), MODELO_PADRAO, ensaio=False,
                          executor=executor_de_prova("nomic-embed-text",
                                                     placa_chega=False))
        subiu = [c for c in falas if "up" in c][0]
        caso("sem placa entregue ele SOBE IGUAL, em CPU, e o arquivo da "
             "placa fica de fora — maquina sem placa nao pode ficar sem "
             "indice por causa disto",
             saida == 0 and COMPOSE_COM_PLACA not in " ".join(subiu)
             and "CPU" in dito.getvalue())

        falas.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            saida = subir(str(raiz), MODELO_PADRAO, ensaio=False,
                          executor=executor_de_prova("nomic", sobe=False))
        caso("compose que nao sobe e falha, com o texto do docker colado",
             saida == 1)

        def sem_docker(comando, teto):
            return False, "cannot connect to the docker daemon"
        with contextlib.redirect_stdout(io.StringIO()):
            saida = subir(str(raiz), MODELO_PADRAO, ensaio=False,
                          executor=sem_docker)
        caso("docker fora do ar recusa cedo, em vez de tentar subir",
             saida == 2)

        caso("imagem que nao se le nao vira placa entregue — nao medido "
             "nunca e sim",
             a_placa_chega_no_conteiner("")[0] is False)

    print(f"{'OK' if not falhou else 'FALHOU'}: {passou + falhou} casos")
    return 1 if falhou else 0


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=USO)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--modelo", default=MODELO_PADRAO,
                        help="modelo que gera os vetores")
    parser.add_argument("--ensaio", action="store_true",
                        help="mostra a decisão e o comando, sem subir")
    parser.add_argument(BANDEIRA_DE_TESTE, action="store_true")
    return parser


def main() -> int:
    if BANDEIRA_DE_TESTE in sys.argv[1:]:
        return testar()
    a = montar_parser().parse_args()
    return subir(a.cwd, a.modelo, a.ensaio)


if __name__ == "__main__":
    sys.exit(main())
