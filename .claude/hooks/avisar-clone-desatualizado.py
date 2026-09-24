import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ARQUIVO_EXECUTOR = "nucleo/executor.json"
PASTA_DOS_VIZINHOS = "projetos"
CERCA_IRMA = "vetar-escrita-em-somente-leitura.py"
NOME_DO_MODULO_IRMAO = "cerca_somente_leitura"
CACHE_DA_CERCA_IRMA = []

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

CHAVE_DA_SESSAO = "session_id"
CHAVE_DA_ENTRADA = "tool_input"
CHAVE_DA_FERRAMENTA = "tool_name"
CHAVE_DO_DIRETORIO = "cwd"
CAMPOS_QUE_SAO_CAMINHO = ("file_path", "path", "notebook_path")
CAMPO_DO_COMANDO = "command"
PEDACO_DE_COMANDO = re.compile(
    r""""([^"]*)"|'([^']*)'|([^\s"'=;|&<>()]+)""")
PREFIXO_DA_REDE_MUDA = "remoto-mudo-"
VALIDADE_DA_REDE_MUDA_EM_SEGUNDOS = 600
SEPARADORES_DE_CAMINHO = ("/", "\\")

PREFIXO_DA_MARCA = "avisou-clone-desatualizado-"
PREFIXO_DO_NAO_MEDIU = "nao-mediu-clone-desatualizado-"
CADASTRO_QUE_NAO_SE_LEU = (
    "o cadastro de vizinhos, em {}, não se deixou ler")
CERCA_IRMA_QUE_NAO_CARREGOU = "a cerca irmã `{}` não carregou ({})"
MARCA_DO_ESTOURO = "estouro-"
DIA_DA_MARCA = "%Y%m%d"
AVISO_DE_QUE_ESTOUROU = (
    "O aviso de clone atrasado NÃO MEDIU: o próprio gancho estourou ({}: "
    "{}). Ele não sabe dizer se esta chamada lia um vizinho. Se a sessão "
    "concluir algo a partir do código de um vizinho, diga de que commit e "
    "de que data a conclusão saiu. Este aviso sai uma vez por dia.")
AVISO_DE_QUE_NAO_MEDIU = (
    "O aviso de clone atrasado NÃO MEDIU: {razao}. Esta sessão está lendo a "
    "pasta dos vizinhos, e sem essa leitura o aviso não sabe quais são "
    "somente leitura nem se o clone deles está atrás do remoto. Silêncio "
    "aqui não quer dizer clone em dia: antes de concluir a partir do código "
    "de um vizinho, diga de que commit e de que data a conclusão saiu.")
PREFIXO_DA_COBRANCA = "cobrou-clone-desatualizado-"
PREFIXO_DO_CACHE = "sha-remoto-"
VALIDADE_DO_CACHE_EM_SEGUNDOS = 6 * 3600
ESPERA_MAXIMA_DA_REDE_EM_SEGUNDOS = 10

SILENCIO = 0
BANDEIRA_DE_TESTE = "--testar"
SEM_AVISO = ""

CHAVE_DO_EVENTO = "hook_event_name"
EVENTO_DE_PARADA = "Stop"
CHAVE_DA_SAIDA = "hookSpecificOutput"
CHAVE_DO_EVENTO_NA_SAIDA = "hookEventName"
CHAVE_DO_CONTEXTO = "additionalContext"

COBRANCA = (
    "Esta sessão leu {quais}, cujo clone está atrás do remoto. Antes de "
    "encerrar, confira uma coisa só: toda conclusão que saiu de lá diz de "
    "que commit e de que data ela saiu? Relato, issue e comentário que "
    "citem aquele código sem a data envelhecem sem avisar — e quem ler "
    "amanhã não tem como saber que a resposta era de semanas atrás.\n"
    "Se alguma conclusão decide alguma coisa, confira pelo remoto o "
    "arquivo que a sustenta antes de entregá-la."
)
E_ENTRE_OS_ULTIMOS = " e "
VIRGULA = ", "

AVISO = (
    "O clone de `{nome}` está ATRÁS do remoto, e é dele que você está "
    "lendo agora.\n"
    "{linhas}\n"
    "Isto NÃO impede a leitura, e sai uma vez por sessão: ler o código do "
    "vizinho continua sendo a forma mais barata de não depender do time "
    "dele. O que o aviso cobra é outra coisa — conclusão tirada daqui tem "
    "de dizer de que commit e de que data ela saiu.\n"
    "Antes de concluir:\n"
    "  - confira pelo remoto SÓ os arquivos que sustentam a sua conclusão, "
    "não o repositório inteiro. Pelo servidor de contexto do provedor, "
    "listando os commits daquele caminho desde a data do clone; lista "
    "vazia quer dizer que a leitura local ainda vale.\n"
    "  - quando o arquivo tiver mudado, leia o conteúdo de hoje pelo "
    "provedor e use esse.\n"
    "  - atualizar o clone é decisão do dono: aqui é território de outro "
    "time, e a cerca de somente leitura recusa escrita nele."
)
LINHA_DA_ARVORE = "  - a árvore que você lê está em {sha}, de {data}"
LINHA_DO_REMOTO = "  - o remoto está em {sha}, que a árvore não tem"
LINHA_DO_MEIO = (
    "  - e há uma segunda defasagem: o próprio clone já baixou {quantos} "
    "commit(s) que a árvore não usa, até {data}. Conferir por "
    "`origin/{ramo}` diria que você está mais novo do que está."
)


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def cerca_irma():
    if CACHE_DA_CERCA_IRMA:
        return CACHE_DA_CERCA_IRMA[0]
    caminho = Path(__file__).resolve().with_name(CERCA_IRMA)
    origem = importlib.util.spec_from_file_location(NOME_DO_MODULO_IRMAO,
                                                    caminho)
    modulo = importlib.util.module_from_spec(origem)
    origem.loader.exec_module(modulo)
    CACHE_DA_CERCA_IRMA.append(modulo)
    return modulo


def vizinhos_somente_leitura_ou_por_que_nao(raiz: Path) -> tuple:
    try:
        cadastro = cerca_irma().cadastro_dos_vizinhos(raiz)
    except Exception as falha:
        return frozenset(), CERCA_IRMA_QUE_NAO_CARREGOU.format(
            CERCA_IRMA, type(falha).__name__)
    if not cadastro.medido:
        return frozenset(), CADASTRO_QUE_NAO_SE_LEU.format(ARQUIVO_EXECUTOR)
    return cadastro.nomes, ""


def alvos_do_pedido(entrada: dict) -> list:
    campos = entrada.get(CHAVE_DA_ENTRADA) or {}
    if not isinstance(campos, dict):
        return []
    alvos = [str(campos[campo]) for campo in CAMPOS_QUE_SAO_CAMINHO
             if campos.get(campo)]
    comando = campos.get(CAMPO_DO_COMANDO)
    if isinstance(comando, str):
        alvos += [pedaco for pedaco in pedacos_do_comando(comando)
                  if any(sinal in pedaco for sinal in SEPARADORES_DE_CAMINHO)]
    return alvos


def pedacos_do_comando(comando: str) -> list:
    pedacos = []
    for entre_duplas, entre_simples, solto in PEDACO_DE_COMANDO.findall(
            comando):
        pedaco = entre_duplas or entre_simples or solto
        opcao, dois_pontos, colado = pedaco.partition(":")
        if opcao.startswith("-") and dois_pontos:
            pedaco = colado
        if pedaco:
            pedacos.append(pedaco)
    return pedacos


def cai_sob(alvo: str, onde: str, pasta: Path) -> bool:
    alvo = os.path.expanduser(os.path.expandvars(alvo))
    resolvido = os.path.normcase(os.path.normpath(os.path.join(onde, alvo)))
    limite = os.path.normcase(os.path.normpath(str(pasta)))
    return resolvido == limite or resolvido.startswith(limite + os.sep)


def pedido_cai_sob(entrada: dict, raiz: Path, pasta: Path) -> bool:
    onde = str(entrada.get(CHAVE_DO_DIRETORIO) or raiz)
    alvos = alvos_do_pedido(entrada)
    if not alvos:
        return cai_sob(".", onde, pasta)
    return any(cai_sob(alvo, onde, pasta) for alvo in alvos)


def vizinho_do_pedido(entrada: dict, raiz: Path, nomes) -> str:
    for nome in sorted(nomes):
        if pedido_cai_sob(entrada, raiz, raiz / PASTA_DOS_VIZINHOS / nome):
            return nome
    return ""


def rodar_git(pasta: Path, argumentos: list, espera: int) -> str:
    ambiente = dict(os.environ)
    ambiente["GIT_TERMINAL_PROMPT"] = "0"
    try:
        feito = subprocess.run(["git", "-C", str(pasta)] + argumentos,
                               capture_output=True, text=True, timeout=espera,
                               env=ambiente)
    except (OSError, subprocess.SubprocessError):
        return ""
    return feito.stdout.strip() if feito.returncode == 0 else ""


def cabeca_local(pasta: Path) -> tuple:
    dito = rodar_git(pasta, ["log", "-1", "--format=%H %ad", "--date=short"],
                     ESPERA_MAXIMA_DA_REDE_EM_SEGUNDOS)
    if not dito or " " not in dito:
        return "", ""
    sha, data = dito.split(" ", 1)
    return sha.strip(), data.strip()


def ramo_atual(pasta: Path) -> str:
    return rodar_git(pasta, ["rev-parse", "--abbrev-ref", "HEAD"],
                     ESPERA_MAXIMA_DA_REDE_EM_SEGUNDOS)


def ja_baixado_e_nao_usado(pasta: Path, ramo: str) -> tuple:
    referencia = f"origin/{ramo}"
    quantos = rodar_git(pasta, ["rev-list", "--count", f"HEAD..{referencia}"],
                        ESPERA_MAXIMA_DA_REDE_EM_SEGUNDOS)
    if not quantos or quantos == "0":
        return 0, ""
    data = rodar_git(pasta, ["log", "-1", "--format=%ad", "--date=short",
                             referencia], ESPERA_MAXIMA_DA_REDE_EM_SEGUNDOS)
    try:
        return int(quantos), data
    except ValueError:
        return 0, ""


def sha_do_remoto(pasta: Path, ramo: str, temporaria: Path,
                  agora: float) -> str:
    cache = temporaria / f"{PREFIXO_DO_CACHE}{pasta.name}-{ramo}"
    guardado = ler_cache(cache, agora)
    if guardado:
        return guardado
    rede_muda = temporaria / f"{PREFIXO_DA_REDE_MUDA}{pasta.name}-{ramo}"
    if ficou_muda_ha_pouco(rede_muda, agora):
        return ""
    dito = rodar_git(pasta, ["ls-remote", "origin", f"refs/heads/{ramo}"],
                     ESPERA_MAXIMA_DA_REDE_EM_SEGUNDOS)
    sha = dito.split("\t")[0].strip() if dito else ""
    if sha:
        gravar_cache(cache, sha)
    else:
        gravar_cache(rede_muda, str(agora))
    return sha


def ficou_muda_ha_pouco(rede_muda: Path, agora: float) -> bool:
    try:
        quando = float(rede_muda.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    return 0 <= agora - quando < VALIDADE_DA_REDE_MUDA_EM_SEGUNDOS


def ler_cache(cache: Path, agora: float) -> str:
    try:
        idade = agora - cache.stat().st_mtime
        if idade > VALIDADE_DO_CACHE_EM_SEGUNDOS:
            return ""
        return cache.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def gravar_cache(cache: Path, sha: str) -> None:
    try:
        cache.write_text(sha, encoding="utf-8")
    except OSError:
        pass


def ja_avisou(marca: Path) -> bool:
    if marca.exists():
        return True
    try:
        marca.touch()
    except OSError:
        return False
    return False


def texto_do_aviso_de_clone_atrasado(nome: str, sha: str, data: str, sha_remoto: str,
                   atrasados: int, data_do_meio: str, ramo: str) -> str:
    linhas = [LINHA_DA_ARVORE.format(sha=sha[:9], data=data)]
    if atrasados:
        linhas.append(LINHA_DO_MEIO.format(quantos=atrasados,
                                           data=data_do_meio, ramo=ramo))
    linhas.append(LINHA_DO_REMOTO.format(sha=sha_remoto[:9]))
    return AVISO.format(nome=nome, linhas="\n".join(linhas))


def aviso_de_que_nao_mediu(entrada: dict, raiz: Path, sessao: str,
                           temporaria: Path, razao: str) -> str:
    pasta_dos_vizinhos = raiz / PASTA_DOS_VIZINHOS
    if not pasta_dos_vizinhos.is_dir():
        return SEM_AVISO
    if not pedido_cai_sob(entrada, raiz, pasta_dos_vizinhos):
        return SEM_AVISO
    if ja_avisou(temporaria / f"{PREFIXO_DO_NAO_MEDIU}{sessao}"):
        return SEM_AVISO
    return AVISO_DE_QUE_NAO_MEDIU.format(razao=razao)


def decisao(entrada: dict, raiz: Path, agora: float,
            temporaria: Path) -> str:
    sessao = str(entrada.get(CHAVE_DA_SESSAO) or "")
    if not sessao:
        return SEM_AVISO
    nomes, por_que_nao_mediu = vizinhos_somente_leitura_ou_por_que_nao(raiz)
    if por_que_nao_mediu:
        return aviso_de_que_nao_mediu(entrada, raiz, sessao, temporaria,
                                      por_que_nao_mediu)
    nome = vizinho_do_pedido(entrada, raiz, nomes)
    if not nome:
        return SEM_AVISO
    pasta = raiz / PASTA_DOS_VIZINHOS / nome
    if not (pasta / ".git").exists():
        return SEM_AVISO
    marca = temporaria / f"{PREFIXO_DA_MARCA}{sessao}-{nome}"
    if marca.exists():
        return SEM_AVISO
    sha, data = cabeca_local(pasta)
    ramo = ramo_atual(pasta)
    if not sha or not ramo:
        return SEM_AVISO
    remoto = sha_do_remoto(pasta, ramo, temporaria, agora)
    if not remoto or remoto == sha:
        return SEM_AVISO
    if ja_avisou(marca):
        return SEM_AVISO
    atrasados, data_do_meio = ja_baixado_e_nao_usado(pasta, ramo)
    return texto_do_aviso_de_clone_atrasado(nome, sha, data, remoto, atrasados, data_do_meio,
                          ramo)


def vizinhos_avisados(temporaria: Path, sessao: str) -> list:
    if not sessao:
        return []
    inicio = f"{PREFIXO_DA_MARCA}{sessao}-"
    try:
        achados = [marca.name[len(inicio):]
                   for marca in temporaria.glob(f"{inicio}*")]
    except OSError:
        return []
    return sorted(nome for nome in achados if nome)


def em_lista(nomes: list) -> str:
    rotulos = [f"`{nome}`" for nome in nomes]
    if len(rotulos) == 1:
        return rotulos[0]
    return VIRGULA.join(rotulos[:-1]) + E_ENTRE_OS_ULTIMOS + rotulos[-1]


def cobranca_da_parada(entrada: dict, temporaria: Path) -> str:
    sessao = str(entrada.get(CHAVE_DA_SESSAO) or "")
    nomes = vizinhos_avisados(temporaria, sessao)
    if not nomes:
        return SEM_AVISO
    if ja_avisou(temporaria / f"{PREFIXO_DA_COBRANCA}{sessao}"):
        return SEM_AVISO
    return COBRANCA.format(quais=em_lista(nomes))


def aviso_de_que_estourou(falha, temporaria: Path) -> str:
    if ja_avisou(temporaria / f"{PREFIXO_DO_NAO_MEDIU}{MARCA_DO_ESTOURO}"
                              f"{type(falha).__name__}-"
                              f"{time.strftime(DIA_DA_MARCA)}"):
        return SEM_AVISO
    return AVISO_DE_QUE_ESTOUROU.format(type(falha).__name__, falha)


def main() -> int:
    temporaria = Path(tempfile.gettempdir())
    try:
        entrada = json.load(sys.stdin)
        if not isinstance(entrada, dict):
            return SILENCIO
        if entrada.get(CHAVE_DO_EVENTO) == EVENTO_DE_PARADA:
            cobranca = cobranca_da_parada(entrada, temporaria)
            if cobranca:
                print(json.dumps({CHAVE_DA_SAIDA: {
                    CHAVE_DO_EVENTO_NA_SAIDA: EVENTO_DE_PARADA,
                    CHAVE_DO_CONTEXTO: cobranca,
                }}))
            return SILENCIO
        aviso = decisao(entrada, raiz_do_projeto_nunca_o_cwd(), time.time(),
                        temporaria)
    except Exception as falha:
        aviso = aviso_de_que_estourou(falha, temporaria)
    if aviso:
        print(json.dumps({"systemMessage": aviso}))
    return SILENCIO


def montar_vizinho(raiz: Path, nome: str) -> Path:
    pasta = raiz / PASTA_DOS_VIZINHOS / nome
    (pasta / ".git").mkdir(parents=True)
    return pasta


def executor_com(raiz: Path, nome: str) -> None:
    (raiz / "nucleo").mkdir(parents=True, exist_ok=True)
    (raiz / ARQUIVO_EXECUTOR).write_text(json.dumps({
        "projetos": {
            "vizinho": {"repositorio": nome, "somente_leitura": True},
            "meu": {"repositorio": "meu-proprio", "somente_leitura": False},
        }}), encoding="utf-8")


def pedido(ferramenta: str, campo: str, valor: str, sessao="s1") -> dict:
    return {CHAVE_DA_SESSAO: sessao, CHAVE_DA_FERRAMENTA: ferramenta,
            CHAVE_DA_ENTRADA: {campo: valor}}


def testar() -> int:
    falhas, rodados = [], []

    def caso(rotulo, passou):
        rodados.append(rotulo)
        if not passou:
            falhas.append(rotulo)

    nomes = frozenset({"vizinho-alheio"})
    with tempfile.TemporaryDirectory(prefix="alvo-do-pedido-") as pasta:
        raiz = Path(pasta) / "raiz"
        do_vizinho = raiz / "projetos" / "vizinho-alheio"
        de_outro = raiz / "projetos" / "outro"

        def lido(ferramenta, campo, valor, onde=None):
            entrada = pedido(ferramenta, campo, valor)
            entrada[CHAVE_DO_DIRETORIO] = str(onde or raiz)
            return vizinho_do_pedido(entrada, raiz, nomes)

        caso("o vizinho é reconhecido no caminho absoluto de um Read",
             lido("Read", "file_path", str(do_vizinho / "src" / "a.go"))
             == "vizinho-alheio")
        caso("e no caminho relativo à raiz, no meio de um comando com aspas",
             lido("Bash", "command",
                  "grep -rn x 'projetos/vizinho-alheio/src'")
             == "vizinho-alheio")
        caso("nome que apenas COMEÇA igual não conta, senão o aviso sai no "
             "repositório errado",
             lido("Read", "file_path",
                  "projetos/vizinho-alheio-outro/a.go") == "")
        caso("repositório que não é somente leitura não desperta o aviso",
             lido("Read", "file_path", "projetos/meu-proprio/a.go") == "")
        caso("pedido sem alvo nenhum, fora do vizinho, não desperta o aviso",
             lido("Bash", "command", "git status") == "")
        caso("tema de MESMO NOME dentro de outro projeto não é o vizinho: "
             "o que conta é o alvo cair sob a pasta do vizinho, não o nome "
             "aparecer no caminho",
             lido("Read", "file_path",
                  str(de_outro / "src" / "temas" / "vizinho-alheio" / "a.ts"))
             == "")
        caso("procurar a PALAVRA não é ler o vizinho",
             lido("Bash", "command", "grep -rn vizinho-alheio projetos/outro")
             == "")
        caso("o padrão de uma busca é texto procurado, nunca alvo",
             lido("Grep", "pattern", "projetos/vizinho-alheio") == "")
        caso("pasta de mesmo nome FORA desta raiz não é o vizinho daqui",
             lido("Read", "file_path",
                  str(Path(pasta) / "outra" / "projetos" / "vizinho-alheio"
                      / "a.go")) == "")
        caso("caminho que entra no vizinho e SAI dele não é leitura do "
             "vizinho",
             lido("Read", "file_path",
                  "projetos/vizinho-alheio/../outro/a.go") == "")
        caso("de DENTRO do vizinho, pedido sem alvo explícito é leitura "
             "dele: o diretório de trabalho resolve o que o comando cala",
             lido("Bash", "command", "cat a.go", onde=do_vizinho / "src")
             == "vizinho-alheio")
        raiz_com_espaco = Path(pasta) / "minha raiz"
        alvo_com_espaco = (raiz_com_espaco / "projetos" / "vizinho-alheio"
                           / "a.go")

        def lido_da_raiz_com_espaco(comando):
            entrada = pedido("PowerShell", "command", comando)
            entrada[CHAVE_DO_DIRETORIO] = str(raiz_com_espaco)
            return vizinho_do_pedido(entrada, raiz_com_espaco, nomes)

        caso("caminho entre ASPAS com espaço no meio é um alvo só: partido "
             "no espaço, nenhum dos pedaços cai sob o vizinho e o aviso "
             "emudece justo no caso comum desta máquina",
             lido_da_raiz_com_espaco(f'Get-Content "{alvo_com_espaco}"')
             == "vizinho-alheio")
        caso("caminho colado a uma opção por dois-pontos também é alvo",
             lido("PowerShell", "command",
                  f"Get-Content -Path:{do_vizinho / 'a.go'}")
             == "vizinho-alheio")
        os.environ["ALVO_DA_BANCADA_DO_AVISO"] = str(do_vizinho)
        try:
            caso("variável de ambiente no caminho se expande antes de "
                 "resolver o alvo",
                 lido("Bash", "command",
                      "cat $ALVO_DA_BANCADA_DO_AVISO/src/a.go")
                 == "vizinho-alheio")
        finally:
            del os.environ["ALVO_DA_BANCADA_DO_AVISO"]
        caso("de dentro do vizinho, alvo absoluto de FORA não desperta o "
             "aviso daquele clone",
             lido("Read", "file_path", str(de_outro / "a.go"),
                  onde=do_vizinho) == "")

    caso("os alvos do pedido trazem o caminho de dentro do comando",
         "a/b.go" in alvos_do_pedido(pedido("Bash", "command",
                                            "grep x a/b.go")))
    caso("os alvos do pedido trazem o caminho do Read",
         alvos_do_pedido(pedido("Read", "file_path", "a.go")) == ["a.go"])
    caso("os alvos do pedido trazem o caminho do Grep, que vem em path",
         alvos_do_pedido(pedido("Grep", "path", "aqui")) == ["aqui"])

    with tempfile.TemporaryDirectory(prefix="clone-velho-") as pasta:
        base = Path(pasta)
        raiz = base / "raiz"
        marcas = base / "marcas"
        marcas.mkdir()
        executor_com(raiz, "vizinho-alheio")
        montar_vizinho(raiz, "vizinho-alheio")
        agora = time.time()

        caso("vizinho sem git de verdade não trava o gancho: ele cala em vez "
             "de estourar",
             decisao(pedido("Read", "file_path",
                            str(raiz / "projetos" / "vizinho-alheio" / "a.go")),
                     raiz, agora, marcas) == SEM_AVISO)

        caso("clone cujo estado NÃO se mediu não gasta a marca de uma vez "
             "por sessão: marca que nasce antes da medida cala a segunda "
             "tentativa e faz a parada cobrar um aviso que nunca saiu",
             not list(marcas.glob(f"{PREFIXO_DA_MARCA}*")))

        le_o_vizinho = pedido("Read", "file_path",
                              str(raiz / "projetos" / "vizinho-alheio" / "a"),
                              sessao="s-cega")
        (raiz / ARQUIVO_EXECUTOR).write_text("{ quebrado", encoding="utf-8")
        primeira = decisao(le_o_vizinho, raiz, agora, marcas)
        segunda = decisao(le_o_vizinho, raiz, agora, marcas)
        caso("cadastro de vizinhos ilegível, com a sessão olhando a pasta "
             "dos vizinhos, AVISA que não mediu: calar aqui tem a mesma "
             "cara de não há clone atrasado",
             "NÃO MEDIU" in primeira)
        caso("e o aviso de não mediu sai uma vez por sessão: a primeira "
             "presente, a segunda ausente",
             bool(primeira) and segunda == SEM_AVISO)
        caso("o aviso de não mediu não vira cobrança na parada: nenhum "
             "clone foi lido com atraso provado",
             cobranca_da_parada({CHAVE_DA_SESSAO: "s-cega",
                                 CHAVE_DO_EVENTO: EVENTO_DE_PARADA},
                                marcas) == SEM_AVISO)
        caso("cadastro ilegível SEM olhar vizinho nenhum cala: instalação "
             "virgem não tem cadastro, e avisar a cada sessão dela ensina a "
             "ignorar o aviso",
             decisao(pedido("Read", "file_path", str(raiz / "LEIAME.md"),
                            sessao="s-virgem"), raiz, agora, marcas)
             == SEM_AVISO)

        sem_pasta_de_vizinhos = base / "virgem"
        (sem_pasta_de_vizinhos / "nucleo").mkdir(parents=True)
        caso("instalação SEM pasta de vizinhos cala mesmo quando o texto "
             "procurado tem cara de caminho de vizinho: não há vizinho que "
             "a sessão possa estar lendo",
             decisao(pedido("Bash", "command",
                            "grep 'projetos/futuro/a.go' LEIAME.md",
                            sessao="s-sem-pasta"),
                     sem_pasta_de_vizinhos, agora, marcas) == SEM_AVISO)

        executor_com(raiz, "vizinho-alheio")
        consultas = []
        de_verdade = (globals()["rodar_git"], globals()["cabeca_local"],
                      globals()["ramo_atual"])

        def remoto_mudo(pasta_do_git, argumentos, espera):
            consultas.append(argumentos[0])
            return ""

        globals()["rodar_git"] = remoto_mudo
        globals()["cabeca_local"] = lambda pasta_do_git: ("abc123", "2026-01-01")
        globals()["ramo_atual"] = lambda pasta_do_git: "main"
        try:
            for _ in range(3):
                decisao(pedido("Read", "file_path",
                               str(raiz / "projetos" / "vizinho-alheio" / "a"),
                               sessao="s-rede-muda"), raiz, agora, marcas)
        finally:
            (globals()["rodar_git"], globals()["cabeca_local"],
             globals()["ramo_atual"]) = de_verdade
        caso("remoto que não responde se consulta UMA vez, não a cada "
             "leitura: cada consulta espera a rede, e três leituras "
             "seguidas não podem pagar três esperas",
             consultas.count("ls-remote") == 1)

        irma_de_verdade = CERCA_IRMA
        globals()["CERCA_IRMA"] = "cerca-que-nao-existe.py"
        CACHE_DA_CERCA_IRMA.clear()
        try:
            sem_irma = decisao(
                pedido("Read", "file_path",
                       str(raiz / "projetos" / "vizinho-alheio" / "a"),
                       sessao="s-sem-irma"), raiz, agora, marcas)
        finally:
            globals()["CERCA_IRMA"] = irma_de_verdade
            CACHE_DA_CERCA_IRMA.clear()
        caso("cerca irmã que não carrega AVISA que não mediu, em vez de "
             "virar conjunto vazio calado",
             "NÃO MEDIU" in sem_irma)

        (raiz / ARQUIVO_EXECUTOR).write_text(json.dumps({"projetos": {}}),
                                             encoding="utf-8")
        caso("cadastro LIDO e vazio cala: vazio medido não é falha",
             decisao(pedido("Read", "file_path",
                            str(raiz / "projetos" / "vizinho-alheio" / "a"),
                            sessao="s-vazio"), raiz, agora, marcas)
             == SEM_AVISO)
        executor_com(raiz, "vizinho-alheio")

        sem_sessao = pedido("Read", "file_path", "projetos/vizinho-alheio/a.go")
        sem_sessao[CHAVE_DA_SESSAO] = ""
        caso("pedido sem sessão não avisa: a marca de uma vez por sessão "
             "dependeria de um identificador que não existe",
             decisao(sem_sessao, raiz, agora, marcas) == SEM_AVISO)

        cache = base / "cache-teste"
        cache.mkdir()
        alvo = cache / "sha"
        gravar_cache(alvo, "abc123")
        caso("o cache devolve o sha guardado enquanto vale",
             ler_cache(alvo, time.time()) == "abc123")
        caso("e devolve vazio quando vence, para não congelar uma resposta "
             "de ontem",
             ler_cache(alvo, time.time() + VALIDADE_DO_CACHE_EM_SEGUNDOS
                       + 60) == "")

        marca = base / "marca-unica"
        caso("a primeira passada não encontra marca", ja_avisou(marca) is False)
        caso("e a segunda encontra: o aviso sai uma vez",
             ja_avisou(marca) is True)

    texto = texto_do_aviso_de_clone_atrasado("vizinho-alheio", "1234567890abcdef", "2026-08-05",
                           "fedcba0987654321", 26, "2026-08-17", "main")
    caso("o aviso diz o commit curto da árvore lida", "123456789" in texto)
    caso("o aviso diz a data da árvore lida", "2026-08-05" in texto)
    caso("o aviso denuncia a segunda defasagem, que é a silenciosa",
         "26 commit(s)" in texto and "origin/main" in texto)
    caso("o aviso não bloqueia, e diz isso",
         "NÃO impede a leitura" in texto)
    caso("o aviso cobra a data na conclusão, que é a causa real do erro",
         "de que commit e de que data" in texto)
    caso("o aviso manda conferir só os arquivos que sustentam a conclusão",
         "não o repositório inteiro" in texto)
    caso("o aviso lembra que atualizar o clone é decisão do dono",
         "decisão do dono" in texto)

    sem_meio = texto_do_aviso_de_clone_atrasado("vizinho-alheio", "1234567890abcdef",
                              "2026-08-05", "fedcba0987654321", 0, "", "main")
    caso("sem a segunda defasagem, o aviso não inventa uma",
         "origin/main" not in sem_meio)

    with tempfile.TemporaryDirectory(prefix="parada-") as pasta:
        marcas = Path(pasta)
        parada = {CHAVE_DA_SESSAO: "s9", CHAVE_DO_EVENTO: EVENTO_DE_PARADA}
        caso("sessão que não leu vizinho nenhum não é cobrada na parada",
             cobranca_da_parada(parada, marcas) == SEM_AVISO)

        (marcas / f"{PREFIXO_DA_MARCA}s9-vizinho-alheio").touch()
        dita = cobranca_da_parada(parada, marcas)
        caso("sessão que leu clone atrasado é cobrada na parada", bool(dita))
        caso("e a cobrança nomeia o vizinho lido",
             "`vizinho-alheio`" in dita)
        caso("e cobra exatamente a data, que é o que se perde",
             "de que commit e de que data" in dita)

        caso("a cobrança sai uma vez, não em toda parada da sessão",
             cobranca_da_parada(parada, marcas) == SEM_AVISO)

        (marcas / f"{PREFIXO_DA_MARCA}s9-outro-alheio").touch()
        (marcas / f"{PREFIXO_DA_COBRANCA}s9").unlink()
        duas = cobranca_da_parada(parada, marcas)
        caso("com dois vizinhos lidos, a cobrança nomeia os dois",
             "`outro-alheio`" in duas and "`vizinho-alheio`" in duas)

        de_outra = {CHAVE_DA_SESSAO: "s10", CHAVE_DO_EVENTO: EVENTO_DE_PARADA}
        caso("a marca de uma sessão não cobra a sessão vizinha",
             cobranca_da_parada(de_outra, marcas) == SEM_AVISO)

    caso("a lista de um nome não ganha conectivo",
         em_lista(["um"]) == "`um`")
    caso("a lista de dois nomes liga com e",
         em_lista(["um", "dois"]) == "`um` e `dois`")

    if falhas:
        for falha in falhas:
            print(f"FALHOU: {falha}")
        print(f"FALHOU: {len(falhas)} de {len(rodados)} caso(s)")
        return 1
    print(f"OK: o aviso de clone desatualizado — {len(rodados)} casos")
    return 0


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
