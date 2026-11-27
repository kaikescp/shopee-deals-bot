import json
import os
import time

# Os arquivos ficam na pasta raiz do projeto, ao lado de .env.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMINHO = os.path.join(RAIZ, "config.json")
SINAL = os.path.join(RAIZ, "bot_status.json")

PADRAO = {
    "pausado": False,
    "palavras_chave": ["Eletrônicos"],
    "palavras_por_ciclo": 1,
    "paginas_por_busca": 3,
    "limite_por_busca": 20,
    "pausa_entre_requisicoes": 5,
    "coletar_a_cada_minutos": 10,
    "publicar_a_cada_segundos": 180,
    "min_comissao": 0.05,
    "min_vendas": 0,
    "min_avaliacao": 0,
}


def carregar():
    """Lê config.json e completa com os padrões. Se o arquivo estiver inválido, usa os padrões."""
    cfg = dict(PADRAO)
    cfg["palavras_chave"] = list(PADRAO["palavras_chave"])

    try:
        with open(CAMINHO, encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        for chave in PADRAO:
            if chave in dados:
                cfg[chave] = dados[chave]

    except FileNotFoundError:
        pass
    except (json.JSONDecodeError, OSError) as erro:
        print(f"⚠️ config.json inválido, usando padrões: {erro}")

    return cfg


def salvar(cfg):
    """Grava só as chaves conhecidas em config.json."""
    limpo = {chave: cfg[chave] for chave in PADRAO}

    with open(CAMINHO, "w", encoding="utf-8") as arquivo:
        json.dump(limpo, arquivo, ensure_ascii=False, indent=2)


def registrar_sinal(pausado, etapa="aguardando"):
    """O bot chama isso periodicamente, para o painel saber que ele está rodando e o que faz."""
    try:
        with open(SINAL, "w", encoding="utf-8") as arquivo:
            json.dump(
                {"rodando": True, "pausado": pausado, "etapa": etapa, "ultimo_sinal": time.time()},
                arquivo,
            )
    except OSError:
        pass


def registrar_parada():
    """Marca que o bot foi encerrado de forma limpa."""
    try:
        with open(SINAL, "w", encoding="utf-8") as arquivo:
            json.dump({"rodando": False, "pausado": False, "ultimo_sinal": time.time()}, arquivo)
    except OSError:
        pass


PEDIDO_PARAR = os.path.join(RAIZ, "parar.flag")


def pedir_parada():
    """O painel chama isso para o bot parar sozinho na próxima verificação."""
    with open(PEDIDO_PARAR, "w", encoding="utf-8") as arquivo:
        arquivo.write("parar")


def pedido_parar():
    return os.path.exists(PEDIDO_PARAR)


def limpar_pedido_parar():
    try:
        os.remove(PEDIDO_PARAR)
    except FileNotFoundError:
        pass


POSICAO = os.path.join(RAIZ, "rodizio.json")


def ler_posicao():
    """Última posição do rodízio de palavras-chave, para continuar de onde parou após reiniciar."""
    try:
        with open(POSICAO, encoding="utf-8") as arquivo:
            return int(json.load(arquivo).get("posicao", 0))
    except (OSError, ValueError, AttributeError):
        return 0


def salvar_posicao(posicao):
    try:
        with open(POSICAO, "w", encoding="utf-8") as arquivo:
            json.dump({"posicao": posicao}, arquivo)
    except OSError:
        pass


def ler_sinal():
    """Último sinal do bot, ou None se nunca rodou."""
    try:
        with open(SINAL, encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (OSError, json.JSONDecodeError):
        return None