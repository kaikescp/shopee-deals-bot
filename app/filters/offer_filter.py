
def filtrar_ofertas(produtos, desconto_minimo=20):
    ofertas = []

    for produto in produtos:

        preco = produto["price"]
        preco_original = produto["original_price"]

        if preco_original <= 0 or preco <= 0:
            continue

        desconto = (
            (preco_original - preco)
            / preco_original
        ) * 100

        if preco < preco_original and desconto >= desconto_minimo:

            produto["discount"] = round(desconto, 2)

            ofertas.append(produto)

    return ofertas
