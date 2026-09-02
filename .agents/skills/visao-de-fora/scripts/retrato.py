import argparse
import http.client
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from html import unescape
from pathlib import Path

NAO_MEDIDO = "nao-medido"
AGENTE = "visao-de-fora-retrato/1.0 (coleta publica; uma requisicao por alvo)"
IDIOMA = "pt-BR,pt;q=0.9,en;q=0.5"
TEMPO_LIMITE_S = 25
ESPERA_ENTRE_CHAMADAS_S = 2.0
TETO_DE_LEITURA_BYTES = 2_000_000
PASTA_DE_SAIDA = "dados"
NOME_DO_ARQUIVO = "retrato-{caso}-{data}.json"

FONTE = ("scripts/retrato.py — HTTP sem sessao de navegador, uma requisicao "
         "por alvo, User-Agent declarado. O campo nao-medido e confissao, "
         "nunca zero: ali a coleta manual no navegador de perfil persistente "
         "e a reserva.")
LEITURA_DA_META = ("meta og:description (cache da rede): numero com sufixo "
                   "e aproximado e fica como texto")
LEITURA_JSON_LD = "json-ld aggregateRating"
LEITURA_DO_HTML = "html da pagina"
LEITURA_DO_DOMINIO = "rdap {}; cdx do wayback {}"
LEITURA_HTTP = "HTTP {}"
LEITURA_CORPO_NAO_JSON = "HTTP {} com corpo que nao e JSON"
MOTIVO_REDE = "sem resposta HTTP: {}"
MOTIVO_429 = "HTTP 429: sem nova tentativa (regra 7)"
MOTIVO_HTTP = "HTTP {}"
MOTIVO_BLOQUEIO = ("a resposta e um desafio (CAPTCHA ou Cloudflare), que nao "
                   "se contorna: coleta manual no navegador de perfil "
                   "persistente")
MOTIVO_CASCA = ("HTTP {} com a casca sem os dados: codigo nao prova pagina "
                "viva; coleta manual no navegador")
MOTIVO_SEM_META = ("sem meta legivel: a pagina pediu login ou veio casca; "
                   "coleta manual no navegador")
MOTIVO_SEM_AVALIACAO = "sem aggregateRating legivel no json-ld da pagina"

MARCAS_DE_BLOQUEIO = ("just a moment", "unusual traffic", "/sorry/index",
                      "consent.google")
TITULOS_DE_CASCA = ("google maps", "facebook", "instagram")
MARCAS_DE_CONSTRUTOR_GRATUITO = ("lovable", "wixsite.com", "wordpress.com",
                                 "sites.google.com", "carrd.co", "webnode.",
                                 "canva.site", "godaddysites.com")
ROTULOS_DE_SEGUIDORES = ("followers", "seguidores")
ROTULOS_DE_SEGUINDO = ("following", "seguindo")
ROTULOS_DE_POSTS = ("posts", "publicações", "publicacoes")
ROTULOS_DE_CURTIDAS = ("likes", "curtidas")

INSTAGRAM = "https://www.instagram.com/{}/"
RDAP_BR = "https://rdap.registro.br/domain/{}"
RDAP_GENERICO = "https://rdap.org/domain/{}"
CDX = ("https://web.archive.org/cdx/search/cdx?url={}&output=json"
       "&fl=timestamp,statuscode")
CDX_AMOSTRA = CDX + "&limit=1"
DOMINIO_DE_CONTRAPROVA = "registro.br"
ALVO_ARQUIVADO_DE_CONTRAPROVA = "example.com"
CONTRAPROVA = ("RDAP de {}: HTTP {}; CDX de {}: {} captura(s) na amostra de 1")

CHAVES_DOS_ALVOS = ("negocio", "site", "google", "instagram",
                    "instagram_homonimos", "facebook", "dominios",
                    "agregadores")
ALVO_SEM_NEGOCIO = "alvos sem a chave obrigatoria 'negocio': {}"
ALVO_DESCONHECIDO = "chave desconhecida em alvos: {} — as aceitas: {}"
ALVOS_NAO_SAO_OBJETO = "alvos precisa ser um objeto JSON, veio {}"

CHAVES_DO_RETRATO = (
    "data", "negocio", "fonte",
    "site.url", "site.http", "site.titulo", "site.meta", "site.cta_whatsapp",
    "site.tel_link", "site.gerador", "site.indicio_de_plano_gratuito",
    "site.leitura",
    "google.url", "google.http", "google.titulo", "google.nota",
    "google.avaliacoes", "google.leitura",
    "instagram.handle", "instagram.http", "instagram.posts",
    "instagram.seguidores", "instagram.seguindo", "instagram.texto_da_meta",
    "instagram.leitura",
    "instagram_homonimos[].handle", "instagram_homonimos[].http",
    "instagram_homonimos[].posts", "instagram_homonimos[].seguidores",
    "instagram_homonimos[].seguindo", "instagram_homonimos[].texto_da_meta",
    "instagram_homonimos[].leitura",
    "facebook.pagina", "facebook.http", "facebook.curtidas",
    "facebook.seguidores", "facebook.texto_da_meta", "facebook.leitura",
    "dominios.<dominio>.rdap", "dominios.<dominio>.criado",
    "dominios.<dominio>.expira", "dominios.<dominio>.titular",
    "dominios.<dominio>.ns", "dominios.<dominio>.registro_A",
    "dominios.<dominio>.wayback_capturas",
    "dominios.<dominio>.wayback_periodo", "dominios.<dominio>.leitura",
    "dominios.contraprova_positiva",
    "agregadores.<nome>.url", "agregadores.<nome>.http",
    "agregadores.<nome>.titulo", "agregadores.<nome>.nota",
    "agregadores.<nome>.avaliacoes", "agregadores.<nome>.leitura",
)
CHAVES_COM_FILHOS_MASCARADOS = {"dominios": "<dominio>", "agregadores": "<nome>"}
FILHOS_QUE_NAO_SE_MASCARAM = ("contraprova_positiva",)

META = re.compile(r"<meta\b([^>]*)>", re.I)
ATRIBUTO = re.compile(r"""([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")
TITULO = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
HREF = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.I)
JSON_LD = re.compile(
    r"""<script[^>]+type\s*=\s*["']application/ld\+json["'][^>]*>(.*?)</script>""",
    re.I | re.S)
WHATSAPP = ("wa.me/", "api.whatsapp.com/", "whatsapp://", "web.whatsapp.com/")
TELEFONE = "tel:"
SUFIXO_APROXIMADO = r"(?:[KMkm]\b|mil\b|mi\b)?"


class Coletor:
    def __init__(self, espera=ESPERA_ENTRE_CHAMADAS_S, contato=None):
        self.espera = espera
        self.agente = AGENTE if not contato else f"{AGENTE}; contato: {contato}"
        self.chamadas = 0

    def buscar(self, url):
        if self.chamadas:
            time.sleep(self.espera)
        self.chamadas += 1
        try:
            return self.requisitar(url)
        except (OSError, http.client.HTTPException, ValueError) as erro:
            return {"url": url, "http": None, "url_final": url, "corpo": "",
                    "erro": str(getattr(erro, "reason", erro))}

    def requisitar(self, url):
        pedido = urllib.request.Request(
            url, headers={"User-Agent": self.agente, "Accept-Language": IDIOMA})
        try:
            with urllib.request.urlopen(pedido, timeout=TEMPO_LIMITE_S) as resposta:
                return {"url": url, "http": resposta.status,
                        "url_final": resposta.geturl(),
                        "corpo": decodificar(resposta.read(TETO_DE_LEITURA_BYTES))}
        except urllib.error.HTTPError as erro:
            return {"url": url, "http": erro.code, "url_final": url,
                    "corpo": decodificar(erro.read(TETO_DE_LEITURA_BYTES))}


def decodificar(bruto):
    return bruto.decode("utf-8", errors="replace")


def metas(html):
    achadas = {}
    for bruto in META.findall(html):
        atributos = {nome.lower(): unescape(duplas or simples)
                     for nome, duplas, simples in ATRIBUTO.findall(bruto)}
        chave = (atributos.get("property") or atributos.get("name")
                 or atributos.get("itemprop"))
        if chave and "content" in atributos and chave not in achadas:
            achadas[chave] = atributos["content"]
    return achadas


def titulo(html):
    achado = TITULO.search(html)
    return " ".join(unescape(achado.group(1)).split()) if achado else None


def inteiro_exato(texto):
    if texto is None:
        return None
    limpo = texto.strip().replace(".", "").replace(",", "")
    return int(limpo) if limpo.isdigit() else None


def contagem_rotulada(texto, rotulos):
    numero = r"(\d(?:[\d.,]*\d)?\s*" + SUFIXO_APROXIMADO + r")"
    rotulo = r"(?:" + "|".join(rotulos) + r")"
    numero_antes = re.compile(numero + r"\s*" + rotulo + r"\b", re.I)
    rotulo_antes = re.compile(r"\b" + rotulo + r"\s+" + numero, re.I)
    achado = numero_antes.search(texto or "") or rotulo_antes.search(texto or "")
    if not achado:
        return None
    bruto = " ".join(achado.group(1).split())
    exato = inteiro_exato(bruto)
    return bruto if exato is None else exato


def motivo_de_nao_leitura(resposta):
    if resposta["http"] is None:
        return MOTIVO_REDE.format(resposta.get("erro", "?"))
    if resposta["http"] == 429:
        return MOTIVO_429
    corpo = resposta["corpo"].lower()
    if any(marca in corpo for marca in MARCAS_DE_BLOQUEIO):
        return MOTIVO_BLOQUEIO
    if resposta["http"] >= 400:
        return MOTIVO_HTTP.format(resposta["http"])
    if (titulo(resposta["corpo"]) or "").lower() in TITULOS_DE_CASCA:
        return MOTIVO_CASCA.format(resposta["http"])
    return None


def perfil_de_rede(resposta, rotulos_por_campo):
    perfil = {"http": resposta["http"]}
    perfil.update({campo: NAO_MEDIDO for campo in rotulos_por_campo})
    perfil["texto_da_meta"] = None
    motivo = motivo_de_nao_leitura(resposta)
    descricao = metas(resposta["corpo"]).get("og:description") if not motivo else None
    if descricao is None:
        perfil["leitura"] = motivo or MOTIVO_SEM_META
        return perfil
    for campo, rotulos in rotulos_por_campo.items():
        lido = contagem_rotulada(descricao, rotulos)
        perfil[campo] = NAO_MEDIDO if lido is None else lido
    perfil["texto_da_meta"] = descricao
    perfil["leitura"] = LEITURA_DA_META
    return perfil


def ler_instagram(handle, resposta):
    perfil = {"handle": handle}
    perfil.update(perfil_de_rede(resposta, {
        "posts": ROTULOS_DE_POSTS, "seguidores": ROTULOS_DE_SEGUIDORES,
        "seguindo": ROTULOS_DE_SEGUINDO}))
    return perfil


def ler_facebook(pagina, resposta):
    perfil = {"pagina": pagina}
    perfil.update(perfil_de_rede(resposta, {
        "curtidas": ROTULOS_DE_CURTIDAS, "seguidores": ROTULOS_DE_SEGUIDORES}))
    return perfil


def primeiro_link(html, prefixos):
    for link in HREF.findall(html):
        if any(prefixo in link.lower() for prefixo in prefixos):
            return unescape(link)
    return None


def indicio_de_plano_gratuito(html):
    minusculo = html.lower()
    return next((marca for marca in MARCAS_DE_CONSTRUTOR_GRATUITO
                 if marca in minusculo), None)


def ler_site(url, resposta):
    site = {"url": url, "http": resposta["http"], "titulo": NAO_MEDIDO,
            "meta": NAO_MEDIDO, "cta_whatsapp": NAO_MEDIDO,
            "tel_link": NAO_MEDIDO, "gerador": NAO_MEDIDO,
            "indicio_de_plano_gratuito": NAO_MEDIDO}
    motivo = motivo_de_nao_leitura(resposta)
    if motivo:
        site["leitura"] = motivo
        return site
    html = resposta["corpo"]
    lidas = metas(html)
    site.update({
        "titulo": titulo(html), "meta": lidas.get("description"),
        "cta_whatsapp": primeiro_link(html, WHATSAPP),
        "tel_link": primeiro_link(html, (TELEFONE,)),
        "gerador": lidas.get("generator"),
        "indicio_de_plano_gratuito": indicio_de_plano_gratuito(html),
        "leitura": LEITURA_DO_HTML})
    return site


def blocos_json_ld(html):
    blocos = []
    for bruto in JSON_LD.findall(html):
        try:
            blocos.append(json.loads(bruto.strip()))
        except json.JSONDecodeError:
            continue
    return blocos


def nota_decimal(valor):
    if valor is None:
        return None
    try:
        return float(str(valor).replace(",", "."))
    except ValueError:
        return None


def avaliacao_agregada_em(dado):
    if isinstance(dado, dict):
        agregada = dado.get("aggregateRating")
        nota = nota_decimal(agregada.get("ratingValue")) if isinstance(agregada, dict) else None
        if nota is not None:
            contagem = agregada.get("reviewCount", agregada.get("ratingCount"))
            return nota, contagem_inteira(contagem)
        dado = list(dado.values())
    if isinstance(dado, list):
        for item in dado:
            achado = avaliacao_agregada_em(item)
            if achado:
                return achado
    return None


def contagem_inteira(contagem):
    if isinstance(contagem, bool) or contagem is None:
        return None
    if isinstance(contagem, (int, float)):
        return int(contagem) if float(contagem).is_integer() else None
    return inteiro_exato(str(contagem))


def avaliacao_agregada(html):
    return avaliacao_agregada_em(blocos_json_ld(html))


def ler_ficha(url, resposta):
    ficha = {"url": url, "http": resposta["http"],
             "titulo": titulo(resposta["corpo"]) if resposta["corpo"] else None,
             "nota": NAO_MEDIDO, "avaliacoes": NAO_MEDIDO}
    motivo = motivo_de_nao_leitura(resposta)
    avaliacao = avaliacao_agregada(resposta["corpo"]) if not motivo else None
    if avaliacao is None:
        ficha["leitura"] = motivo or MOTIVO_SEM_AVALIACAO
        return ficha
    ficha["nota"], ficha["avaliacoes"] = avaliacao
    ficha["avaliacoes"] = NAO_MEDIDO if ficha["avaliacoes"] is None else ficha["avaliacoes"]
    ficha["leitura"] = LEITURA_JSON_LD
    return ficha


def endereco_do_rdap(dominio):
    return (RDAP_BR if dominio.lower().endswith(".br") else RDAP_GENERICO).format(dominio)


def tipo_do_titular(rdap):
    for entidade in rdap.get("entities", []):
        if "registrant" in entidade.get("roles", []):
            tipos = [p.get("type", "").lower() for p in entidade.get("publicIds", [])]
            return tipos[0] if tipos else NAO_MEDIDO
    return NAO_MEDIDO


def data_do_evento(rdap, acao):
    return next((e.get("eventDate", "")[:10] for e in rdap.get("events", [])
                 if e.get("eventAction") == acao), None)


def json_do_corpo(resposta, tipo):
    if resposta["http"] != 200:
        return None
    try:
        dado = json.loads(resposta["corpo"])
    except json.JSONDecodeError:
        return None
    return dado if isinstance(dado, tipo) else None


def leitura_de_json(resposta, lido):
    ilegivel = resposta["http"] == 200 and lido == NAO_MEDIDO
    return (LEITURA_CORPO_NAO_JSON if ilegivel else LEITURA_HTTP).format(resposta["http"])


def ler_rdap(resposta):
    registro = {"rdap": resposta["http"], "criado": None, "expira": None,
                "titular": None, "ns": None}
    if resposta["http"] == 404:
        return registro
    rdap = json_do_corpo(resposta, dict)
    if rdap is None:
        registro.update({"criado": NAO_MEDIDO, "expira": NAO_MEDIDO,
                         "titular": NAO_MEDIDO, "ns": NAO_MEDIDO})
        return registro
    registro.update({
        "criado": data_do_evento(rdap, "registration"),
        "expira": data_do_evento(rdap, "expiration"),
        "titular": tipo_do_titular(rdap),
        "ns": ", ".join(sorted(n.get("ldhName", "") for n in rdap.get("nameservers", [])))})
    return registro


def data_do_carimbo(carimbo):
    return f"{carimbo[:4]}-{carimbo[4:6]}-{carimbo[6:8]}"


def linhas_do_cdx(resposta):
    if resposta["http"] == 200 and not resposta["corpo"].strip():
        return []
    return json_do_corpo(resposta, list)


def ler_wayback(resposta):
    linhas = linhas_do_cdx(resposta)
    if linhas is None:
        return {"wayback_capturas": NAO_MEDIDO, "wayback_periodo": NAO_MEDIDO}
    capturas = linhas[1:]
    if not capturas:
        return {"wayback_capturas": 0, "wayback_periodo": None}
    return {"wayback_capturas": len(capturas),
            "wayback_periodo": f"{data_do_carimbo(capturas[0][0])} a "
                               f"{data_do_carimbo(capturas[-1][0])}"}


def registro_a(dominio):
    try:
        return socket.gethostbyname(dominio)
    except socket.gaierror:
        return None


def ler_dominio(dominio, coletor):
    rdap = coletor.buscar(endereco_do_rdap(dominio))
    cdx = coletor.buscar(CDX.format(dominio))
    registro = ler_rdap(rdap)
    registro["registro_A"] = registro_a(dominio)
    registro.update(ler_wayback(cdx))
    registro["leitura"] = LEITURA_DO_DOMINIO.format(
        leitura_de_json(rdap, registro["criado"]),
        leitura_de_json(cdx, registro["wayback_capturas"]))
    return registro


def contraprova_positiva(coletor):
    rdap = coletor.buscar(endereco_do_rdap(DOMINIO_DE_CONTRAPROVA))
    cdx = ler_wayback(coletor.buscar(CDX_AMOSTRA.format(ALVO_ARQUIVADO_DE_CONTRAPROVA)))
    return CONTRAPROVA.format(DOMINIO_DE_CONTRAPROVA, rdap["http"],
                              ALVO_ARQUIVADO_DE_CONTRAPROVA,
                              cdx["wayback_capturas"])


def validar_alvos(alvos):
    if not isinstance(alvos, dict):
        raise SystemExit(ALVOS_NAO_SAO_OBJETO.format(type(alvos).__name__))
    if not alvos.get("negocio"):
        raise SystemExit(ALVO_SEM_NEGOCIO.format(sorted(alvos)))
    for chave in alvos:
        if chave not in CHAVES_DOS_ALVOS:
            raise SystemExit(ALVO_DESCONHECIDO.format(chave, ", ".join(CHAVES_DOS_ALVOS)))
    return alvos


def ler_redes(alvos, coletor, retrato):
    if alvos.get("instagram"):
        handle = alvos["instagram"]
        retrato["instagram"] = ler_instagram(
            handle, coletor.buscar(INSTAGRAM.format(handle)))
    if alvos.get("instagram_homonimos"):
        retrato["instagram_homonimos"] = [
            ler_instagram(h, coletor.buscar(INSTAGRAM.format(h)))
            for h in alvos["instagram_homonimos"]]
    if alvos.get("facebook"):
        retrato["facebook"] = ler_facebook(
            alvos["facebook"], coletor.buscar(alvos["facebook"]))


def ler_dominios_e_agregadores(alvos, coletor, retrato):
    if alvos.get("dominios"):
        retrato["dominios"] = {d: ler_dominio(d, coletor) for d in alvos["dominios"]}
        retrato["dominios"]["contraprova_positiva"] = contraprova_positiva(coletor)
    if alvos.get("agregadores"):
        retrato["agregadores"] = {
            nome: ler_ficha(url, coletor.buscar(url))
            for nome, url in alvos["agregadores"].items()}


def montar_retrato(alvos, coletor, hoje):
    retrato = {"data": hoje, "negocio": alvos["negocio"], "fonte": FONTE}
    if alvos.get("site"):
        retrato["site"] = ler_site(alvos["site"], coletor.buscar(alvos["site"]))
    if alvos.get("google"):
        retrato["google"] = ler_ficha(alvos["google"], coletor.buscar(alvos["google"]))
    ler_redes(alvos, coletor, retrato)
    ler_dominios_e_agregadores(alvos, coletor, retrato)
    return retrato


def caminhos(valor, prefixo="", pai=None):
    if isinstance(valor, dict):
        achados = set()
        for chave, filho in valor.items():
            mascara = CHAVES_COM_FILHOS_MASCARADOS.get(pai)
            nome = mascara if mascara and chave not in FILHOS_QUE_NAO_SE_MASCARAM else chave
            achados |= caminhos(filho, f"{prefixo}{nome}.", chave)
        return achados
    if isinstance(valor, list):
        achados = set()
        for item in valor:
            achados |= caminhos(item, f"{prefixo[:-1]}[].", pai)
        return achados
    return {prefixo[:-1]}


def nome_do_arquivo(caso, hoje):
    return NOME_DO_ARQUIVO.format(caso=caso, data=hoje)


def resumo(retrato):
    for secao in ("site", "google", "instagram", "facebook"):
        if secao in retrato:
            dados = retrato[secao]
            medidos = {k: v for k, v in dados.items()
                       if k in ("titulo", "nota", "avaliacoes", "posts",
                                "seguidores", "seguindo", "curtidas")}
            print(f"{secao}: HTTP {dados['http']} | {medidos} | {dados['leitura']}")
    for dominio, registro in retrato.get("dominios", {}).items():
        if isinstance(registro, dict):
            print(f"dominio {dominio}: rdap {registro['rdap']} | titular "
                  f"{registro['titular']} | wayback {registro['wayback_capturas']}")
    for nome, ficha in retrato.get("agregadores", {}).items():
        print(f"agregador {nome}: HTTP {ficha['http']} | nota {ficha['nota']} | "
              f"{ficha['leitura']}")


FIXTURE_INSTAGRAM = (
    '<html><head><title>Loja Exemplo (@loja.exemplo) • Instagram photos</title>'
    '<meta property="og:description" content="8,574 Followers, 285 Following, '
    '1.234 Posts - See Instagram photos and videos from Loja Exemplo" />'
    '</head></html>')
FIXTURE_INSTAGRAM_PT = (
    '<html><head><title>Loja (@loja) • Instagram</title>'
    '<meta content="49,7 mil seguidores, seguindo 1.764, 650 posts — Veja fotos '
    'de Loja (@loja)" property="og:description"></head></html>')
FIXTURE_LOGIN = '<html><head><title>Instagram</title></head><body>Log in</body></html>'
FIXTURE_FACEBOOK = (
    '<html><head><title>Loja Exemplo | Facebook</title>'
    '<meta property="og:description" content="Loja Exemplo. 12.345 curtidas · '
    '678 seguidores · 9 estiveram aqui. Descricao da loja." /></head></html>')
FIXTURE_SITE = (
    '<html><head><title> Loja &amp; Cia </title>'
    '<meta name="description" content="Projeto gerado pelo construtor">'
    '<meta name="generator" content="Construtor 1.0"></head><body>'
    '<a href="https://wa.me/5500000000000?text=oi">WhatsApp</a>'
    '<a href="tel:+5500000000000">Ligar</a>'
    '<script src="https://cdn.lovable.dev/x.js"></script></body></html>')
FIXTURE_SITE_SEM_CTA = '<html><head><title>Loja</title></head><body>oi</body></html>'
FIXTURE_JSON_LD = (
    '<html><head><title>Loja no Agregador</title>'
    '<script type="application/ld+json">{"@graph": [{"@type": "LocalBusiness", '
    '"aggregateRating": {"@type": "AggregateRating", "ratingValue": "4,7", '
    '"reviewCount": "1.345"}}]}</script></head></html>')
FIXTURE_BLOQUEIO = '<html><head><title>Just a moment...</title></head></html>'
FIXTURE_SITE_COM_RECAPTCHA = (
    '<html><head><title>Loja Viva</title><meta name="description" content="aberta">'
    '</head><body><form><div class="g-recaptcha"></div></form></body></html>')
FIXTURE_JSON_LD_NOTA_ILEGIVEL = (
    '<html><head><title>Loja no Agregador</title><script type="application/ld+json">'
    '{"aggregateRating": {"ratingValue": "4.5/5", "reviewCount": 10}}</script></head></html>')
FIXTURE_HTML_NO_LUGAR_DE_JSON = '<html><body>Service Unavailable</body></html>'
FIXTURE_CASCA_GOOGLE = '<html><head><title> Google Maps </title></head></html>'
FIXTURE_RDAP = {
    "events": [{"eventAction": "registration", "eventDate": "2025-01-14T12:00:00Z"},
               {"eventAction": "expiration", "eventDate": "2030-01-14T12:00:00Z"}],
    "nameservers": [{"ldhName": "ns2.exemplo.net"}, {"ldhName": "ns1.exemplo.net"}],
    "entities": [{"roles": ["registrant"],
                  "publicIds": [{"type": "cnpj", "identifier": "12345678000199"}]}]}
FIXTURE_CDX = [["timestamp", "statuscode"], ["20020120142510", "200"],
               ["20020328012821", "200"], ["20020524041628", "301"]]
FIXTURE_ALVOS = {
    "negocio": "Loja Exemplo", "site": "https://loja.exemplo",
    "google": "https://www.google.com/maps/place/Loja+Exemplo/",
    "instagram": "loja.exemplo", "instagram_homonimos": ["loja_exemplo"],
    "facebook": "https://www.facebook.com/lojaexemplo/",
    "dominios": ["loja.exemplo.br", "loja.exemplo"],
    "agregadores": {"agregador": "https://agregador.exemplo/loja"}}


def resposta_fixa(url, corpo, http=200):
    corpo_texto = corpo if isinstance(corpo, str) else json.dumps(corpo)
    return {"url": url, "http": http, "url_final": url, "corpo": corpo_texto}


class ColetorDeFixtures:
    def __init__(self):
        self.chamadas = {}

    def buscar(self, url):
        self.chamadas[url] = self.chamadas.get(url, 0) + 1
        if "instagram.com" in url:
            return resposta_fixa(url, FIXTURE_INSTAGRAM)
        if "facebook.com" in url:
            return resposta_fixa(url, FIXTURE_FACEBOOK)
        if "google.com" in url:
            return resposta_fixa(url, FIXTURE_CASCA_GOOGLE)
        if "rdap" in url:
            return resposta_fixa(url, FIXTURE_RDAP)
        if "web.archive.org" in url:
            return resposta_fixa(url, FIXTURE_CDX)
        if "agregador" in url:
            return resposta_fixa(url, FIXTURE_JSON_LD)
        return resposta_fixa(url, FIXTURE_SITE)


class ColetorQueSoDevolveHtml:
    def buscar(self, url):
        return resposta_fixa(url, FIXTURE_HTML_NO_LUGAR_DE_JSON)


class ColetorCortadoNoMeioDoCorpo(Coletor):
    def requisitar(self, url):
        raise http.client.IncompleteRead(b"metade")


def recusa(funcao, *argumentos):
    try:
        funcao(*argumentos)
    except SystemExit:
        return True
    return False


def testar_parsers(caso):
    lidas = metas(FIXTURE_SITE)
    caso("metas le name e generator sem depender da ordem dos atributos",
         lidas["description"] == "Projeto gerado pelo construtor"
         and lidas["generator"] == "Construtor 1.0")
    caso("titulo desfaz entidade e apara espaco", titulo(FIXTURE_SITE) == "Loja & Cia")
    caso("inteiro exato aceita separador de milhar e recusa sufixo",
         (inteiro_exato("8,574"), inteiro_exato("1.345"), inteiro_exato("49,7 mil"),
          inteiro_exato("686M")) == (8574, 1345, None, None))
    ig = ler_instagram("loja.exemplo", resposta_fixa("u", FIXTURE_INSTAGRAM))
    caso("instagram le posts, seguidores e seguindo da meta em ingles",
         (ig["posts"], ig["seguidores"], ig["seguindo"]) == (1234, 8574, 285)
         and ig["leitura"] == LEITURA_DA_META and ig["handle"] == "loja.exemplo")
    ig_pt = ler_instagram("loja", resposta_fixa("u", FIXTURE_INSTAGRAM_PT))
    caso("instagram em portugues guarda o aproximado como texto e o exato como numero",
         (ig_pt["seguidores"], ig_pt["posts"]) == ("49,7 mil", 650))
    caso("instagram em portugues le seguindo com o rotulo antes do numero, sem a virgula",
         ig_pt["seguindo"] == 1764)
    caso("contagem rotulada nao confunde o rotulo vizinho com o numero do outro",
         contagem_rotulada("8 seguidores, seguindo 3, 2 posts", ROTULOS_DE_SEGUIDORES) == 8
         and contagem_rotulada("8 seguidores, seguindo 3, 2 posts", ROTULOS_DE_POSTS) == 2)
    ig_login = ler_instagram("x", resposta_fixa("u", FIXTURE_LOGIN))
    caso("instagram atras de login confessa nao-medido, nunca zero",
         ig_login["seguidores"] == NAO_MEDIDO and ig_login["leitura"].startswith("HTTP 200"))
    fb = ler_facebook("pagina", resposta_fixa("u", FIXTURE_FACEBOOK))
    caso("facebook le curtidas e seguidores da meta",
         (fb["curtidas"], fb["seguidores"]) == (12345, 678))
    site = ler_site("https://loja.exemplo", resposta_fixa("u", FIXTURE_SITE))
    caso("site le titulo, meta, cta de whatsapp, tel e indicio de construtor",
         site["titulo"] == "Loja & Cia" and site["cta_whatsapp"].startswith("https://wa.me/")
         and site["tel_link"] == "tel:+5500000000000" and site["gerador"] == "Construtor 1.0"
         and site["indicio_de_plano_gratuito"] == "lovable")
    vazio = ler_site("u", resposta_fixa("u", FIXTURE_SITE_SEM_CTA))
    caso("site sem cta devolve nulo, e nao nao-medido",
         vazio["cta_whatsapp"] is None and vazio["tel_link"] is None
         and vazio["indicio_de_plano_gratuito"] is None)
    caso("json-ld aninhado em @graph rende nota e volume",
         avaliacao_agregada(FIXTURE_JSON_LD) == (4.7, 1345))
    vivo = ler_site("u", resposta_fixa("u", FIXTURE_SITE_COM_RECAPTCHA))
    caso("site vivo com formulario recaptcha e lido, nao tomado por desafio",
         vivo["titulo"] == "Loja Viva" and vivo["leitura"] == LEITURA_DO_HTML)


def testar_fichas_e_registros(caso):
    ficha = ler_ficha("u", resposta_fixa("u", FIXTURE_JSON_LD))
    caso("ficha com json-ld le nota e avaliacoes",
         (ficha["nota"], ficha["avaliacoes"], ficha["leitura"]) == (4.7, 1345, LEITURA_JSON_LD))
    bloqueada = ler_ficha("u", resposta_fixa("u", FIXTURE_BLOQUEIO))
    caso("desafio de cloudflare vira nao-medido com o motivo, sem contorno",
         bloqueada["nota"] == NAO_MEDIDO and bloqueada["leitura"] == MOTIVO_BLOQUEIO)
    casca = ler_ficha("u", resposta_fixa("u", FIXTURE_CASCA_GOOGLE))
    caso("casca do google com HTTP 200 nao prova pagina viva",
         casca["nota"] == NAO_MEDIDO and casca["leitura"] == MOTIVO_CASCA.format(200))
    sem_rede = ler_ficha("u", {"url": "u", "http": None, "url_final": "u",
                               "corpo": "", "erro": "timed out"})
    caso("falha de rede vira nao-medido com o erro nomeado",
         sem_rede["leitura"] == MOTIVO_REDE.format("timed out"))
    caso("HTTP 429 vira nao-medido sem nova tentativa",
         ler_ficha("u", resposta_fixa("u", "", 429))["leitura"] == MOTIVO_429)
    caso("desafio servido com HTTP 503 e bloqueio, nao HTTP generico",
         ler_ficha("u", resposta_fixa("u", FIXTURE_BLOQUEIO, 503))["leitura"] == MOTIVO_BLOQUEIO)
    sem_esquema = Coletor(espera=0).buscar("facebook.com/loja")
    caso("alvo sem esquema vira resposta sem HTTP com o erro nomeado, antes de qualquer rede",
         sem_esquema["http"] is None and "unknown url type" in sem_esquema["erro"])
    cortado = ColetorCortadoNoMeioDoCorpo(espera=0).buscar("https://loja.exemplo")
    caso("corpo cortado no meio da leitura vira resposta sem HTTP, nao excecao",
         cortado["http"] is None and cortado["erro"].startswith("IncompleteRead"))
    nota_ilegivel = ler_ficha("u", resposta_fixa("u", FIXTURE_JSON_LD_NOTA_ILEGIVEL))
    caso("ratingValue que nao e numero vira sem avaliacao legivel, sem excecao",
         avaliacao_agregada_em({"aggregateRating": {"ratingValue": "", "reviewCount": 10}}) is None
         and nota_ilegivel["nota"] == NAO_MEDIDO
         and nota_ilegivel["leitura"] == MOTIVO_SEM_AVALIACAO)
    caso("contagem numerica do json-ld vira inteiro direto: 10.0 e 10, nunca 100",
         avaliacao_agregada_em({"aggregateRating": {"ratingValue": "4.5", "reviewCount": 10.0}}) == (4.5, 10)
         and avaliacao_agregada_em({"aggregateRating": {"ratingValue": "4.5", "reviewCount": "1.345"}}) == (4.5, 1345)
         and avaliacao_agregada_em({"aggregateRating": {"ratingValue": "4.5", "reviewCount": 10.5}}) == (4.5, None))
    registro = ler_rdap(resposta_fixa("u", FIXTURE_RDAP))
    caso("rdap le criacao, expiracao, tipo do titular e nameservers ordenados",
         (registro["criado"], registro["expira"], registro["titular"], registro["ns"])
         == ("2025-01-14", "2030-01-14", "cnpj", "ns1.exemplo.net, ns2.exemplo.net"))
    caso("rdap nunca copia o identificador do titular",
         "12345678000199" not in json.dumps(registro))
    livre = ler_rdap(resposta_fixa("u", "", 404))
    caso("rdap 404 e dominio livre: campos nulos, nao nao-medido",
         livre["rdap"] == 404 and livre["criado"] is None and livre["titular"] is None)
    caso("rdap fora do ar confessa nao-medido",
         ler_rdap(resposta_fixa("u", "", 503))["criado"] == NAO_MEDIDO)
    caso("rdap com HTTP 200 e corpo que nao e JSON confessa nao-medido, sem excecao",
         ler_rdap(resposta_fixa("u", FIXTURE_HTML_NO_LUGAR_DE_JSON))["criado"] == NAO_MEDIDO)
    caso("wayback com HTTP 200 e corpo que nao e JSON confessa nao-medido, sem excecao",
         ler_wayback(resposta_fixa("u", FIXTURE_HTML_NO_LUGAR_DE_JSON))["wayback_capturas"] == NAO_MEDIDO)
    caso("wayback conta capturas e data o periodo",
         ler_wayback(resposta_fixa("u", FIXTURE_CDX))
         == {"wayback_capturas": 3, "wayback_periodo": "2002-01-20 a 2002-05-24"})
    caso("wayback vazio e zero com periodo nulo; sem resposta e nao-medido",
         ler_wayback(resposta_fixa("u", "")) == {"wayback_capturas": 0, "wayback_periodo": None}
         and ler_wayback(resposta_fixa("u", "", 503))["wayback_capturas"] == NAO_MEDIDO)
    caso("rdap de .br vai ao registro.br e o resto ao rdap.org",
         endereco_do_rdap("loja.exemplo.br").startswith("https://rdap.registro.br/")
         and endereco_do_rdap("loja.exemplo").startswith("https://rdap.org/"))


def testar_retrato(caso):
    caso("alvos sem negocio, com chave desconhecida ou fora de objeto sao recusados",
         recusa(validar_alvos, {"site": "x"}) and recusa(validar_alvos, {"negocio": "x", "sitio": "y"})
         and recusa(validar_alvos, ["negocio"]) and validar_alvos(FIXTURE_ALVOS) is FIXTURE_ALVOS)
    coletor = ColetorDeFixtures()
    retrato = montar_retrato(FIXTURE_ALVOS, coletor, "2026-09-01")
    caso("o retrato completo tem exatamente as chaves declaradas",
         caminhos(retrato) == set(CHAVES_DO_RETRATO))
    caso("cada alvo recebe uma requisicao, e a contraprova entra uma vez",
         all(n == 1 for n in coletor.chamadas.values())
         and any(DOMINIO_DE_CONTRAPROVA in u for u in coletor.chamadas)
         and any(ALVO_ARQUIVADO_DE_CONTRAPROVA in u for u in coletor.chamadas))
    caso("o retrato e datado e cita a fonte",
         retrato["data"] == "2026-09-01" and retrato["fonte"] == FONTE)
    caso("a leitura do dominio registra o HTTP do rdap e o do wayback",
         retrato["dominios"]["loja.exemplo.br"]["leitura"] == "rdap HTTP 200; cdx do wayback HTTP 200")
    ilegivel = ler_dominio("loja.exemplo", ColetorQueSoDevolveHtml())
    caso("dominio com rdap e cdx ilegiveis confessa nao-medido e diz o motivo na leitura",
         ilegivel["criado"] == NAO_MEDIDO and ilegivel["wayback_capturas"] == NAO_MEDIDO
         and ilegivel["leitura"] == "rdap HTTP 200 com corpo que nao e JSON; "
                                    "cdx do wayback HTTP 200 com corpo que nao e JSON")
    caso("dominio e nome de agregador sao mascarados no caminho da forma",
         "dominios.<dominio>.rdap" in caminhos(retrato)
         and "agregadores.<nome>.nota" in caminhos(retrato)
         and "dominios.contraprova_positiva" in caminhos(retrato))
    caso("o nome do arquivo segue o padrao dos retratos manuais",
         nome_do_arquivo("exemplo", "2026-09-01") == "retrato-exemplo-2026-09-01.json")
    caso("o retrato pode ir a json sem valor que nao se serialize",
         json.dumps(retrato, ensure_ascii=False))


def testar():
    casos, falhas = [], []

    def caso(nome, deu_certo):
        casos.append(nome)
        if not deu_certo:
            falhas.append(nome)

    testar_parsers(caso)
    testar_fichas_e_registros(caso)
    testar_retrato(caso)
    for nome in falhas:
        print(f"CAIU: {nome}")
    if falhas:
        print(f"FALHOU: {len(falhas)} de {len(casos)} casos")
        return 1
    print(f"OK: {len(casos)} casos")
    return 0


def imprimir_forma(arquivo):
    with open(arquivo, encoding="utf-8") as origem:
        for caminho in sorted(caminhos(json.load(origem))):
            print(caminho)


def principal():
    if "--testar" in sys.argv[1:]:
        return testar()
    parser = argparse.ArgumentParser(
        description="Retrato datado da vitrine digital de um negocio, por HTTP "
                    "sem sessao de navegador: site, ficha do Google, redes, "
                    "dominios e agregadores. O que nao se le vira nao-medido.")
    parser.add_argument("--alvos", help="JSON com negocio, site, google, instagram, "
                                        "instagram_homonimos, facebook, dominios, agregadores")
    parser.add_argument("--caso", help="nome do caso, vai no nome do arquivo")
    parser.add_argument("--saida-dir", default=PASTA_DE_SAIDA)
    parser.add_argument("--espera", type=float, default=ESPERA_ENTRE_CHAMADAS_S,
                        help="segundos entre requisicoes")
    parser.add_argument("--contato", help="vai no User-Agent, para quem quiser falar")
    parser.add_argument("--forma", metavar="RETRATO.json",
                        help="imprime so as chaves de um retrato, sem valor nenhum")
    args = parser.parse_args()
    if args.forma:
        imprimir_forma(args.forma)
        return 0
    if not args.alvos or not args.caso:
        parser.error("--alvos e --caso sao obrigatorios (ou use --forma)")
    with open(args.alvos, encoding="utf-8") as origem:
        alvos = validar_alvos(json.load(origem))
    hoje = date.today().isoformat()
    retrato = montar_retrato(alvos, Coletor(args.espera, args.contato), hoje)
    destino = Path(args.saida_dir) / nome_do_arquivo(args.caso, hoje)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8") as saida:
        json.dump(retrato, saida, ensure_ascii=False, indent=1)
    resumo(retrato)
    print(f"gravado: {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
