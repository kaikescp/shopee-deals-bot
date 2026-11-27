"""
Mostra a resposta bruta da API para uma palavra-chave, para conferir os campos de preço.
Uso: python ver_api.py "fone de ouvido"
"""
import json
import sys

from app.affiliate.link_generator import _executar_graphql
from app.collectors.shopee_collector import QUERY_PRODUTOS


def main():
    palavra = sys.argv[1] if len(sys.argv) > 1 else "fone de ouvido"

    dados = _executar_graphql(
        QUERY_PRODUTOS,
        {"keyword": palavra, "page": 1, "limit": 5},
    )

    for item in dados["productOfferV2"]["nodes"]:
        print(json.dumps(item, ensure_ascii=False, indent=2))
        print("-" * 40)


if __name__ == "__main__":
    main()