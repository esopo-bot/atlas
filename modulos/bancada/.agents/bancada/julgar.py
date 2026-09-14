import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bancada

USO = ("aplica ao placar os itens que instrumento nenhum mede — os que um "
       "painel de juizes julgou lendo o resumo de cada braco. O julgamento "
       "chega como JSON: {\"<braco>\": {\"<item>\": 0|1}}")
ITEM_DESCONHECIDO = ("o item {!r} nao existe no placar do braco {!r}. Os que "
                     "existem: {}")


def aplicar(versao: str, julgamentos: dict, pasta: Path) -> None:
    bancada.CASA = pasta
    bancada.RODADAS = pasta / "rodadas"
    for braco, itens in julgamentos.items():
        arquivo = bancada.pasta_da_rodada(versao, braco) / "medidas.json"
        medidas = json.loads(arquivo.read_text(encoding="utf-8"))
        for item, valor in itens.items():
            if item not in medidas["itens"]:
                raise SystemExit(ITEM_DESCONHECIDO.format(
                    item, braco, ", ".join(sorted(medidas["itens"]))))
            medidas["itens"][item] = valor
        aplicaveis = [v for v in medidas["itens"].values() if v is not None]
        if not medidas.get("nao_mediu") and aplicaveis:
            medidas["nota"] = round(100 * sum(aplicaveis) / len(aplicaveis))
        arquivo.write_text(
            json.dumps(medidas, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8")
    bancada.placar(versao)


def main() -> int:
    parser = argparse.ArgumentParser(description=USO)
    parser.add_argument("versao")
    parser.add_argument("julgamentos", help="o JSON do painel")
    parser.add_argument("--pasta", default="tmp/bancada",
                        help="onde as rodadas moram")
    args = parser.parse_args()
    aplicar(args.versao, json.loads(args.julgamentos), Path(args.pasta).resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
