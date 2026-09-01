import argparse
import json
import sys

from renda_por_raio import (centro_de_bbox_por_registro_do_shp,
                            coluna_do_dbf_por_registro, haversine_km,
                            media_ponderada, renda_por_setor)


def setores_no_raio(setores, lat, lon, raio_km):
    return [s for s in setores
            if haversine_km(lat, lon, s["lat"], s["lon"]) <= raio_km]


def validar_bairros(bairros):
    for bairro in bairros:
        if not {"bairro", "lat", "lon"} <= set(bairro):
            raise SystemExit(
                f"bairro sem campo obrigatorio (bairro, lat, lon): {bairro}")
    return bairros


def testar():
    setores = [
        {"lat": 0.0, "lon": 0.0, "domicilios": 10, "renda_media": 100.0},
        {"lat": 0.0, "lon": 0.005, "domicilios": 30, "renda_media": 300.0},
        {"lat": 1.0, "lon": 1.0, "domicilios": 99, "renda_media": 999.0},
    ]
    perto = setores_no_raio(setores, 0.0, 0.0, 0.8)
    assert len(perto) == 2
    assert media_ponderada([(s["domicilios"], s["renda_media"]) for s in perto]) == 250.0
    assert setores_no_raio(setores, 0.0, 0.0, 0.1) == setores[:1]
    completo = [{"bairro": "Centro", "lat": 0.0, "lon": 0.0}]
    assert validar_bairros(completo) == completo
    try:
        validar_bairros([{"bairro": "sem coordenada"}])
        raise AssertionError("bairro sem lat/lon deveria recusar")
    except SystemExit:
        pass
    print("testes: 5/5 passaram")


def principal():
    if "--testar" in sys.argv:
        testar()
        return
    parser = argparse.ArgumentParser(
        description="Renda relativa por bairro sobre a malha do Censo 2010: "
                    "para cada centroide do arquivo de bairros, a renda media "
                    "ponderada dos setores no raio e a razao sobre a media do "
                    "municipio.")
    parser.add_argument("--bairros", required=True,
                        help="JSON com lista de {bairro, lat, lon} geocodificados")
    parser.add_argument("--shp", required=True, help="malha 2010 (SHP)")
    parser.add_argument("--dbf", required=True, help="malha 2010 (DBF)")
    parser.add_argument("--csv", required=True, help="Basico do Censo 2010")
    parser.add_argument("--municipio", required=True,
                        help="codigo IBGE de 7 digitos")
    parser.add_argument("--raio-km", type=float, default=0.8)
    parser.add_argument("--fonte-centroides", default="Nominatim",
                        help="origem e data da geocodificacao, vai no JSON de saida")
    parser.add_argument("--saida", default="dados/renda-bairros-resultado.json")
    args = parser.parse_args()

    with open(args.bairros, encoding="utf-8") as arq:
        bairros = validar_bairros(json.load(arq))

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

    media_municipio = media_ponderada(
        [(s["domicilios"], s["renda_media"]) for s in setores])
    saida = {"fonte": "IBGE, Censo 2010 — Basico V005; centroides: "
                      + args.fonte_centroides,
             "raio_do_bairro_km": args.raio_km,
             "renda_media_municipio_2010": round(media_municipio, 2),
             "bairros": []}
    for item in bairros:
        dentro = setores_no_raio(setores, item["lat"], item["lon"], args.raio_km)
        media = media_ponderada(
            [(s["domicilios"], s["renda_media"]) for s in dentro])
        saida["bairros"].append({
            "bairro": item["bairro"],
            "setores": len(dentro),
            "renda_media_2010": round(media, 2) if media else None,
            "razao_sobre_municipio":
                round(media / media_municipio, 2) if media else None,
        })

    saida["bairros"].sort(
        key=lambda b: b["razao_sobre_municipio"] or 0, reverse=True)
    with open(args.saida, "w", encoding="utf-8") as arq:
        json.dump(saida, arq, ensure_ascii=False, indent=1)
    print(f"municipio {args.municipio}: renda media 2010 R$ {media_municipio:.0f}")
    for bairro in saida["bairros"]:
        if bairro["renda_media_2010"] is None:
            print(f"{bairro['bairro']}: sem setor com renda no raio")
            continue
        alerta = " | AMOSTRA FINA — indicativo" if bairro["setores"] <= 2 else ""
        print(f"{bairro['bairro']}: R$ {bairro['renda_media_2010']:.0f}"
              f" | {bairro['razao_sobre_municipio']:.2f}x a media do municipio"
              f" | {bairro['setores']} setores{alerta}")


if __name__ == "__main__":
    principal()
