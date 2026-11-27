import os
import requests
from dotenv import load_dotenv
from html import escape

load_dotenv()

# Limite de legenda de foto no Telegram.
LIMITE_LEGENDA = 1024

# Tamanho máximo do nome do produto na mensagem.
LIMITE_NOME = 150


def formatar_preco(valor):
    """Formata o preço no padrão brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def montar_mensagem(produto):

    nome = escape(produto["name"][:LIMITE_NOME])
    categoria = escape(produto.get("category") or "Geral")

    mensagem = (
        "🛒 <b>NOVA OFERTA</b>\n\n"
        f"📦 <b>{nome}</b>\n"
        f"🏷️ Categoria: {categoria}\n\n"
        f"💰 <b>{formatar_preco(produto['price'])}</b>"
    )

    # Aviso de teste só aparece se MODO_TESTE=1 no .env.
    if os.getenv("MODO_TESTE") == "1":
        mensagem += "\n\n🧪 <i>Publicação de teste — produto fictício.</i>"

    return mensagem


def _chamar_telegram(token, metodo, dados):
    """Chama a API do Telegram. Retorna o JSON mesmo quando a resposta é erro."""
    resposta = requests.post(
        f"https://api.telegram.org/bot{token}/{metodo}",
        data=dados,
        timeout=30
    )

    # O Telegram devolve o motivo do erro no corpo da resposta, mesmo com status 400.
    return resposta.json()


def publicar_oferta(produto):

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise ValueError("Token ou Chat ID do Telegram não configurado.")

    mensagem = montar_mensagem(produto)

    imagem = produto.get("image_url")
    link = produto.get("affiliate_url") or produto.get("product_url")

    if link:
        mensagem += f'\n\n🔗 <a href="{escape(link, quote=True)}">Ver produto</a>'

    # Tenta com foto, se houver imagem e a legenda couber no limite.
    if imagem and len(mensagem) <= LIMITE_LEGENDA:
        resultado = _chamar_telegram(token, "sendPhoto", {
            "chat_id": chat_id,
            "photo": imagem,
            "caption": mensagem,
            "parse_mode": "HTML"
        })

        if resultado.get("ok"):
            return resultado["result"]["message_id"]

        # Se a foto for recusada, envia só o texto em vez de perder a oferta.
        print(f"⚠️ Foto recusada pelo Telegram: {resultado.get('description')}. Enviando só o texto.")

    resultado = _chamar_telegram(token, "sendMessage", {
        "chat_id": chat_id,
        "text": mensagem,
        "parse_mode": "HTML"
    })

    if not resultado.get("ok"):
        raise RuntimeError(
            f"Telegram recusou a mensagem: {resultado.get('description')}"
        )

    return resultado["result"]["message_id"]