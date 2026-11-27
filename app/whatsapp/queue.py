from app.collectors.shopee_collector import _combina_com_busca
from app.config import carregar
from app.database.repository import candidatos_publicacao

CANAL = "whatsapp"


def _e_da_lista_atual(produto, palavras):
    """Só produtos de uma palavra-chave atual, cujo nome combina com ela."""
    categoria = (produto.get("category") or "").lower()
    atuais = {p.lower() for p in palavras}

    return categoria in atuais and _combina_com_busca(produto["name"], categoria)


def fila_pendente(limite=50):
    """Ofertas prontas para enviar pelo WhatsApp, mais recentes primeiro."""
    palavras = carregar()["palavras_chave"]

    candidatos = [
        c for c in candidatos_publicacao(CANAL, limite=500)
        if _e_da_lista_atual(c, palavras)
    ]

    return candidatos[:limite]