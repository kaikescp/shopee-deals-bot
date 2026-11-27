import time

from dotenv import load_dotenv

from app.collectors.shopee_collector import _combina_com_busca, buscar_produtos, palavras_pendentes
from app.config import (
    carregar,
    ler_posicao,
    limpar_pedido_parar,
    pedido_parar,
    registrar_parada,
    registrar_sinal,
    salvar_posicao,
)
from app.filters.duplicate_filter import e_duplicado
from app.database.models import criar_tabelas
from app.database.connection import conectar
from app.database.repository import (
    candidatos_publicacao,
    nomes_publicados,
    produto_ja_publicado,
    registrar_mensagem,
    registrar_publicacao
)
from app.telegram.publisher import montar_mensagem, publicar_oferta

load_dotenv()

CANAL = "telegram"

# Posição atual no rodízio das palavras-chave. Continua de onde parou após reiniciar.
_posicao_rodizio = ler_posicao()

# Produtos que deram erro ao publicar nesta execução. Não são tentados de novo.
_com_erro = set()

# Produtos já avisados como ignorados por parecerem repetidos. Evita repetir o aviso a cada ciclo.
_avisados = set()

# Intervalo de verificação enquanto o bot está pausado pelo painel.
SEGUNDOS_PAUSADO = 30

# Etapas mostradas no painel de controle.
ETAPA_POSTANDO = "postando"
ETAPA_COLETANDO = "coletando"
ETAPA_AGUARDANDO = "aguardando"


class PedidoDeParada(Exception):
    """Lançada quando o painel pede para o bot parar."""


def _dormir(segundos, pausado, etapa):
    """Espera enviando sinal de vida a cada minuto, para o painel saber que o bot está rodando."""
    fim = time.time() + segundos

    while True:
        if pedido_parar():
            raise PedidoDeParada()

        registrar_sinal(pausado, etapa)
        restante = fim - time.time()

        if restante <= 0:
            break

        time.sleep(min(60, restante))


def salvar_produtos(produtos):
    conexao = conectar()
    cursor = conexao.cursor()
    ids_existentes = {linha[0] for linha in cursor.execute("SELECT id FROM products").fetchall()}
    conexao.close()

    novos = [p for p in produtos if p["id"] not in ids_existentes]
    existentes = len(produtos) - len(novos)

    # Avisa os que já foram postados, para ficar claro por que não voltam a ser publicados.
    for produto in produtos:
        if produto_ja_publicado(produto["id"], CANAL):
            print(f"🔁 Já publicado antes, não será postado de novo: {produto['name']}")

    conexao = conectar()
    cursor = conexao.cursor()

    for produto in produtos:
        cursor.execute("""
            INSERT INTO products (
                id, name, price, original_price, category,
                product_url, affiliate_url, image_url
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                price = excluded.price,
                original_price = excluded.original_price,
                category = excluded.category,
                product_url = excluded.product_url,
                affiliate_url = excluded.affiliate_url,
                image_url = excluded.image_url
        """, (
            produto["id"],
            produto["name"],
            produto["price"],
            produto["original_price"],
            produto["category"],
            produto.get("product_url", ""),
            produto.get("affiliate_url", ""),
            produto.get("image_url", "")
        ))

    conexao.commit()
    conexao.close()

    print(f"📦 {len(produtos)} coletados: {len(novos)} novos, {existentes} já estavam no banco.")


def _proximo_lote(cfg):
    """Pega as próximas palavras da lista, em rodízio, e avança a posição."""
    global _posicao_rodizio

    palavras = cfg["palavras_chave"]

    if not palavras:
        return []

    total = len(palavras)
    quantidade = min(cfg["palavras_por_ciclo"], total)

    lote = [palavras[(_posicao_rodizio + i) % total] for i in range(quantidade)]
    _posicao_rodizio = (_posicao_rodizio + quantidade) % total
    salvar_posicao(_posicao_rodizio)

    return lote


def coletar(cfg):
    """Consulta algumas palavras-chave por ciclo e guarda no banco."""
    global _posicao_rodizio

    lote = _proximo_lote(cfg)

    if not lote:
        print("⚠️ Nenhuma palavra-chave configurada. Configure no painel.")
        return

    print(f"\n🔎 Coletando: {', '.join(lote)}")
    produtos = buscar_produtos(lote)
    salvar_produtos(produtos)

    # Se o limite da API cortou a coleta, a próxima começa pela palavra que ficou sem consulta.
    pendentes = palavras_pendentes()
    if pendentes:
        _posicao_rodizio = cfg["palavras_chave"].index(pendentes[0])
        salvar_posicao(_posicao_rodizio)

    print("Coleta concluída.")


def _e_da_lista_atual(produto, palavras):
    """
    True só se o produto pertence a uma palavra-chave atual e o nome combina com ela.
    Isso descarta sobras de buscas antigas guardadas no banco.
    """
    categoria = (produto.get("category") or "").lower()
    atuais = {p.lower() for p in palavras}

    return categoria in atuais and _combina_com_busca(produto["name"], categoria)


def _fila_pendente(cfg):
    """
    Ofertas prontas para publicar agora: das palavras atuais, com nome combinando,
    e sem título parecido com o que já foi publicado. Não consulta a API.
    """
    palavras = cfg["palavras_chave"]

    candidatos = [
        c for c in candidatos_publicacao(CANAL, limite=500, categorias=palavras)
        if _e_da_lista_atual(c, palavras) and c["id"] not in _com_erro
    ]

    titulos = nomes_publicados(CANAL)
    fila = []

    for c in candidatos:
        if not e_duplicado(c["name"], titulos):
            fila.append(c)
            continue

        # Mostra uma vez qual oferta já postada parece com esta, para você saber o motivo.
        if c["id"] not in _avisados:
            _avisados.add(c["id"])
            parecido = next((t for t in titulos if e_duplicado(c["name"], [t])), "")
            print(f"⏭️ Não postado, parecido com oferta já publicada: {c['name']}")
            print(f"   ↳ já postado: {parecido}")

    return fila


def publicar_um(produto):
    """Publica uma oferta no Telegram e registra no banco."""
    texto = montar_mensagem(produto)

    try:
        message_id = publicar_oferta(produto)
        registrar_publicacao(produto["id"], CANAL, message_id)
        registrar_mensagem(produto, CANAL, message_id, texto)

        print(f"✅ Publicado: {produto['name']} (R$ {produto['price']:.2f})".replace(".", ",", 1))

    except Exception as erro:
        _com_erro.add(produto["id"])
        print(f"❌ Erro ao publicar {produto['name']}: {erro}")


def executar():
    criar_tabelas()

    # Um pedido de parada antigo não deve impedir este início.
    limpar_pedido_parar()

    ultima_coleta = 0  # 0 faz a primeira busca logo no início
    estava_pausado = False
    postando = False

    print("Bot iniciado. Configurações no painel de controle. Ctrl+C para parar.")

    while True:
        # Relê a configuração a cada ciclo, então mudanças no painel valem sem reiniciar.
        cfg = carregar()

        if cfg["pausado"]:
            if not estava_pausado:
                print("⏸️ Bot pausado pelo painel de controle.")
                estava_pausado = True

            _dormir(SEGUNDOS_PAUSADO, pausado=True, etapa=ETAPA_AGUARDANDO)
            continue

        if estava_pausado:
            print("▶️ Bot retomado.")
            estava_pausado = False

        try:
            fila = _fila_pendente(cfg)
        except Exception as erro:
            print(f"❌ Erro ao montar a fila de publicação: {erro}")
            fila = []

        # Primeiro: publica a fila inteira, uma oferta por intervalo.
        if fila:
            if not postando:
                print(f"📤 Postando itens no Telegram ({len(fila)} na fila).")
                postando = True

            publicar_um(fila[0])
            _dormir(cfg["publicar_a_cada_segundos"], pausado=False, etapa=ETAPA_POSTANDO)
            continue

        if postando:
            print("✅ Fila postada. Buscando novos produtos.")
            postando = False

        # Depois: com a fila vazia, busca de novo, respeitando o intervalo entre buscas.
        if time.time() - ultima_coleta >= cfg["coletar_a_cada_minutos"] * 60:
            registrar_sinal(False, ETAPA_COLETANDO)

            try:
                coletar(cfg)
            except Exception as erro:
                print(f"❌ Erro na coleta: {erro}")

            ultima_coleta = time.time()
            continue

        espera = cfg["coletar_a_cada_minutos"] * 60 - (time.time() - ultima_coleta)
        _dormir(min(cfg["publicar_a_cada_segundos"], espera), pausado=False, etapa=ETAPA_AGUARDANDO)


if __name__ == "__main__":
    try:
        executar()
    except KeyboardInterrupt:
        registrar_parada()
        print("\nBot parado pelo usuário.")
    except PedidoDeParada:
        registrar_parada()
        limpar_pedido_parar()
        print("\nBot parado pelo painel de controle.")