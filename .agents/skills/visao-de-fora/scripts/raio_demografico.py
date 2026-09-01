import argparse
import csv
import json
import math
import sqlite3
import struct
import sys

FAIXAS = {
    "0-14": ["V01031", "V01032", "V01033"],
    "15-29": ["V01034", "V01035", "V01036"],
    "30-59": ["V01037", "V01038", "V01039"],
    "60+": ["V01040", "V01041"],
}
MULHERES_40_MAIS = ["V01027", "V01028", "V01029", "V01030"]
UM_CENTESIMO_DE_GRAU_DE_LATITUDE_EM_KM = 1.112


def haversine_km(lat1, lon1, lat2, lon2):
    raio_terra = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * raio_terra * math.asin(math.sqrt(a))


def centro_do_envelope_gpb(blob):
    if blob is None or len(blob) < 8 or blob[:2] != b"GP":
        return None
    flags = blob[3]
    little = "<" if flags & 0x01 else ">"
    indicador = (flags >> 1) & 0x07
    if indicador == 0:
        return None
    n_doubles = {1: 4, 2: 6, 3: 6, 4: 8}.get(indicador)
    if n_doubles is None:
        return None
    vals = struct.unpack(f"{little}{n_doubles}d", blob[8:8 + 8 * n_doubles])
    minx, maxx, miny, maxy = vals[0], vals[1], vals[2], vals[3]
    return ((miny + maxy) / 2, (minx + maxx) / 2)


def tabela_de_setores(con):
    linha = con.execute(
        "SELECT table_name FROM gpkg_contents WHERE data_type='features'"
    ).fetchone()
    if linha is None:
        sys.exit("o GPKG não tem tabela de feições — arquivo errado?")
    return linha[0]


def carregar_setores(gpkg, cd_mun):
    con = sqlite3.connect(gpkg)
    tabela = tabela_de_setores(con)
    linhas = con.execute(
        f"SELECT CD_SETOR, NM_BAIRRO, AREA_KM2, v0001, v0002, geom "
        f"FROM {tabela} WHERE CD_MUN = ?", (cd_mun,)
    ).fetchall()
    con.close()
    setores = {}
    for cd, bairro, area, pop, dom, geom in linhas:
        centro = centro_do_envelope_gpb(geom)
        if centro is None:
            continue
        setores[str(cd)] = {
            "bairro": bairro or "(sem bairro)",
            "area_km2": float(area or 0),
            "pop": int(pop or 0),
            "dom": int(dom or 0),
            "lat": centro[0],
            "lon": centro[1],
        }
    return setores


def anexar_faixas_etarias(csv_demografia, setores):
    with open(csv_demografia, newline="", encoding="utf-8-sig") as arq:
        leitor = csv.DictReader(arq, delimiter=";")
        for linha in leitor:
            cd = linha.get("CD_setor") or linha.get("CD_SETOR")
            alvo = setores.get(str(cd))
            if alvo is None:
                continue
            def valor(campo):
                bruto = (linha.get(campo) or "0").strip()
                return int(bruto) if bruto.isdigit() else 0
            alvo["faixas"] = {
                nome: sum(valor(c) for c in cols) for nome, cols in FAIXAS.items()
            }
            alvo["mulheres_40_mais"] = sum(valor(c) for c in MULHERES_40_MAIS)


def resumo_por_raio(setores, lat, lon, raios):
    resultado = []
    for raio in sorted(raios):
        dentro = [s for s in setores.values()
                  if haversine_km(lat, lon, s["lat"], s["lon"]) <= raio]
        faixas = {nome: sum(s.get("faixas", {}).get(nome, 0) for s in dentro)
                  for nome in FAIXAS}
        area = sum(s["area_km2"] for s in dentro)
        pop = sum(s["pop"] for s in dentro)
        bairros = {}
        for s in dentro:
            bairros[s["bairro"]] = bairros.get(s["bairro"], 0) + s["pop"]
        resultado.append({
            "raio_km": raio,
            "setores": len(dentro),
            "populacao": pop,
            "domicilios": sum(s["dom"] for s in dentro),
            "area_km2": round(area, 2),
            "densidade_hab_km2": round(pop / area) if area else 0,
            "faixas": faixas,
            "mulheres_40_mais": sum(s.get("mulheres_40_mais", 0) for s in dentro),
            "bairros_top": sorted(bairros.items(), key=lambda kv: -kv[1])[:8],
        })
    return resultado


def testar():
    assert haversine_km(-23.0, -47.0, -23.0, -47.0) < 1e-9
    assert abs(haversine_km(-23.0, -47.0, -23.01, -47.0)
               - UM_CENTESIMO_DE_GRAU_DE_LATITUDE_EM_KM) < 0.01
    blob = (b"GP" + bytes([0, 0b00000011]) + struct.pack("<i", 4674)
            + struct.pack("<4d", -47.5, -47.4, -23.5, -23.4))
    lat, lon = centro_do_envelope_gpb(blob)
    assert abs(lat - (-23.45)) < 1e-9 and abs(lon - (-47.45)) < 1e-9
    assert centro_do_envelope_gpb(b"XX") is None
    print("testes: 4/4 passaram")


def principal():
    if "--testar" in sys.argv:
        testar()
        return
    parser = argparse.ArgumentParser(
        description="demografia por raio — Censo 2022, agregados por setor censitário")
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--municipio", required=True,
                        help="código IBGE de 7 dígitos do município")
    parser.add_argument("--gpkg", required=True,
                        help="malha de setores com atributos da UF (GPKG)")
    parser.add_argument("--demografia", required=True,
                        help="CSV Agregados_por_setores_demografia_BR extraído")
    parser.add_argument("--raios", default="1,2,3")
    parser.add_argument("--saida", default="raio-resultado.json")
    args = parser.parse_args()

    raios = [float(r) for r in args.raios.split(",")]
    setores = carregar_setores(args.gpkg, args.municipio)
    if not setores:
        sys.exit("nenhum setor carregado — confira --gpkg e --municipio")
    anexar_faixas_etarias(args.demografia, setores)
    resultado = resumo_por_raio(setores, args.lat, args.lon, raios)

    with open(args.saida, "w", encoding="utf-8") as arq:
        json.dump({"ancora": {"lat": args.lat, "lon": args.lon},
                   "municipio": args.municipio,
                   "fonte": "IBGE, Censo Demográfico 2022 — agregados por setor censitário",
                   "raios": resultado}, arq, ensure_ascii=False, indent=1)

    for r in resultado:
        print(f"\n== raio {r['raio_km']} km — {r['setores']} setores ==")
        print(f"população: {r['populacao']:,} | domicílios: {r['domicilios']:,}"
              f" | densidade: {r['densidade_hab_km2']:,} hab/km²")
        print(f"faixas: {r['faixas']} | mulheres 40+: {r['mulheres_40_mais']:,}")
        print("bairros:", ", ".join(f"{b} ({p:,})" for b, p in r["bairros_top"][:5]))


if __name__ == "__main__":
    principal()
