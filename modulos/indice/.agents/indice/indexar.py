import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

BANDEIRA_DE_TESTE = "--testar"
USO = ("indexa o acervo pelo servidor do índice, um alvo por vez, para rodar "
       "em segundo plano. Fala JSON-RPC direto com o servidor, sem depender "
       "do cliente MCP da sessão — assim a indexação sobrevive à sessão que "
       "a disparou")

ARQUIVO_DOS_ALVOS = ".agents/indice/alvos.json"
CAMPO_DOS_ALVOS = "alvos"
CAMPO_DO_SERVIDOR = "servidor"
CAMPO_DO_AMBIENTE = "ambiente"

PROTOCOLO = "2024-11-05"
QUEM_CHAMA = {"name": "indexar", "version": "1"}
FERRAMENTA_DE_INDEXAR = "index_codebase"
FERRAMENTA_DO_ESTADO = "get_indexing_status"
CAMPO_DO_CAMINHO = "path"

TEMPO_DE_HANDSHAKE = 60
TEMPO_POR_ALVO = 8 * 3600
INTERVALO_DA_ESPERA = 5

RECUSA_SEM_ALVOS = ("sem alvos: declare `{}` com a lista de caminhos a "
                    "indexar. O instrumento não adivinha o que é acervo")
RECUSA_SEM_SERVIDOR = ("sem `{}` declarado em {}: diga o caminho do "
                       "`dist/index.js` do servidor do índice. A receita de "
                       "instalar está na página do módulo")
RECUSA_SERVIDOR_AUSENTE = "o servidor declarado não existe: {}"
RECUSA_ALVO_AUSENTE = "alvo que não existe no disco: {}"
NAO_RESPONDEU = "o servidor não respondeu em {}s"
LINHA_DO_ENSAIO = "  {} — {} arquivo(s) sob ele"
CABECA_DO_ENSAIO = "ENSAIO — {} alvo(s), nada será indexado:"
CABECA_DA_RODADA = "indexando {} alvo(s) pelo servidor {}"
LINHA_DO_COMECO = "  [{}/{}] {} — começou"
LINHA_DO_FIM = "  [{}/{}] {} — {} em {}"
FEITO = "indexado"
DISPARADO = "disparado"
MARCA_DE_COMPLETO = "Status: completed"
MARCA_DE_ANDANDO = "currently being indexed"
NAO_TERMINOU = ("o alvo foi disparado mas nao terminou em {} — o servidor "
                "indexa em segundo plano, e matar o processo aqui aborta o "
                "trabalho dele")
JA_ESTAVA = "já estava indexado"
FALHOU = "FALHOU"
MARCA_DE_JA_INDEXADO = "already indexed"
CAMPO_DE_ERRO_DA_FERRAMENTA = "isError"
LINHA_DO_ESTADO = "        {}"
RESUMO_COM_PULADOS = "{} indexado(s), {} já estava(m), {} falhou(ram), em {}"
RESUMO = "{} de {} alvo(s) indexado(s), em {}"


def duracao(segundos: float) -> str:
    return f"{segundos / 60:.1f} min" if segundos >= 60 else f"{segundos:.0f}s"


def configuracao(cwd: str = "") -> dict:
    alvo = Path(cwd or ".") / ARQUIVO_DOS_ALVOS
    try:
        return json.loads(alvo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def recusa_da_configuracao(dado: dict, cwd: str = "") -> str:
    alvos = dado.get(CAMPO_DOS_ALVOS) or []
    if not alvos:
        return RECUSA_SEM_ALVOS.format(ARQUIVO_DOS_ALVOS)
    servidor = dado.get(CAMPO_DO_SERVIDOR) or ""
    if not servidor:
        return RECUSA_SEM_SERVIDOR.format(CAMPO_DO_SERVIDOR, ARQUIVO_DOS_ALVOS)
    if not Path(servidor).expanduser().is_file():
        return RECUSA_SERVIDOR_AUSENTE.format(servidor)
    for caminho in alvos:
        if not Path(caminho).expanduser().is_dir():
            return RECUSA_ALVO_AUSENTE.format(caminho)
    return ""


def quantos_arquivos(caminho: str) -> int:
    raiz = Path(caminho).expanduser()
    return sum(1 for _ in raiz.rglob("*") if _.is_file())


class Servidor:
    def __init__(self, caminho: str, ambiente: dict):
        self.processo = subprocess.Popen(
            ["node", str(Path(caminho).expanduser())],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
            env=dict(os.environ, **(ambiente or {})))
        self.proxima_id = 1

    def manda(self, mensagem: dict) -> None:
        self.processo.stdin.write(json.dumps(mensagem) + "\n")
        self.processo.stdin.flush()

    def espera(self, identidade: int, teto: int):
        comeco = time.monotonic()
        while time.monotonic() - comeco < teto:
            linha = self.processo.stdout.readline()
            if not linha:
                return None
            try:
                resposta = json.loads(linha)
            except ValueError:
                continue
            if resposta.get("id") == identidade:
                return resposta
        return None

    def pergunta(self, metodo: str, parametros: dict, teto: int):
        identidade = self.proxima_id
        self.proxima_id += 1
        self.manda({"jsonrpc": "2.0", "id": identidade, "method": metodo,
                    "params": parametros})
        return self.espera(identidade, teto)

    def apresenta(self) -> bool:
        pronto = self.pergunta("initialize", {
            "protocolVersion": PROTOCOLO, "capabilities": {},
            "clientInfo": QUEM_CHAMA}, TEMPO_DE_HANDSHAKE)
        if pronto is None:
            return False
        self.manda({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return True

    def indexa(self, caminho: str, teto: int, refazer: bool = False):
        argumentos = {CAMPO_DO_CAMINHO: str(Path(caminho).expanduser())}
        if refazer:
            argumentos["force"] = True
        return self.pergunta("tools/call", {
            "name": FERRAMENTA_DE_INDEXAR, "arguments": argumentos}, teto)

    def estado(self, caminho: str, teto: int):
        return self.pergunta("tools/call", {
            "name": FERRAMENTA_DO_ESTADO,
            "arguments": {CAMPO_DO_CAMINHO: str(Path(caminho).expanduser())}},
            teto)

    def espera_terminar(self, caminho: str, teto: int, intervalo: int,
                        relator=None):
        comeco = time.monotonic()
        ultimo = ""
        while time.monotonic() - comeco < teto:
            ultimo = texto_da_resposta(self.estado(caminho, TEMPO_DE_HANDSHAKE))
            if terminou(ultimo):
                return True, ultimo
            if not ainda_anda(ultimo):
                return False, ultimo
            if relator:
                relator(ultimo)
            time.sleep(intervalo)
        return False, ultimo

    def encerra(self) -> None:
        self.processo.kill()


def texto_da_resposta(resposta) -> str:
    if not isinstance(resposta, dict):
        return ""
    partes = (resposta.get("result") or {}).get("content") or []
    return " ".join(p.get("text", "") for p in partes if isinstance(p, dict))


def terminou(texto: str) -> bool:
    return MARCA_DE_COMPLETO in texto


def ainda_anda(texto: str) -> bool:
    return MARCA_DE_ANDANDO in texto


def veredito(resposta) -> str:
    if resposta is None or "error" in resposta:
        return FALHOU
    if not (resposta.get("result") or {}).get(CAMPO_DE_ERRO_DA_FERRAMENTA):
        return FEITO
    return (JA_ESTAVA if MARCA_DE_JA_INDEXADO in texto_da_resposta(resposta)
            else FALHOU)


def ensaiar(alvos: list) -> int:
    print(CABECA_DO_ENSAIO.format(len(alvos)))
    for caminho in alvos:
        print(LINHA_DO_ENSAIO.format(caminho, quantos_arquivos(caminho)))
    return 0


def indexar(dado: dict, teto: int, refazer: bool = False) -> int:
    alvos = dado[CAMPO_DOS_ALVOS]
    servidor = Servidor(dado[CAMPO_DO_SERVIDOR], dado.get(CAMPO_DO_AMBIENTE))
    print(CABECA_DA_RODADA.format(len(alvos), dado[CAMPO_DO_SERVIDOR]))
    if not servidor.apresenta():
        servidor.encerra()
        print(NAO_RESPONDEU.format(TEMPO_DE_HANDSHAKE), file=sys.stderr)
        return 1
    feitos = pulados = 0
    comeco_da_rodada = time.monotonic()
    for i, caminho in enumerate(alvos, 1):
        print(LINHA_DO_COMECO.format(i, len(alvos), caminho), flush=True)
        comeco = time.monotonic()
        resposta = servidor.indexa(caminho, teto, refazer)
        gasto = duracao(time.monotonic() - comeco)
        dito = veredito(resposta)
        if dito == FEITO:
            sobrou = max(1, int(teto - (time.monotonic() - comeco)))
            fechou, ultimo = servidor.espera_terminar(
                caminho, sobrou, INTERVALO_DA_ESPERA)
            gasto = duracao(time.monotonic() - comeco)
            if not fechou:
                dito = FALHOU
                resposta = {"result": {"content": [{"type": "text", "text": (
                    NAO_TERMINOU.format(gasto) + " — " + ultimo)}]}}
        feitos += 1 if dito == FEITO else 0
        pulados += 1 if dito == JA_ESTAVA else 0
        print(LINHA_DO_FIM.format(i, len(alvos), caminho, dito, gasto),
              flush=True)
        if dito == FALHOU:
            print(LINHA_DO_ESTADO.format(
                texto_da_resposta(resposta)[:200] or NAO_RESPONDEU.format(teto)),
                flush=True)
        else:
            print(LINHA_DO_ESTADO.format(
                texto_da_resposta(servidor.estado(caminho, teto)
                                  ).replace(chr(10), " · ")[:200]), flush=True)
    servidor.encerra()
    print(RESUMO_COM_PULADOS.format(
        feitos, pulados, len(alvos) - feitos - pulados,
        duracao(time.monotonic() - comeco_da_rodada)))
    return 0 if feitos + pulados == len(alvos) else 1


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
        servidor = raiz / "servidor.js"
        servidor.write_text("", encoding="utf-8")
        acervo = raiz / "acervo"
        acervo.mkdir()
        (acervo / "um.md").write_text("x", encoding="utf-8")
        (acervo / "dois.md").write_text("y", encoding="utf-8")

        caso("sem alvos declarados o instrumento recusa e diz o arquivo",
             ARQUIVO_DOS_ALVOS in recusa_da_configuracao({}))
        caso("sem servidor declarado ele recusa e ensina o campo",
             CAMPO_DO_SERVIDOR in recusa_da_configuracao(
                 {CAMPO_DOS_ALVOS: [str(acervo)]}))
        caso("servidor declarado que não existe é recusado ANTES de subir "
             "processo — senão a falha vira 'não respondeu', que manda "
             "procurar no lugar errado",
             "não existe" in recusa_da_configuracao(
                 {CAMPO_DOS_ALVOS: [str(acervo)],
                  CAMPO_DO_SERVIDOR: str(raiz / "nao-existe.js")}))
        caso("alvo que não existe no disco é recusado antes de indexar",
             "não existe no disco" in recusa_da_configuracao(
                 {CAMPO_DOS_ALVOS: [str(raiz / "fantasma")],
                  CAMPO_DO_SERVIDOR: str(servidor)}))
        caso("configuração inteira passa sem recusa",
             recusa_da_configuracao({CAMPO_DOS_ALVOS: [str(acervo)],
                                     CAMPO_DO_SERVIDOR: str(servidor)}) == "")
        caso("o ensaio conta os arquivos sob cada alvo, para o dono saber o "
             "tamanho antes de disparar de madrugada",
             quantos_arquivos(str(acervo)) == 2)
        caso("configuração ilegível não estoura — devolve vazio e a recusa "
             "explica",
             configuracao(str(raiz)) == {})
        def resposta_de(texto, erro=False):
            return {"result": {"content": [{"type": "text", "text": texto}],
                               **({"isError": True} if erro else {})}}

        caso("resposta limpa e indexação feita",
             veredito(resposta_de("Indexed 14 files")) == FEITO)
        caso("resposta com isError dizendo 'already indexed' NAO e falha — "
             "e alvo que ja estava, e chamar isso de falha faria a rodada "
             "noturna parecer quebrada toda madrugada",
             veredito(resposta_de("Codebase is already indexed. Use force",
                                  erro=True)) == JA_ESTAVA)
        caso("resposta com isError de qualquer outra causa E falha — o campo "
             "isError vive DENTRO do result, entao olhar so o erro de topo "
             "transforma recusa em sucesso",
             veredito(resposta_de("Milvus connection refused",
                                  erro=True)) == FALHOU)
        caso("servidor que nao respondeu e falha, nao sucesso",
             veredito(None) == FALHOU)
        caso("erro de protocolo tambem e falha",
             veredito({"error": {"code": -1}}) == FALHOU)
        caso("o texto da resposta e extraido para o relato",
             "Indexed" in texto_da_resposta(resposta_de("Indexed 14 files")))
        caso("resposta que nao e objeto nao estoura",
             texto_da_resposta(None) == "")

        caso("estado com 'Status: completed' e alvo terminado",
             terminou("Statistics: 14 files · Status: completed"))
        caso("estado com 'currently being indexed' ainda anda — e o "
             "instrumento NAO pode encerrar aqui, porque matar o processo "
             "aborta a indexacao em segundo plano do servidor",
             ainda_anda("Codebase is currently being indexed. Progress: 3%")
             and not terminou("Progress: 3%"))
        caso("estado que nao diz nem uma coisa nem outra encerra a espera em "
             "vez de girar ate o teto",
             not terminou("erro qualquer") and not ainda_anda("erro qualquer"))

        caso("duração sai em minutos quando passa de um minuto",
             duracao(90) == "1.5 min" and duracao(30) == "30s")

    print(f"{'OK' if not falhou else 'FALHOU'}: {passou + falhou} casos")
    return 1 if falhou else 0


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=USO)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--ensaio", action="store_true",
                        help="mostra os alvos e o tamanho, sem indexar")
    parser.add_argument("--tempo-limite", type=int, default=TEMPO_POR_ALVO,
                        help="teto em segundos de cada alvo")
    parser.add_argument("--refazer", action="store_true",
                        help="reindexa o que já está indexado")
    parser.add_argument(BANDEIRA_DE_TESTE, action="store_true")
    return parser


def main() -> int:
    if BANDEIRA_DE_TESTE in sys.argv[1:]:
        return testar()
    a = montar_parser().parse_args()
    dado = configuracao(a.cwd)
    if (recusa := recusa_da_configuracao(dado, a.cwd)):
        print(recusa, file=sys.stderr)
        return 2
    if a.ensaio:
        return ensaiar(dado[CAMPO_DOS_ALVOS])
    return indexar(dado, a.tempo_limite, a.refazer)


if __name__ == "__main__":
    sys.exit(main())
