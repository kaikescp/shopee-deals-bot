def formatar_preco(valor):
    """Formata o preço no padrão brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_mensagem(produto):
    """
    Texto para WhatsApp. O WhatsApp usa *negrito*, não HTML.
    O link é colocado como texto puro, e o próprio WhatsApp o transforma em link.
    """
    nome = produto["name"][:150]
    categoria = produto.get("category") or "Geral"
    link = produto.get("affiliate_url") or produto.get("product_url") or ""

    linhas = [
        "🛒 *NOVA OFERTA*",
        "",
        f"📦 *{nome}*",
        f"🏷️ Categoria: {categoria}",
        "",
        f"💰 *{formatar_preco(produto['price'])}*",
        "",
        f"🔗 {link}",
    ]

    return "\n".join(linhas)