import argparse
import json
import math
import sys

ALFABETO = "23456789CFGHJMPQRVWX"
BASE = len(ALFABETO)
SEPARADOR = "+"
POSICAO_DO_SEPARADOR = 8
PREENCHIMENTO = "0"
DIGITOS_EM_PARES = 10
DIGITOS_NO_MAXIMO = 15
COMPRIMENTO_PADRAO = 10
COMPRIMENTO_DA_IDA_E_VOLTA = 11
LINHAS_DA_GRADE = 5
COLUNAS_DA_GRADE = 4
PRECISAO_DOS_PARES = BASE ** 3
PRIMEIRO_VALOR_DE_PAR = BASE ** 4
PRECISAO_FINAL_DA_LATITUDE = PRECISAO_DOS_PARES * LINHAS_DA_GRADE ** 5
PRECISAO_FINAL_DA_LONGITUDE = PRECISAO_DOS_PARES * COLUNAS_DA_GRADE ** 5
LATITUDE_MAXIMA = 90
LONGITUDE_MAXIMA = 180
METROS_POR_GRAU = 111_320.0
ERRO_MAXIMO_DA_IDA_E_VOLTA_M = 5.0
CODIGO_INVALIDO = "Plus Code inválido: {!r} — caractere fora do alfabeto ou separador fora do lugar"
COMPRIMENTO_INVALIDO = "comprimento inválido: {} — use 2, 4, 6, 8, 10 ou de 11 a 15"
CURTO_SEM_REFERENCIA = ("código curto ({}) precisa de --referencia LAT LON: "
                        "o centro do município que o geocodificador devolveu serve")


def normalizar_longitude(lon):
    while lon < -LONGITUDE_MAXIMA:
        lon += 2 * LONGITUDE_MAXIMA
    while lon >= LONGITUDE_MAXIMA:
        lon -= 2 * LONGITUDE_MAXIMA
    return lon


def limitar_latitude(lat):
    return min(max(lat, -LATITUDE_MAXIMA), LATITUDE_MAXIMA)


def e_valido(codigo):
    if not codigo or codigo.count(SEPARADOR) != 1:
        return False
    posicao = codigo.find(SEPARADOR)
    if posicao > POSICAO_DO_SEPARADOR or posicao % 2 == 1:
        return False
    if len(codigo) - posicao - 1 == 1:
        return False
    corpo = codigo.upper().replace(SEPARADOR, "")
    if not corpo:
        return False
    preenchido = corpo.rstrip(PREENCHIMENTO) if PREENCHIMENTO in corpo else corpo
    if PREENCHIMENTO in corpo:
        if posicao < POSICAO_DO_SEPARADOR or corpo.find(PREENCHIMENTO) < 2:
            return False
        if len(preenchido) % 2 == 1 or codigo.rstrip(SEPARADOR) != codigo[:-1]:
            return False
    return all(c in ALFABETO for c in preenchido)


def e_completo(codigo):
    return e_valido(codigo) and codigo.find(SEPARADOR) == POSICAO_DO_SEPARADOR


def codificar(lat, lon, comprimento=COMPRIMENTO_PADRAO):
    if comprimento < 2 or (comprimento < DIGITOS_EM_PARES and comprimento % 2 == 1):
        raise ValueError(COMPRIMENTO_INVALIDO.format(comprimento))
    comprimento = min(comprimento, DIGITOS_NO_MAXIMO)
    amplitude_da_latitude = 2 * LATITUDE_MAXIMA * PRECISAO_FINAL_DA_LATITUDE
    amplitude_da_longitude = 2 * LONGITUDE_MAXIMA * PRECISAO_FINAL_DA_LONGITUDE
    valor_lat = int(round(lat * PRECISAO_FINAL_DA_LATITUDE)) + amplitude_da_latitude // 2
    valor_lat = min(max(valor_lat, 0), amplitude_da_latitude - 1)
    valor_lon = int(round(lon * PRECISAO_FINAL_DA_LONGITUDE)) + amplitude_da_longitude // 2
    valor_lon %= amplitude_da_longitude
    codigo = ""
    if comprimento > DIGITOS_EM_PARES:
        for _ in range(DIGITOS_NO_MAXIMO - DIGITOS_EM_PARES):
            indice = (valor_lat % LINHAS_DA_GRADE) * COLUNAS_DA_GRADE + valor_lon % COLUNAS_DA_GRADE
            codigo = ALFABETO[indice] + codigo
            valor_lat //= LINHAS_DA_GRADE
            valor_lon //= COLUNAS_DA_GRADE
    else:
        valor_lat //= LINHAS_DA_GRADE ** 5
        valor_lon //= COLUNAS_DA_GRADE ** 5
    for _ in range(DIGITOS_EM_PARES // 2):
        codigo = ALFABETO[valor_lon % BASE] + codigo
        codigo = ALFABETO[valor_lat % BASE] + codigo
        valor_lat //= BASE
        valor_lon //= BASE
    codigo = codigo[:POSICAO_DO_SEPARADOR] + SEPARADOR + codigo[POSICAO_DO_SEPARADOR:]
    if comprimento >= POSICAO_DO_SEPARADOR:
        return codigo[:comprimento + 1]
    return codigo[:comprimento] + PREENCHIMENTO * (POSICAO_DO_SEPARADOR - comprimento) + SEPARADOR


def decodificar(codigo):
    if not e_completo(codigo):
        raise ValueError(CODIGO_INVALIDO.format(codigo))
    digitos = codigo.upper().replace(SEPARADOR, "").replace(PREENCHIMENTO, "")
    digitos = digitos[:DIGITOS_NO_MAXIMO]
    lat_normal = int(-LATITUDE_MAXIMA * PRECISAO_DOS_PARES)
    lon_normal = int(-LONGITUDE_MAXIMA * PRECISAO_DOS_PARES)
    valor_do_par = PRIMEIRO_VALOR_DE_PAR
    nos_pares = min(len(digitos), DIGITOS_EM_PARES)
    for i in range(0, nos_pares, 2):
        lat_normal += ALFABETO.index(digitos[i]) * valor_do_par
        lon_normal += ALFABETO.index(digitos[i + 1]) * valor_do_par
        if i < nos_pares - 2:
            valor_do_par //= BASE
    passo_lat = valor_do_par / PRECISAO_DOS_PARES
    passo_lon = valor_do_par / PRECISAO_DOS_PARES
    lat_grade, lon_grade = 0, 0
    if len(digitos) > DIGITOS_EM_PARES:
        valor_da_linha = LINHAS_DA_GRADE ** 4
        valor_da_coluna = COLUNAS_DA_GRADE ** 4
        for i in range(DIGITOS_EM_PARES, len(digitos)):
            indice = ALFABETO.index(digitos[i])
            lat_grade += (indice // COLUNAS_DA_GRADE) * valor_da_linha
            lon_grade += (indice % COLUNAS_DA_GRADE) * valor_da_coluna
            if i < len(digitos) - 1:
                valor_da_linha //= LINHAS_DA_GRADE
                valor_da_coluna //= COLUNAS_DA_GRADE
        passo_lat = valor_da_linha / PRECISAO_FINAL_DA_LATITUDE
        passo_lon = valor_da_coluna / PRECISAO_FINAL_DA_LONGITUDE
    lat_min = lat_normal / PRECISAO_DOS_PARES + lat_grade / PRECISAO_FINAL_DA_LATITUDE
    lon_min = lon_normal / PRECISAO_DOS_PARES + lon_grade / PRECISAO_FINAL_DA_LONGITUDE
    lat = lat_min + passo_lat / 2
    lon = lon_min + passo_lon / 2
    return {"lat": lat, "lon": lon,
            "raio_da_celula_m": round(raio_da_celula_m(lat, passo_lat, passo_lon), 1),
            "digitos": len(digitos)}


def raio_da_celula_m(lat, passo_lat, passo_lon):
    meia_altura = passo_lat / 2 * METROS_POR_GRAU
    meia_largura = passo_lon / 2 * METROS_POR_GRAU * math.cos(math.radians(lat))
    return math.hypot(meia_altura, meia_largura)


def recuperar(codigo_curto, lat_referencia, lon_referencia):
    if not e_valido(codigo_curto):
        raise ValueError(CODIGO_INVALIDO.format(codigo_curto))
    if e_completo(codigo_curto):
        return codigo_curto.upper()
    lat_referencia = limitar_latitude(lat_referencia)
    lon_referencia = normalizar_longitude(lon_referencia)
    faltam = POSICAO_DO_SEPARADOR - codigo_curto.find(SEPARADOR)
    resolucao = BASE ** (2 - faltam // 2)
    metade = resolucao / 2
    prefixo = codificar(lat_referencia, lon_referencia)[:faltam]
    centro = decodificar(prefixo + codigo_curto.upper())
    lat, lon = centro["lat"], centro["lon"]
    if lat_referencia + metade < lat and lat - resolucao >= -LATITUDE_MAXIMA:
        lat -= resolucao
    elif lat_referencia - metade > lat and lat + resolucao <= LATITUDE_MAXIMA:
        lat += resolucao
    if lon_referencia + metade < lon:
        lon -= resolucao
    elif lon_referencia - metade > lon:
        lon += resolucao
    return codificar(lat, lon, centro["digitos"])


def distancia_m(lat1, lon1, lat2, lon2):
    raio_terra_m = 6_371_008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * raio_terra_m * math.asin(math.sqrt(a))


def testar():
    casos = []

    def caso(nome, passou):
        casos.append(nome)
        assert passou, nome

    centro = decodificar("7FG49Q00+")
    caso("código curto preenchido decodifica no centro da célula de 0,05°",
         abs(centro["lat"] - 20.375) < 1e-9 and abs(centro["lon"] - 2.775) < 1e-9)
    centro = decodificar("7FG49QCJ+2V")
    caso("código de 10 dígitos decodifica no centro da célula de 1/8000°",
         abs(centro["lat"] - 20.3700625) < 1e-9 and abs(centro["lon"] - 2.7821875) < 1e-9)
    centro = decodificar("8FVC2222+22")
    caso("dígitos mínimos decodificam no canto inferior de cada célula",
         abs(centro["lat"] - 47.0000625) < 1e-9 and abs(centro["lon"] - 8.0000625) < 1e-9)
    centro = decodificar("6FH32222+222")
    caso("vetor público de 11 dígitos: a grade final é 5 linhas por 4 colunas",
         abs(centro["lat"] - 1.0000125) < 1e-9 and abs(centro["lon"] - 1.000015625) < 1e-9)
    caso("codificar reproduz os vetores públicos do padrão",
         codificar(20.375, 2.775, 6) == "7FG49Q00+"
         and codificar(47.0000625, 8.0000625) == "8FVC2222+22"
         and codificar(20.3701125, 2.782234375, 11) == "7FG49QCJ+2VX")
    caso("codificar arredonda ao inteiro mais próximo, como a referência: vetor público de 15 dígitos",
         codificar(47.00000008, 8.00022229, 15) == "8FVC2222+235235F")
    caso("latitude acima de 90 e longitude fora da volta são trazidas de volta antes de codificar",
         codificar(90, 1, 4) == "CFX30000+" and codificar(1, 180, 4) == "62H20000+")
    ponto = (-23.5505, -46.6333)
    ida_e_volta = decodificar(codificar(*ponto, COMPRIMENTO_DA_IDA_E_VOLTA))
    erro_m = distancia_m(*ponto, ida_e_volta["lat"], ida_e_volta["lon"])
    caso(f"ida-e-volta com {COMPRIMENTO_DA_IDA_E_VOLTA} dígitos erra menos de "
         f"{ERRO_MAXIMO_DA_IDA_E_VOLTA_M:.0f} m (mediu {erro_m:.1f} m)",
         erro_m < ERRO_MAXIMO_DA_IDA_E_VOLTA_M)
    de_10 = decodificar(codificar(*ponto))
    caso("ida-e-volta com 10 dígitos erra menos que o raio da própria célula",
         distancia_m(*ponto, de_10["lat"], de_10["lon"]) <= de_10["raio_da_celula_m"])
    completo = codificar(*ponto)
    curto = completo[4:]
    caso("código curto da ficha recompõe o inteiro a partir do centro da cidade",
         not e_completo(curto) and recuperar(curto, -23.55, -46.63) == completo)
    ao_sul = codificar(-23.9505, -46.6333)
    caso("referência em célula vizinha ainda recompõe o código mais próximo",
         recuperar(ao_sul[4:], -24.1, -46.6333) == ao_sul)
    caso("código com caractere fora do alfabeto é recusado",
         not e_valido("7FG49QAJ+2V") and not e_valido("7FG49QCJ2V"))
    caso("código de um só caractere ou curto com preenchimento é recusado, como no padrão",
         not e_valido("+") and not e_valido("WC2300+") and not e_valido("7F00+"))
    try:
        recuperar("C9A8+VF", -23.55, -46.63)
        recusou = False
    except ValueError:
        recusou = True
    caso("recuperar recusa código curto inválido em vez de chutar", recusou)
    print(f"testes: {len(casos)}/{len(casos)} passaram")


def principal():
    if "--testar" in sys.argv:
        testar()
        return
    parser = argparse.ArgumentParser(
        description="Plus Code (Open Location Code) para lat/lon e de volta, sem chave de API")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--decodificar", metavar="CODIGO",
                       help="o Plus Code da ficha; curto (XXXX+XX) pede --referencia")
    grupo.add_argument("--codificar", nargs=2, type=float, metavar=("LAT", "LON"))
    parser.add_argument("--referencia", nargs=2, type=float, metavar=("LAT", "LON"),
                        help="ponto a menos de 50 km, para recompor código curto")
    parser.add_argument("--comprimento", type=int, default=COMPRIMENTO_PADRAO)
    args = parser.parse_args()

    try:
        if args.codificar:
            codigo = codificar(args.codificar[0], args.codificar[1], args.comprimento)
        elif args.referencia is not None:
            codigo = recuperar(args.decodificar, args.referencia[0], args.referencia[1])
        elif e_completo(args.decodificar):
            codigo = args.decodificar.upper()
        elif e_valido(args.decodificar):
            sys.exit(CURTO_SEM_REFERENCIA.format(args.decodificar))
        else:
            raise ValueError(CODIGO_INVALIDO.format(args.decodificar))
        centro = decodificar(codigo)
    except ValueError as erro:
        sys.exit(str(erro))
    centro["lat"], centro["lon"] = round(centro["lat"], 8), round(centro["lon"], 8)
    print(json.dumps({"codigo": codigo, **centro}, ensure_ascii=False))


if __name__ == "__main__":
    principal()
