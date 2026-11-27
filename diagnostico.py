"""
Mostra quantos produtos sobram em cada etapa do filtro de publicação.
Rode na pasta raiz do projeto: python diagnostico.py
"""
from app.collectors.shopee_collector import PALAVRAS_CHAVE, _combina_com_busca
from app.database.connection import conectar
from app.filters.duplicate_filter import e_duplicado
from app.database.repository import nomes_publicados

CANAL = "telegram"


def main():
    conexao = conectar()
    cursor = conexao.cursor()

    linhas = [dict(l) for l in cursor.execute("""
        SELECT p.id, p.name, p.price, p.category, p.affiliate_url, p.active,
               EXISTS (
                   SELECT 1 FROM publications pub
                   WHERE pub.product_id = p.id
                   AND pub.channel = ? AND pub.status = 'success'
               ) AS publicado
        FROM products p
    """, (CANAL,)).fetchall()]
    conexao.close()

    palavras = {p.lower() for p in PALAVRAS_CHAVE}
    titulos = nomes_publicados(CANAL)

    etapas = [("Total no banco", linhas)]
    etapas.append(("Ativos", [p for p in etapas[-1][1] if p["active"] == 1]))
    etapas.append(("Categoria é uma palavra-chave atual",
                   [p for p in etapas[-1][1] if (p["category"] or "").lower() in palavras]))
    etapas.append(("Nome combina com a palavra-chave",
                   [p for p in etapas[-1][1]
                    if _combina_com_busca(p["name"], p["category"] or "")]))
    etapas.append(("Tem link de afiliado",
                   [p for p in etapas[-1][1] if p["affiliate_url"]]))
    etapas.append(("Preço válido",
                   [p for p in etapas[-1][1] if p["price"] > 0]))
    etapas.append((f"Ainda não publicados no {CANAL}",
                   [p for p in etapas[-1][1] if not p["publicado"]]))
    etapas.append(("Sem título parecido já publicado",
                   [p for p in etapas[-1][1] if not e_duplicado(p["name"], titulos)]))

    print("Funil de publicação:\n")
    for nome, lista in etapas:
        print(f"  {len(lista):>5}  {nome}")


if __name__ == "__main__":
    main()