import importlib.util
import io
import contextlib
import json
import re
import sys
import tempfile
from pathlib import Path

CERCA_VIZINHA = "vetar-pergunta-ja-respondida.py"
NOME_DO_MODULO_VIZINHO = "cerca_de_pergunta_ja_respondida"
CACHE_DA_CERCA_VIZINHA = []

CHAVE_DO_TRANSCRIPT = "transcript_path"
CHAVE_DO_LACO = "stop_hook_active"
CHAVE_DA_FALA_FINAL = "last_assistant_message"
FERRAMENTA_DE_PERGUNTA = "AskUserQuestion"
CAUDA_LIDA_DA_FALA = 1500
CAUDA_LIDA_DO_TRANSCRIPT = 2 * 1024 * 1024
FALA_CURTA_DEMAIS = 200
MARCA_DE_AVISO_DO_CLIENTE = "<task-notification>"

SILENCIO = 0
BANDEIRA_DE_TESTE = "--testar"

OFERTA_PRESA_AO_SIM_DO_DONO = re.compile(
    r"[^.?!\n]*(?:\bquer que eu\b"
    r"|\bse (?:voc[eê] )?quiser(?: que)?,? (?:eu|posso)\b"
    r"|\bse preferir,? eu\b"
    r"|\bcom (?:o )?seu sim\b"
    r"|\bdiga se\b"
    r"|\bproponho\b"
    r"|(?:^|(?<=[.!?:]\s))confirma\b(?=[^.?!\n]*\?))[^.?!\n]*\??",
    re.I | re.M)
PERGUNTA_AO_DONO_APONTADA_PARA_OUTRO_LUGAR = re.compile(
    r"[^.?!\n]*\b(?:uma\s+pergunta|perguntas)\b(?:\s+[^\s.?!]+){0,3}?\s+"
    r"(?:(?:n[oa]s?|em|nest[ea]|ness[ea])\s+(?:[^\s.?!]+\s+)?"
    r"(?:coment[aá]rios?|issues?|relatos?)|acima)\b[^.?!\n]*",
    re.I | re.M)
PROPOSTA_DEIXADA_AO_DONO = re.compile(
    r"(?:^|(?<=[.!?:]\s))proposta\b[^.?!\n]*", re.I | re.M)
MARCA_DE_PROPOSTA_NAO_APLICADA = re.compile(
    r"\bn[aã]o\s+(?:apliquei|aplicad[ao]s?)\b", re.I)
BLOCO_DE_CODIGO = re.compile(r"```.*?```|`[^`\n]*`", re.S)
FALA_CITADA = re.compile(r"\"[^\"\n]*\"|“[^”\n]*”|«[^»\n]*»")
ACAO_QUE_NAO_SE_DESFAZ = re.compile(
    r"\bapag\w+|\bremov\w+|\bdelet\w+|\bexclu\w+|\breset\w*|\bfor[cç]\w+"
    r"|\bdestru\w+|\bsobrescr\w+", re.I)

COBRANCA = (
    "A resposta deixou decisão do dono em PROSA: «{frase}». Decisão dele vai "
    "pela ferramenta de pergunta, e a ferramenta não é passe livre. Quatro "
    "condições: só quando necessário, porque o que já está autorizado não "
    "se pergunta e o que dá para medir se mede; a dúvida INVESTIGADA antes, "
    "e a pergunta chega com o que a medição mostrou; prós e contras de cada "
    "opção; e o recomendado primeiro na lista. Nenhuma opção mais curta do "
    "que o pedido real. Se a frase acima não era decisão dele, diga isso em "
    "uma linha e encerre.")
NAO_MEDIU = (
    "A cobrança de pergunta em pendência NÃO MEDIU: {}. Silêncio dela aqui "
    "não quer dizer resposta sem pendência.")
TRANSCRIPT_QUE_NAO_SE_ENTENDEU = (
    "nenhuma linha do fim do transcript se deixou ler como registro da "
    "sessão, então não sei se o turno já usou a ferramenta de pergunta")


class NaoMediu(Exception):
    pass


def cerca_vizinha():
    if CACHE_DA_CERCA_VIZINHA:
        return CACHE_DA_CERCA_VIZINHA[0]
    caminho = Path(__file__).resolve().with_name(CERCA_VIZINHA)
    origem = importlib.util.spec_from_file_location(NOME_DO_MODULO_VIZINHO,
                                                    caminho)
    modulo = importlib.util.module_from_spec(origem)
    origem.loader.exec_module(modulo)
    CACHE_DA_CERCA_VIZINHA.append(modulo)
    return modulo


def cauda_do_transcript(transcript: Path) -> list:
    with transcript.open("rb") as arquivo:
        arquivo.seek(0, 2)
        tamanho = arquivo.tell()
        arquivo.seek(max(0, tamanho - CAUDA_LIDA_DO_TRANSCRIPT))
        bruto = arquivo.read()
    linhas = bruto.decode("utf-8", errors="replace").split("\n")
    return linhas[1:] if tamanho > CAUDA_LIDA_DO_TRANSCRIPT else linhas


def abre_turno_de_gente(dado: dict) -> bool:
    if dado.get("type") != "user" or dado.get("isMeta"):
        return False
    mensagem = dado.get("message")
    conteudo = mensagem.get("content") if isinstance(mensagem, dict) else None
    if isinstance(conteudo, str):
        return MARCA_DE_AVISO_DO_CLIENTE not in conteudo
    if not isinstance(conteudo, list):
        return False
    blocos = [bloco for bloco in conteudo if isinstance(bloco, dict)]
    if any(bloco.get("type") == "tool_result" for bloco in blocos):
        return False
    textos = [str(bloco.get("text", "")) for bloco in blocos
              if bloco.get("type") == "text"]
    if textos and all(MARCA_DE_AVISO_DO_CLIENTE in texto for texto in textos):
        return False
    return bool(blocos)


def registros_da_sessao(linhas: list) -> list:
    registros = []
    for linha in linhas:
        try:
            dado = json.loads(linha)
        except ValueError:
            continue
        if isinstance(dado, dict) and dado.get("type") in ("user",
                                                           "assistant"):
            registros.append(dado)
    return registros


def ultimo_turno(linhas: list) -> tuple:
    registros = registros_da_sessao(linhas)
    if not registros:
        raise NaoMediu(TRANSCRIPT_QUE_NAO_SE_ENTENDEU)
    falas, perguntou = [], False
    for dado in registros:
        if dado.get("isSidechain"):
            continue
        if abre_turno_de_gente(dado):
            falas, perguntou = [], False
            continue
        mensagem = dado.get("message")
        conteudo = mensagem.get("content") if isinstance(mensagem,
                                                         dict) else None
        if dado.get("type") != "assistant" or not isinstance(conteudo, list):
            continue
        textos = [str(bloco.get("text", "")) for bloco in conteudo
                  if isinstance(bloco, dict) and bloco.get("type") == "text"
                  and str(bloco.get("text", "")).strip()]
        if textos:
            falas = textos
        if any(isinstance(bloco, dict) and bloco.get("type") == "tool_use"
               and bloco.get("name") == FERRAMENTA_DE_PERGUNTA
               for bloco in conteudo):
            perguntou = True
    return "\n\n".join(falas), perguntou


def sem_o_que_e_citado(fala: str) -> str:
    return FALA_CITADA.sub(" ", BLOCO_DE_CODIGO.sub(" ", fala))


def ofertas_em_prosa(fala: str) -> list:
    if len(fala) < FALA_CURTA_DEMAIS:
        return []
    cauda = sem_o_que_e_citado(fala)[-CAUDA_LIDA_DA_FALA:]
    formas = [OFERTA_PRESA_AO_SIM_DO_DONO,
              PERGUNTA_AO_DONO_APONTADA_PARA_OUTRO_LUGAR]
    if MARCA_DE_PROPOSTA_NAO_APLICADA.search(cauda):
        formas.append(PROPOSTA_DEIXADA_AO_DONO)
    return [achada.group(0).strip()
            for forma in formas
            for achada in forma.finditer(cauda)
            if achada.group(0).strip()]


def so_pede_o_que_ja_esta_autorizado(oferta: str, permitido: dict) -> bool:
    if ACAO_QUE_NAO_SE_DESFAZ.search(oferta):
        return False
    baixo = oferta.lower()
    citadas = [acao for acao, padroes in cerca_vizinha().ACOES.items()
               if any(re.search(padrao, baixo) for padrao in padroes)]
    return bool(citadas) and all(permitido.get(acao) for acao in citadas)


def autorizacoes_desta_casa() -> dict:
    vizinha = cerca_vizinha()
    return vizinha.autorizacoes(vizinha.raiz_da_camada())


def decisao(entrada: dict, permitido=None) -> str:
    if entrada.get(CHAVE_DO_LACO):
        return ""
    transcript = Path(str(entrada.get(CHAVE_DO_TRANSCRIPT) or ""))
    fala_do_arquivo, perguntou = ultimo_turno(cauda_do_transcript(transcript))
    if perguntou:
        return ""
    do_evento = entrada.get(CHAVE_DA_FALA_FINAL)
    fala = do_evento if isinstance(do_evento, str) and do_evento.strip() \
        else fala_do_arquivo
    ofertas = ofertas_em_prosa(fala)
    if not ofertas:
        return ""
    if permitido is None:
        permitido = autorizacoes_desta_casa()
    pendentes = [oferta for oferta in ofertas
                 if not so_pede_o_que_ja_esta_autorizado(oferta, permitido)]
    if not pendentes:
        return ""
    return COBRANCA.format(frase=pendentes[0])


def main() -> int:
    try:
        entrada = json.load(sys.stdin)
        cobranca = decisao(entrada) if isinstance(entrada, dict) else ""
    except Exception as falha:
        print(json.dumps({"systemMessage": NAO_MEDIU.format(
            "%s: %s" % (type(falha).__name__, falha))}))
        return SILENCIO
    if cobranca:
        print(json.dumps({"decision": "block", "reason": cobranca}))
    return SILENCIO


RELATO_LONGO = "Os cinco painéis dizem agora onde a pessoa está. " * 6
OFERTA = RELATO_LONGO + ("Se quiser, eu reorganizo a página em duas camadas "
                         "antes de você ler.")
FALA_COM_PERGUNTAS_NO_COMENTARIO = RELATO_LONGO + (
    "Espera por você, além do relatório: três perguntas no comentário da "
    "etapa dois. São sobre a cor do alerta, o intervalo de atualização e o "
    "texto do rodapé do painel.")
FALA_COM_PROPOSTA_NAO_APLICADA = RELATO_LONGO + (
    "Proposta da análise de promoção: uma linha no mapa ensinando que um "
    "gancho vivo se edita por subagente com worktree própria quando o agente "
    "não pode escrever em outra. Não apliquei.")


def de_gente(texto):
    return {"type": "user", "message": {"content": texto}}


def do_agente(*blocos, **marcas):
    return dict({"type": "assistant", "message": {"content": list(blocos)}},
                **marcas)


def fala(texto):
    return {"type": "text", "text": texto}


USO_DA_FERRAMENTA = {"type": "tool_use", "name": FERRAMENTA_DE_PERGUNTA}
RESULTADO_DE_FERRAMENTA = {"type": "user", "message": {"content": [
    {"type": "tool_result", "content": "saída"}]}}


def testar() -> int:
    falhas, rodados = [], []

    def caso(rotulo, passou):
        rodados.append(rotulo)
        if not passou:
            falhas.append(rotulo)

    with tempfile.TemporaryDirectory(prefix="pendencia-") as bruta:
        pasta = Path(bruta)
        numero = [0]

        def cobrado(registros, laco=False, commit=True, do_evento=None,
                    cru=None):
            numero[0] += 1
            arquivo = pasta / f"t{numero[0]}.jsonl"
            arquivo.write_text(
                cru if cru is not None
                else "\n".join(json.dumps(r) for r in registros),
                encoding="utf-8")
            entrada = {CHAVE_DO_TRANSCRIPT: str(arquivo),
                       CHAVE_DO_LACO: laco}
            if do_evento is not None:
                entrada[CHAVE_DA_FALA_FINAL] = do_evento
            return decisao(entrada, {"commit": commit})

        def turno(texto, *antes):
            return [de_gente("pedido"), *antes, do_agente(fala(texto))]

        caso("oferta presa ao sim do dono, deixada em prosa, é cobrada",
             "reorganizo a página" in cobrado(turno(OFERTA)))
        caso("a cobrança carrega as quatro condições, senão vira convite a "
             "perguntar tudo",
             all(marca in cobrado(turno(OFERTA))
                 for marca in ("só quando necessário", "INVESTIGADA",
                               "prós e contras", "recomendado")))
        caso("CONTROLE: resposta sem pendência cala — inclusive a lista do "
             "que espera pelo dono, que o briefing manda escrever",
             cobrado(turno(RELATO_LONGO + "O que faltou: nada. Espera por "
                           "você: o pedido de incorporação, quando quiser "
                           "abrir.")) == "")
        caso("CONTROLE: oferta sobre ação que a configuração JÁ autoriza "
             "cala — cobrá-la empurraria a sessão para uma pergunta que a "
             "cerca vizinha recusa, e as duas entrariam em laço",
             cobrado(turno(RELATO_LONGO + "Quer que eu faça o commit dessas "
                           "mudanças?")) == "")
        caso("a autorização vale para TODA forma de oferta que o detector "
             "pega, não só para a que pede licença",
             cobrado(turno(RELATO_LONGO + "Proponho fazer o commit agora."))
             == "" and cobrado(turno(RELATO_LONGO + "Se quiser, eu executo "
                                     "o commit.")) == "")
        caso("e a MESMA oferta é cobrada onde a configuração não autoriza",
             "commit" in cobrado(turno(RELATO_LONGO + "Quer que eu faça o "
                                       "commit dessas mudanças?"),
                                 commit=False))
        caso("oferta autorizada NÃO encobre a outra: ação que não se desfaz "
             "na mesma frase é decisão do dono",
             "apague" in cobrado(turno(RELATO_LONGO + "Quer que eu faça o "
                                       "commit e apague a pasta?")))
        caso("nem encobre a oferta seguinte, em outra frase",
             "reorganizo" in cobrado(turno(
                 RELATO_LONGO + "Quer que eu faça o commit? Se quiser, eu "
                 "reorganizo a página.")))
        caso("turno que JÁ usou a ferramenta de pergunta cala",
             cobrado([de_gente("pedido"), do_agente(USO_DA_FERRAMENTA),
                      RESULTADO_DE_FERRAMENTA, do_agente(fala(OFERTA))])
             == "")
        caso("resultado de ferramenta NÃO abre turno novo: a pergunta feita "
             "antes dele ainda é deste turno",
             cobrado([de_gente("pedido"), do_agente(USO_DA_FERRAMENTA),
                      RESULTADO_DE_FERRAMENTA, RESULTADO_DE_FERRAMENTA,
                      do_agente(fala(OFERTA))]) == "")
        caso("pergunta feita num turno ANTIGO não absolve a oferta do turno "
             "que está parando",
             "reorganizo" in cobrado([
                 de_gente("antigo"), do_agente(USO_DA_FERRAMENTA),
                 do_agente(fala("respondido")), *turno(OFERTA)]))
        caso("aviso do cliente e mensagem de sistema não abrem turno: a "
             "pergunta feita antes deles ainda vale",
             cobrado([de_gente("pedido"), do_agente(USO_DA_FERRAMENTA),
                      de_gente(MARCA_DE_AVISO_DO_CLIENTE + " tarefa pronta"),
                      dict(de_gente("lembrete"), isMeta=True),
                      do_agente(fala(OFERTA))]) == "")
        caso("pergunta feita por SUBAGENTE não é pergunta da sessão",
             "reorganizo" in cobrado([
                 de_gente("pedido"),
                 do_agente(USO_DA_FERRAMENTA, isSidechain=True),
                 do_agente(fala(OFERTA))]))
        caso("pedido só com imagem também abre turno: a oferta do turno "
             "anterior não é deste",
             cobrado([*turno(OFERTA),
                      {"type": "user", "message": {"content": [
                          {"type": "image", "source": {}}]}},
                      do_agente({"type": "tool_use", "name": "Read"})]) == "")
        caso("fala final em VÁRIOS blocos se lê inteira: oferta no primeiro "
             "bloco não some porque o segundo veio depois",
             "reorganizo" in cobrado([de_gente("pedido"), do_agente(
                 fala(OFERTA), fala("O que faltou: nada."))]))
        caso("a fala final vem do EVENTO de parada quando ele a traz: o "
             "arquivo pode ainda não ter a resposta",
             "reorganizo" in cobrado(turno("Feito e provado."),
                                     do_evento=OFERTA)
             and cobrado(turno(OFERTA),
                         do_evento=RELATO_LONGO + "Feito e provado.") == "")
        caso("fala CITADA e bloco de código não são oferta da sessão",
             cobrado(turno(RELATO_LONGO + 'O log registra a fala alheia: '
                           '"Quer que eu reorganize a página?" e o molde '
                           '`se quiser, eu faço`.\n```\nQuer que eu rode?'
                           '\n```\nNada mais a relatar.')) == "")
        caso("verbo confirmar no meio de uma frase não é pedido de "
             "confirmação",
             cobrado(turno(RELATO_LONGO + "A medição confirma a hipótese? "
                           "Não, o caso continua sem prova.")) == ""
             and "Confirma" in cobrado(turno(
                 RELATO_LONGO + "Há um arquivo herdado. Confirma o que "
                 "fazer com ele?")))
        caso("pergunta ao dono APONTADA para outro lugar é decisão "
             "pendente, mesmo sem oferta em primeira pessoa",
             "três perguntas no comentário" in cobrado(turno(
                 FALA_COM_PERGUNTAS_NO_COMENTARIO)))
        caso("proposta que a sessão diz não ter aplicado é decisão pendente",
             "Proposta da análise de promoção" in cobrado(turno(
                 FALA_COM_PROPOSTA_NAO_APLICADA)))
        caso("CONTROLE: ação que espera pelo dono não é decisão pendente",
             cobrado(turno(RELATO_LONGO + "Espera por você: o pedido de "
                           "incorporação de develop para main, quando você "
                           "quiser abrir.")) == "")
        caso("CONTROLE: proposta já feita cala, e proposta sem a marca de "
             "não aplicada também",
             cobrado(turno(RELATO_LONGO + "A proposta do portão no servidor "
                           "foi mesclada ontem.")) == ""
             and cobrado(turno(RELATO_LONGO + "Proposta do portão no "
                               "servidor: mesclada ontem.")) == "")
        caso("CONTROLE: pergunta apontada num turno que JÁ usou a ferramenta "
             "de pergunta cala",
             cobrado([de_gente("pedido"), do_agente(USO_DA_FERRAMENTA),
                      RESULTADO_DE_FERRAMENTA,
                      do_agente(fala(FALA_COM_PERGUNTAS_NO_COMENTARIO))])
             == "")
        caso("oferta enterrada no começo de um relato longo fica fora da "
             "cauda lida: o que decide é o fim da resposta",
             cobrado(turno("Se quiser, eu reorganizo a página. "
                           + RELATO_LONGO * 8)) == "")
        caso("laço do próprio gancho cala, senão a cobrança se repete",
             cobrado(turno(OFERTA), laco=True) == "")
        caso("fala curta cala: pergunta de uma linha a gente presente não "
             "é relato com pendência escondida",
             cobrado(turno("Quer que eu rode?")) == "")

        def nao_mediu(cru):
            try:
                cobrado([], cru=cru)
            except NaoMediu:
                return True
            return False

        caso("transcript em formato que não se entende é NÃO MEDIU, nunca "
             "resposta sem pendência",
             nao_mediu("[1, 2, 3]") and nao_mediu("isto nao e jsonl"))

        arquivo = pasta / "pelo-main.jsonl"
        arquivo.write_text("\n".join(json.dumps(r) for r in turno(
            RELATO_LONGO + "Se quiser, eu apago a pasta antiga.")),
            encoding="utf-8")
        dito, guardado = io.StringIO(), sys.stdin
        sys.stdin = io.StringIO(json.dumps({CHAVE_DO_TRANSCRIPT:
                                            str(arquivo)}))
        try:
            with contextlib.redirect_stdout(dito):
                main()
        finally:
            sys.stdin = guardado
        try:
            saiu = json.loads(dito.getvalue())
        except ValueError:
            saiu = {}
        caso("pela porta da frente, o gancho BLOQUEIA a parada com a razão "
             "— provar só a decisão deixa a emissão quebrar sem ninguém ver",
             saiu.get("decision") == "block"
             and "apago a pasta" in saiu.get("reason", ""))

        dito, sys.stdin = io.StringIO(), io.StringIO(json.dumps(
            {CHAVE_DO_TRANSCRIPT: str(pasta / "nao-existe.jsonl")}))
        try:
            with contextlib.redirect_stdout(dito):
                main()
        finally:
            sys.stdin = guardado
        try:
            medido = json.loads(dito.getvalue())
        except ValueError:
            medido = {}
        caso("transcript que não existe sai como NÃO MEDIU, sem bloquear",
             "NÃO MEDIU" in medido.get("systemMessage", "")
             and "block" not in dito.getvalue())

    if falhas:
        for falha in falhas:
            print(f"FALHOU: {falha}")
        print(f"FALHOU: {len(falhas)} de {len(rodados)} caso(s)")
        return 1
    print(f"OK: a cobrança de pergunta em pendência — {len(rodados)} casos")
    return 0


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
