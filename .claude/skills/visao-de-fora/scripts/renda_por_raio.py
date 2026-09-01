import argparse
import json
import math
import struct
import sys


def haversine_km(lat1, lon1, lat2, lon2):
    raio_terra = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * raio_terra * math.asin(math.sqrt(a))


def centro_de_bbox_por_registro_do_shp(caminho_shp):
    centros = []
    with open(caminho_shp, "rb") as arq:
        arq.seek(100)
        while True:
            cabecalho = arq.read(8)
            if len(cabecalho) < 8:
                break
            _, tamanho_em_palavras = struct.unpack(">2i", cabecalho)
            conteudo = arq.read(tamanho_em_palavras * 2)
            tipo = struct.unpack("<i", conteudo[:4])[0]
            if tipo in (3, 5, 13, 15):
                minx, miny, maxx, maxy = struct.unpack("<4d", conteudo[4:36])
                centros.append(((miny + maxy) / 2, (minx + maxx) / 2))
            else:
                centros.append(None)
    return centros


def coluna_do_dbf_por_registro(caminho_dbf, nome_campo):
    with open(caminho_dbf, "rb") as arq:
        cab = arq.read(32)
        n_registros = struct.unpack("<i", cab[4:8])[0]
        tam_cabecalho = struct.unpack("<h", cab[8:10])[0]
        tam_registro = struct.unpack("<h", cab[10:12])[0]
        campos, deslocamento = [], 1
        while True:
            desc = arq.read(32)
            if desc[0:1] == b"\r":
                break
            nome = desc[:11].split(b"\x00")[0].decode("ascii", "ignore")
            largura = desc[16]
            campos.append((nome, deslocamento, largura))
            deslocamento += largura
        alvo = next((c for c in campos if c[0] == nome_campo), None)
        if alvo is None:
            sys.exit(f"campo {nome_campo} não existe no DBF: {[c[0] for c in campos]}")
        _, inicio, largura = alvo
        arq.seek(tam_cabecalho)
        valores = []
        for _ in range(n_registros):
            registro = arq.read(tam_registro)
            valores.append(registro[inicio:inicio + largura].decode("ascii", "ignore").strip())
    return valores


def renda_por_setor(caminho_csv, prefixo_municipio):
    resultado = {}
    with open(caminho_csv, encoding="latin-1", newline="") as arq:
        cabecalho = arq.readline().rstrip("\n").split(";")
        idx = {nome.strip('"'): i for i, nome in enumerate(cabecalho)}
        for linha in arq:
            partes = linha.rstrip("\n").split(";")
            setor = partes[idx["Cod_setor"]].strip('"')
            if not setor.startswith(prefixo_municipio):
                continue
            def numero(campo):
                bruto = partes[idx[campo]].strip('"').replace(",", ".")
                try:
                    return float(bruto)
                except ValueError:
                    return None
            resultado[setor] = (numero("V001"), numero("V005"))
    return resultado


def media_ponderada(pares):
    peso_total = sum(p for p, v in pares if p and v)
    if not peso_total:
        return None
    return sum(p * v for p, v in pares if p and v) / peso_total


def testar():
    assert haversine_km(0, 0, 0, 0) < 1e-9
    assert media_ponderada([(10, 100.0), (30, 300.0)]) == 250.0
    assert media_ponderada([(0, 100.0)]) is None
    assert media_ponderada([]) is None
    print("testes: 4/4 passaram")


def principal():
    if "--testar" in sys.argv:
        testar()
        return
    parser = argparse.ArgumentParser(
        description="renda relativa por raio — Censo 2010, Básico por setor censitário")
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--shp", required=True, help="malha de setores 2010 (.shp)")
    parser.add_argument("--dbf", required=True, help="atributos da malha (.dbf)")
    parser.add_argument("--csv", required=True, help="Basico_<UF>.csv do Censo 2010")
    parser.add_argument("--municipio", required=True,
                        help="código IBGE de 7 dígitos do município")
    parser.add_argument("--raios", default="1,2,3")
    parser.add_argument("--saida", default="renda-resultado.json")
    args = parser.parse_args()

    centros = centro_de_bbox_por_registro_do_shp(args.shp)
    codigos = coluna_do_dbf_por_registro(args.dbf, "CD_GEOCODI")
    renda = renda_por_setor(args.csv, args.municipio)

    setores = []
    for codigo, centro in zip(codigos, centros):
        if centro is None or not codigo.startswith(args.municipio):
            continue
        dados = renda.get(codigo)
        if dados is None:
            continue
        setores.append({"codigo": codigo, "lat": centro[0], "lon": centro[1],
                        "domicilios": dados[0], "renda_media": dados[1]})
    if not setores:
        sys.exit("nenhum setor com renda — confira --municipio e os arquivos")

    media_municipio = media_ponderada([(s["domicilios"], s["renda_media"]) for s in setores])
    saida = {"fonte": "IBGE, Censo 2010 — Básico V005 (renda média do responsável, R$ de 2010)",
             "municipio": args.municipio,
             "setores_com_renda": len(setores),
             "renda_media_municipio_2010": round(media_municipio, 2),
             "raios": []}
    for raio in sorted(float(r) for r in args.raios.split(",")):
        dentro = [s for s in setores
                  if haversine_km(args.lat, args.lon, s["lat"], s["lon"]) <= raio]
        media_raio = media_ponderada([(s["domicilios"], s["renda_media"]) for s in dentro])
        saida["raios"].append({
            "raio_km": raio,
            "setores": len(dentro),
            "renda_media_2010": round(media_raio, 2) if media_raio else None,
            "razao_sobre_municipio": round(media_raio / media_municipio, 2) if media_raio else None,
        })

    with open(args.saida, "w", encoding="utf-8") as arq:
        json.dump(saida, arq, ensure_ascii=False, indent=1)
    print(f"município: {len(setores)} setores | renda média 2010: R$ {media_municipio:.0f}")
    for r in saida["raios"]:
        if r["renda_media_2010"] is None:
            print(f"raio {r['raio_km']} km: sem setor com renda")
            continue
        print(f"raio {r['raio_km']} km: R$ {r['renda_media_2010']:.0f}"
              f" | {r['razao_sobre_municipio']:.2f}x a média da cidade"
              f" | {r['setores']} setores")


if __name__ == "__main__":
    principal()
