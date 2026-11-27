import hashlib
import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"

# Nome da mutation confirmado em fontes públicas: generateBatchShortLink.
# Os nomes dos campos de entrada e saída (originUrls, subIds, shortLinks)
# NÃO foram confirmados. Ajuste aqui se o schema do painel for diferente.
MUTATION_SHORT_LINK = """
mutation GenerateBatchShortLink($originUrls: [String], $subIds: [String]) {
  generateBatchShortLink(input: {originUrls: $originUrls, subIds: $subIds}) {
    shortLinks {
      originUrl
      shortLink
    }
  }
}
"""


class ShopeeAffiliateError(Exception):
    pass


def _credenciais():
    app_id = os.getenv("SHOPEE_APP_ID")
    secret = os.getenv("SHOPEE_APP_SECRET")

    if not app_id or not secret:
        raise ShopeeAffiliateError(
            "SHOPEE_APP_ID ou SHOPEE_APP_SECRET não configurados no .env."
        )

    return app_id, secret


def _headers(corpo, app_id, secret):
    # A assinatura usa o mesmo corpo enviado e um timestamp atual.
    timestamp = str(int(time.time()))
    base = f"{app_id}{timestamp}{corpo}{secret}"
    assinatura = hashlib.sha256(base.encode("utf-8")).hexdigest()

    return {
        "Content-Type": "application/json",
        "Authorization": (
            f"SHA256 Credential={app_id}, "
            f"Timestamp={timestamp}, "
            f"Signature={assinatura}"
        ),
    }


LIMITE_MENSAGEM = "Limite de requisições atingido. Aguarde antes de coletar de novo."

# 10030 é o limite de requisições. 10000 é erro de sistema da API, temporário e
# só deste pedido: não significa que a cota acabou.
CODIGO_LIMITE = "10030"


def _executar_graphql(query, variaveis):
    app_id, secret = _credenciais()

    corpo = json.dumps(
        {"query": query, "variables": variaveis},
        separators=(",", ":"),
        ensure_ascii=False,
    )

    # Uma única tentativa: cada repetição pode prolongar o bloqueio.
    resposta = requests.post(
        ENDPOINT,
        data=corpo.encode("utf-8"),
        headers=_headers(corpo, app_id, secret),
        timeout=30,
    )

    if resposta.status_code == 429:
        raise ShopeeAffiliateError(LIMITE_MENSAGEM)

    try:
        dados = resposta.json()
    except ValueError:
        resposta.raise_for_status()
        raise ShopeeAffiliateError(f"Resposta inválida da API: {resposta.text[:300]}")

    # Verifica só os erros devolvidos pela API, nunca o corpo inteiro. Assim um
    # número como o preço ou o ID de um produto não é confundido com erro.
    erros = dados.get("errors") or []
    if erros:
        mensagem = str(erros)
        if CODIGO_LIMITE in mensagem:
            raise ShopeeAffiliateError(f"{LIMITE_MENSAGEM} Detalhe da API: {mensagem[:300]}")
        if "10000" in mensagem:
            raise ShopeeAffiliateError(
                f"Erro temporário da API nesta busca (System Error). Detalhe: {mensagem[:300]}"
            )
        raise ShopeeAffiliateError(f"Erro da API: {mensagem[:300]}")

    resposta.raise_for_status()
    return dados["data"]


def gerar_link_afiliado(url_produto, sub_ids=None):
    """
    Gera um link curto de afiliado para uma URL de produto da Shopee.
    sub_ids: lista de tags para medir a origem das vendas (até 5, sem espaços).
    """
    if not url_produto:
        raise ShopeeAffiliateError("URL do produto vazia.")

    dados = _executar_graphql(
        MUTATION_SHORT_LINK,
        {"originUrls": [url_produto], "subIds": sub_ids or []},
    )

    links = dados["generateBatchShortLink"]["shortLinks"]

    if not links or not links[0].get("shortLink"):
        raise ShopeeAffiliateError(f"A API não devolveu link para {url_produto}.")

    return links[0]["shortLink"]