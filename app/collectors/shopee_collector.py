import re
import time
import unicodedata

from app.affiliate.link_generator import _executar_graphql
from app.config import carregar

# Palavras que não ajudam a identificar o produto.
STOPWORDS = {"de", "do", "da", "dos", "das", "com", "para", "em", "um", "uma"}

# ATENÇÃO: os nomes dos argumentos e campos foram confirmados pelas respostas da API.
QUERY_PRODUTOS = """
query ProductOfferV2($keyword: String, $page: Int, $limit: Int) {
  productOfferV2(keyword: $keyword, page: $page, limit: $limit) {
    nodes {
      itemId
      productName
      priceMin
      priceDiscountRate
      imageUrl
      productCatIds
      offerLink
      productLink
      commissionRate
      sales
      ratingStar
    }
  }
}
"""


# Palavras que ficaram sem consulta porque a API atingiu o limite. Lidas por main.py.
_pendentes = []


def palavras_pendentes():
    """Palavras que não foram consultadas no último ciclo por causa do limite da API."""
    return list(_pendentes)


def _palavras(texto):
    """Minúsculas, sem acento, só letras e números."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return re.findall(r"[a-z0-9]+", texto)


def _radical(palavra):
    """Remove o 's' do plural, para 'fones' e 'fone' baterem."""
    if len(palavra) > 3 and palavra.endswith("s"):
        return palavra[:-1]
    return palavra


def _combina_com_busca(nome, palavra_chave):
    """
    True se o nome do produto contém todas as palavras da busca.
    Ex.: 'fones de ouvido' aceita 'Fone de Ouvido Bluetooth', mas não 'Telefone'.
    """
    termos = [_radical(t) for t in _palavras(palavra_chave) if t not in STOPWORDS]
    palavras_nome = _palavras(nome)

    if not termos:
        return True

    return all(any(p.startswith(t) for p in palavras_nome) for t in termos)


def _passa_criterios(item, cfg):
    """Comissão, vendas e avaliação mínimas, conforme o painel de controle."""
    comissao = float(item.get("commissionRate") or 0)
    vendas = int(float(item.get("sales") or 0))
    avaliacao = float(item.get("ratingStar") or 0)

    return (
        comissao >= cfg["min_comissao"]
        and vendas >= cfg["min_vendas"]
        and avaliacao >= cfg["min_avaliacao"]
    )


def _para_produto(item, categoria):
    """Converte um item da API para o formato que o resto do bot usa."""
    preco = float(item.get("priceMin") or 0)

    return {
        "id": str(item.get("itemId") or ""),
        "name": str(item.get("productName") or "").strip(),
        "price": preco,
        "original_price": preco,
        "category": categoria,
        "image_url": item.get("imageUrl") or "",
        "product_url": item.get("productLink") or "",
        "affiliate_url": item.get("offerLink") or "",
    }


def _consultar(palavra, pagina, limite):
    """Uma consulta. Se a API responder erro temporário, tenta mais uma vez após 15 segundos."""
    variaveis = {"keyword": palavra, "page": pagina, "limit": limite}

    try:
        return _executar_graphql(QUERY_PRODUTOS, variaveis)
    except Exception as erro:
        if "Erro temporário" not in str(erro):
            raise

        print("⏳ Erro temporário da API. Tentando de novo em 15 segundos...")
        time.sleep(15)
        return _executar_graphql(QUERY_PRODUTOS, variaveis)


def buscar_produtos(palavras=None):
    """
    Busca produtos na API. As palavras, páginas e critérios vêm de config.json.
    palavras: lista a consultar. Se não vier, usa todas as palavras da configuração.
    """
    global _pendentes
    _pendentes = []

    cfg = carregar()
    palavras = palavras or cfg["palavras_chave"]
    pausa = cfg["pausa_entre_requisicoes"]

    produtos = {}
    descartados_nome = 0
    descartados_criterio = 0

    for indice, palavra in enumerate(palavras):
        if indice > 0:
            time.sleep(pausa)

        for pagina in range(1, cfg["paginas_por_busca"] + 1):
            if pagina > 1:
                time.sleep(pausa)

            try:
                dados = _consultar(palavra, pagina, cfg["limite_por_busca"])
            except Exception as erro:
                print(f"❌ Falha na busca por '{palavra}' (página {pagina}): {erro}")

                # Se o limite da API foi atingido, não adianta continuar agora.
                if "Limite de requisições" in str(erro):
                    # Guarda a palavra que falhou e as que vieram depois, para a próxima coleta.
                    _pendentes = list(palavras[indice:])
                    print("⏸️ Limite da API atingido. Encerrando a busca deste ciclo.")
                    print(f"➡️ A próxima coleta começa por '{palavras[indice]}'.")
                    return list(produtos.values())

                break

            itens = dados["productOfferV2"]["nodes"]

            # Página vazia significa que não há mais produtos para essa palavra.
            if not itens:
                break

            for item in itens:
                produto = _para_produto(item, palavra.capitalize())

                # A API devolve itens parecidos, mas não necessariamente relacionados.
                if not _combina_com_busca(produto["name"], palavra):
                    descartados_nome += 1
                    continue

                if not _passa_criterios(item, cfg):
                    descartados_criterio += 1
                    continue

                # Só entra o que tem id, nome e link de afiliado já pronto.
                if produto["id"] and produto["name"] and produto["affiliate_url"]:
                    produtos[produto["id"]] = produto

    print(f"🔍 {len(produtos)} aproveitados da API.")
    if descartados_nome or descartados_criterio:
        print(
            f"   Descartados: {descartados_nome} porque o nome não combina com a busca, "
            f"{descartados_criterio} por comissão, vendas ou avaliação abaixo do mínimo."
        )
    return list(produtos.values())