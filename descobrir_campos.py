"""
Descobre quais campos de preço a API aceita e mostra os valores.
Campos inexistentes são removidos automaticamente.
Uso: python descobrir_campos.py "eletrônicos"
"""
import json
import re
import sys

from app.affiliate.link_generator import _executar_graphql, ShopeeAffiliateError

CAMPOS_BASE = ["itemId", "productName", "priceMin", "priceDiscountRate", "offerLink"]

# Nomes que podem trazer preço original, desconto ou dados de venda.
CAMPOS_CANDIDATOS = [
    "priceMax", "price", "originalPrice", "priceOriginal", "priceBeforeDiscount",
    "discountPct", "discountRate", "sales", "ratingStar", "shopName", "shopId",
    "commissionRate", "commission", "shopeeCommissionRate", "sellerCommissionRate",
]


def montar_query(campos):
    corpo = "\n      ".join(campos)
    return f"""
query ProductOfferV2($keyword: String, $page: Int, $limit: Int) {{
  productOfferV2(keyword: $keyword, page: $page, limit: $limit) {{
    nodes {{
      {corpo}
    }}
  }}
}}
"""


def main():
    palavra = sys.argv[1] if len(sys.argv) > 1 else "eletrônicos"
    campos = CAMPOS_BASE + CAMPOS_CANDIDATOS

    for tentativa in range(10):
        try:
            dados = _executar_graphql(
                montar_query(campos),
                {"keyword": palavra, "page": 1, "limit": 3},
            )
            break
        except ShopeeAffiliateError as erro:
            invalidos = re.findall(r'Cannot query field \\?"(\w+)\\?"', str(erro))
            if not invalidos:
                print(f"Erro que não é de campo inexistente: {erro}")
                return

            print(f"Campos inexistentes removidos: {', '.join(invalidos)}")
            campos = [c for c in campos if c not in invalidos]
    else:
        print("Não consegui montar uma consulta válida.")
        return

    print(f"\nCampos aceitos: {', '.join(campos)}\n")

    for item in dados["productOfferV2"]["nodes"]:
        print(json.dumps(item, ensure_ascii=False, indent=2))
        print("-" * 40)


if __name__ == "__main__":
    main()