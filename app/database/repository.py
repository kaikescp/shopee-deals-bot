from app.database.connection import conectar


def produto_ja_publicado(product_id, channel):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT id
        FROM publications
        WHERE product_id = ?
        AND channel = ?
        AND status = 'success'
        LIMIT 1
    """, (product_id, channel))

    resultado = cursor.fetchone()
    conexao.close()

    return resultado is not None


def nomes_publicados(channel):
    """Nomes de todos os produtos já publicados no canal."""
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT p.name
        FROM publications pub
        JOIN products p ON p.id = pub.product_id
        WHERE pub.channel = ?
        AND pub.status = 'success'
    """, (channel,))

    nomes = [linha[0] for linha in cursor.fetchall()]
    conexao.close()

    return nomes


def candidatos_publicacao(channel, limite=100, categorias=None):
    """
    Produtos já coletados, com link de afiliado, ainda não publicados no canal.
    categorias: se informado, só traz produtos dessas palavras-chave (filtro feito no banco,
    antes do limite, para que produtos antigos de outras buscas não ocupem a lista).
    Mais recentes primeiro. Não consulta a API.
    """
    conexao = conectar()
    cursor = conexao.cursor()

    filtro_categoria = ""
    parametros = [channel]

    if categorias:
        marcas = ",".join("?" for _ in categorias)
        filtro_categoria = f"AND LOWER(p.category) IN ({marcas})"
        parametros += [c.lower() for c in categorias]

    cursor.execute(f"""
        SELECT p.id, p.name, p.price, p.original_price, p.category,
               p.product_url, p.affiliate_url, p.image_url
        FROM products p
        WHERE p.active = 1
        AND p.affiliate_url IS NOT NULL
        AND p.affiliate_url != ''
        AND p.price > 0
        AND NOT EXISTS (
            SELECT 1
            FROM publications pub
            WHERE pub.product_id = p.id
            AND pub.channel = ?
            AND pub.status = 'success'
        )
        {filtro_categoria}
        ORDER BY p.rowid DESC
        LIMIT ?
    """, parametros + [limite])

    candidatos = [dict(linha) for linha in cursor.fetchall()]
    conexao.close()

    return candidatos


def descartar_candidatos(channel, categorias):
    """
    Tira da fila as ofertas ainda não publicadas no canal, das palavras informadas.
    Marca o produto como inativo (active = 0), então o bot não posta mais.
    Se a mesma oferta aparecer numa busca futura, continua inativa.
    Retorna quantas ofertas foram removidas.
    """
    candidatos = candidatos_publicacao(channel, limite=100000, categorias=categorias)
    ids = [(c["id"],) for c in candidatos]

    if not ids:
        return 0

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.executemany("UPDATE products SET active = 0 WHERE id = ?", ids)

    conexao.commit()
    conexao.close()

    return len(ids)


def registrar_mensagem(produto, channel, message_id, texto):
    """
    Guarda o conteúdo completo da mensagem enviada ao grupo: texto, imagem, preço,
    nome e links. Assim dá para consultar depois o que foi postado.
    """
    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            INSERT INTO mensagens_enviadas (
                product_id, channel, external_message_id,
                nome, categoria, preco, imagem_url,
                link_produto, link_afiliado, texto
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            produto["id"],
            channel,
            str(message_id) if message_id is not None else None,
            produto.get("name"),
            produto.get("category"),
            produto.get("price"),
            produto.get("image_url"),
            produto.get("product_url"),
            produto.get("affiliate_url"),
            texto,
        ))

        conexao.commit()

    finally:
        conexao.close()


def registrar_publicacao(product_id, channel, message_id=None):
    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            INSERT INTO publications (
                product_id,
                channel,
                external_message_id,
                status
            )
            VALUES (?, ?, ?, 'success')
        """, (product_id, channel, str(message_id) if message_id is not None else None))

        conexao.commit()

    finally:
        conexao.close()