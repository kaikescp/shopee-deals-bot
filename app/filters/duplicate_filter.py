import os
import re
import unicodedata

# Quanto as palavras de dois títulos precisam coincidir para serem considerados
# o mesmo produto (0 a 1). Mais alto = menos bloqueio. Ajuste no .env se precisar.
LIMIAR_SIMILARIDADE = float(os.getenv("LIMIAR_SIMILARIDADE", "0.45"))


def _palavras(texto):
    """Minúsculas, sem acento, sem pontuação, só palavras com 3 letras ou mais."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    texto = re.sub(r"[^a-z0-9 ]+", " ", texto)
    return {p for p in texto.split() if len(p) >= 3}


def similaridade(titulo_a, titulo_b):
    """Índice de Jaccard entre as palavras dos dois títulos (0 a 1)."""
    a = _palavras(titulo_a)
    b = _palavras(titulo_b)

    if not a or not b:
        return 0.0

    return len(a & b) / len(a | b)


def e_duplicado(titulo, titulos_publicados):
    """True se o título for parecido com algum já publicado."""
    for publicado in titulos_publicados:
        if similaridade(titulo, publicado) >= LIMIAR_SIMILARIDADE:
            return True
    return False