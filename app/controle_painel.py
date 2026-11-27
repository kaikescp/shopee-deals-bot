import os
import subprocess
import sys
import time

from flask import Flask, jsonify, redirect, render_template_string, request, url_for

from app.collectors.shopee_collector import _combina_com_busca
from app.config import RAIZ, carregar, ler_sinal, limpar_pedido_parar, pedir_parada, salvar
from app.database.connection import conectar
from app.database.repository import candidatos_publicacao, descartar_candidatos, nomes_publicados
from app.filters.duplicate_filter import e_duplicado

app = Flask(__name__)

PAGINA = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Painel de controle</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 720px; margin: 0 auto;
           padding: 16px; background: #f2f2f2; color: #222; }
    h2 { margin-top: 8px; }
    .card { background: #fff; border-radius: 10px; padding: 16px;
            margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
    .stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
    .stat { background: #f7f7f7; border-radius: 8px; padding: 12px; }
    .stat b { display: block; font-size: 22px; }
    .stat span { color: #666; font-size: 13px; }
    label { display: block; margin-top: 12px; font-weight: 600; font-size: 14px; }
    small { color: #666; font-weight: normal; }
    input[type=number], textarea { width: 100%; padding: 8px; font-size: 14px;
             box-sizing: border-box; border: 1px solid #ccc; border-radius: 6px; margin-top: 4px; }
    textarea { min-height: 120px; }
    .check { display: flex; align-items: center; gap: 8px; margin-top: 12px; font-size: 15px; }
    button, .botao { display: inline-block; padding: 10px 16px; border: 0; border-radius: 6px;
             background: #25d366; color: #fff; font-size: 15px; cursor: pointer; text-decoration: none; }
    .msg { padding: 10px; border-radius: 6px; margin-bottom: 12px; }
    .ok { background: #e6f7ea; color: #1b5e20; }
    .erro { background: #fdecea; color: #b71c1c; }
    .pausado { color: #e65100; font-weight: 600; }
    .ativo { color: #1b5e20; font-weight: 600; }
    .parado { color: #b71c1c; font-weight: 600; }
  </style>
</head>
<body>
  {% if pagina == 'inicio' %}
  <h2>Painel de controle</h2>

  {% if aviso %}<div class="msg ok">{{ aviso }}</div>{% endif %}

  <div class="card">
    Status: <span id="status" class="{{ status_bot }}">{{ status_bot|upper }}</span>
    <div id="etapa" style="margin-top:8px;color:#555">{{ etapa_texto }}</div>
    <div style="margin-top:12px">
      <form method="post" action="{{ url_for('bot_iniciar') }}" style="display:inline">
        <button type="submit">Iniciar bot</button>
      </form>
      <form method="post" action="{{ url_for('bot_parar') }}" style="display:inline">
        <button type="submit" style="background:#b71c1c">Parar bot</button>
      </form>
      <form method="post" action="{{ url_for('fila_limpar') }}" style="display:inline"
            onsubmit="return confirm('Remover da fila do Telegram todas as ofertas pendentes?')">
        <button type="submit" style="background:#888">Limpar fila do Telegram</button>
      </form>
    </div>
  </div>

  <div class="card">
    <div class="stats">
      <div class="stat"><b id="s-total">{{ stats.total }}</b><span>Produtos no banco</span></div>
      <div class="stat"><b id="s-pendentes">{{ stats.pendentes }}</b><span>Prontos para o Telegram</span></div>
      <div class="stat"><b id="s-telegram">{{ stats.publicados_telegram }}</b><span>Publicados no Telegram</span></div>
      <div class="stat"><b id="s-whatsapp">{{ stats.publicados_whatsapp }}</b><span>Marcados no WhatsApp</span></div>
    </div>
    <small id="ultima" style="color:#666"></small>
  </div>

  <div class="card">
    <b>Configuração atual</b>
    <p>Palavras-chave: {{ cfg.palavras_chave|join(', ') }}</p>
    <p>Coleta a cada {{ cfg.coletar_a_cada_minutos }} min, com {{ cfg.palavras_por_ciclo }} palavra(s) por ciclo.</p>
    <p>Publicação a cada {{ cfg.publicar_a_cada_segundos }} segundos.</p>
    <p>Comissão mínima: {{ cfg.min_comissao }} · Vendas mínimas: {{ cfg.min_vendas }} · Avaliação mínima: {{ cfg.min_avaliacao }}</p>
    <a class="botao" href="{{ url_for('configuracoes') }}">Editar configurações</a>
  </div>

  {% else %}
  <h2>Configurações</h2>

  {% if msg %}<div class="msg {{ 'ok' if tipo == 'ok' else 'erro' }}">{{ msg }}</div>{% endif %}

  <form method="post" action="{{ url_for('configuracoes') }}">
    <div class="card">
      <label class="check">
        <input type="checkbox" name="pausado" {% if cfg.pausado %}checked{% endif %}>
        Pausar o bot (para coleta e publicação)
      </label>
    </div>

    <div class="card">
      <label>Palavras-chave <small>(uma por linha)</small></label>
      <textarea name="palavras_chave">{{ cfg.palavras_chave|join('\n') }}</textarea>
      <label>Palavras consultadas por ciclo</label>
      <input type="number" name="palavras_por_ciclo" min="1" max="20" value="{{ cfg.palavras_por_ciclo }}">
      <label>Páginas por palavra <small>(mais páginas = mais chamadas à API)</small></label>
      <input type="number" name="paginas_por_busca" min="1" max="10" value="{{ cfg.paginas_por_busca }}">
      <label>Produtos por página</label>
      <input type="number" name="limite_por_busca" min="1" max="50" value="{{ cfg.limite_por_busca }}">
      <label>Pausa entre requisições (segundos)</label>
      <input type="number" name="pausa_entre_requisicoes" min="1" max="60" value="{{ cfg.pausa_entre_requisicoes }}">
    </div>

    <div class="card">
      <label>Coletar a cada (minutos)</label>
      <input type="number" name="coletar_a_cada_minutos" min="1" max="1440" value="{{ cfg.coletar_a_cada_minutos }}">
      <label>Publicar a cada (segundos)</label>
      <input type="number" name="publicar_a_cada_segundos" min="30" max="86400" value="{{ cfg.publicar_a_cada_segundos }}">
    </div>

    <div class="card">
      <label>Comissão mínima <small>(0,05 = 5%)</small></label>
      <input type="number" step="0.01" name="min_comissao" min="0" max="1" value="{{ cfg.min_comissao }}">
      <label>Vendas mínimas</label>
      <input type="number" name="min_vendas" min="0" value="{{ cfg.min_vendas }}">
      <label>Avaliação mínima <small>(0 a 5 estrelas)</small></label>
      <input type="number" step="0.1" name="min_avaliacao" min="0" max="5" value="{{ cfg.min_avaliacao }}">
    </div>

    <button type="submit">Salvar configurações</button>
    <a class="botao" style="background:#888" href="{{ url_for('inicio') }}">Voltar</a>
  </form>
  {% endif %}

  <script>
    // Atualiza os números do painel inicial a cada 15 segundos, sem recarregar a página.
    function atualizarPainel() {
      if (!document.getElementById('s-total')) return;

      fetch('{{ url_for("api_estatisticas") }}', { cache: 'no-store' })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          document.getElementById('s-total').textContent = d.total;
          document.getElementById('s-pendentes').textContent = d.pendentes;
          document.getElementById('s-telegram').textContent = d.publicados_telegram;
          document.getElementById('s-whatsapp').textContent = d.publicados_whatsapp;

          var status = document.getElementById('status');
          status.textContent = d.status.toUpperCase();
          status.className = d.status;
          document.getElementById('etapa').textContent = d.etapa || '';

          document.getElementById('ultima').textContent =
            'Atualizado às ' + new Date().toLocaleTimeString('pt-BR');
        })
        .catch(function () {
          document.getElementById('ultima').textContent =
            'Sem resposta do painel. Tentando de novo...';
        });
    }

    setInterval(atualizarPainel, 15000);
  </script>
</body>
</html>
"""


def _status_bot(cfg):
    """
    'ativo', 'pausado' ou 'parado'.
    O bot envia sinal de vida a cada minuto. Sem sinal recente, ele está parado.
    """
    sinal = ler_sinal()

    if not sinal or not sinal.get("rodando"):
        return "parado"

    if time.time() - sinal.get("ultimo_sinal", 0) > 150:
        return "parado"

    return "pausado" if cfg["pausado"] else "ativo"


ETAPAS = {
    "postando": "Postando itens no Telegram",
    "coletando": "Buscando novos produtos na API",
    "aguardando": "Aguardando a próxima busca",
}


def _etapa_texto(status):
    """O que o bot está fazendo agora. Só mostra quando ele está ativo."""
    if status != "ativo":
        return ""
    sinal = ler_sinal() or {}
    return ETAPAS.get(sinal.get("etapa"), "")


def _estatisticas(cfg):
    conexao = conectar()
    cursor = conexao.cursor()

    total = cursor.execute("SELECT COUNT(*) FROM products").fetchone()[0]

    publicados_telegram = cursor.execute("""
        SELECT COUNT(*) FROM publications
        WHERE channel = 'telegram' AND status = 'success'
    """).fetchone()[0]

    publicados_whatsapp = cursor.execute("""
        SELECT COUNT(*) FROM publications
        WHERE channel = 'whatsapp' AND status = 'success'
    """).fetchone()[0]

    conexao.close()

    # Mesma regra do bot: palavra atual, nome combinando e sem título parecido já publicado.
    palavras = cfg["palavras_chave"]
    titulos = nomes_publicados("telegram")
    pendentes = [
        c for c in candidatos_publicacao("telegram", limite=500)
        if (c.get("category") or "").lower() in {p.lower() for p in palavras}
        and _combina_com_busca(c["name"], c.get("category") or "")
        and not e_duplicado(c["name"], titulos)
    ]

    return {
        "total": total,
        "pendentes": len(pendentes),
        "publicados_telegram": publicados_telegram,
        "publicados_whatsapp": publicados_whatsapp,
    }


def _ler_inteiro(form, campo, minimo, maximo):
    valor = int(form.get(campo, "").strip())
    if not minimo <= valor <= maximo:
        raise ValueError(f"{campo} deve estar entre {minimo} e {maximo}.")
    return valor


def _ler_decimal(form, campo, minimo, maximo):
    valor = float(form.get(campo, "").strip().replace(",", "."))
    if not minimo <= valor <= maximo:
        raise ValueError(f"{campo} deve estar entre {minimo} e {maximo}.")
    return valor


def _ler_formulario(form):
    palavras = [p.strip() for p in form.get("palavras_chave", "").splitlines() if p.strip()]
    palavras = list(dict.fromkeys(palavras))  # remove repetidas, mantém a ordem

    if not palavras:
        raise ValueError("Informe pelo menos uma palavra-chave.")

    return {
        "pausado": "pausado" in form,
        "palavras_chave": palavras,
        "palavras_por_ciclo": _ler_inteiro(form, "palavras_por_ciclo", 1, 20),
        "paginas_por_busca": _ler_inteiro(form, "paginas_por_busca", 1, 10),
        "limite_por_busca": _ler_inteiro(form, "limite_por_busca", 1, 50),
        "pausa_entre_requisicoes": _ler_inteiro(form, "pausa_entre_requisicoes", 1, 60),
        "coletar_a_cada_minutos": _ler_inteiro(form, "coletar_a_cada_minutos", 1, 1440),
        "publicar_a_cada_segundos": _ler_inteiro(form, "publicar_a_cada_segundos", 30, 86400),
        "min_comissao": _ler_decimal(form, "min_comissao", 0, 1),
        "min_vendas": _ler_inteiro(form, "min_vendas", 0, 10**9),
        "min_avaliacao": _ler_decimal(form, "min_avaliacao", 0, 5),
    }


_processo_bot = None


def _iniciar_bot():
    """Abre o bot em uma janela própria, se ele não estiver rodando."""
    global _processo_bot

    if _processo_bot is not None and _processo_bot.poll() is None:
        return "O bot já está em execução."

    if _status_bot(carregar()) != "parado":
        return "O bot já está em execução."

    limpar_pedido_parar()

    kwargs = {}
    if os.name == "nt":
        # No Windows, abre numa janela nova, para os avisos do bot ficarem visíveis.
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE

    _processo_bot = subprocess.Popen([sys.executable, "-m", "app.main"], cwd=RAIZ, **kwargs)
    return "Bot iniciado. Os avisos aparecem na janela nova que foi aberta."


@app.route("/")
def inicio():
    cfg = carregar()
    status = _status_bot(cfg)
    return render_template_string(
        PAGINA, pagina="inicio", cfg=cfg, stats=_estatisticas(cfg),
        status_bot=status, etapa_texto=_etapa_texto(status),
        aviso=request.args.get("msg"), msg=None, tipo=None
    )


@app.route("/fila/limpar", methods=["POST"])
def fila_limpar():
    cfg = carregar()
    quantidade = descartar_candidatos("telegram", cfg["palavras_chave"])
    return redirect(url_for(
        "inicio",
        msg=f"{quantidade} oferta(s) removida(s) da fila do Telegram.",
    ))


@app.route("/bot/iniciar", methods=["POST"])
def bot_iniciar():
    return redirect(url_for("inicio", msg=_iniciar_bot()))


@app.route("/bot/parar", methods=["POST"])
def bot_parar():
    pedir_parada()
    return redirect(url_for(
        "inicio",
        msg="Pedido de parada enviado. O bot para em até 1 minuto.",
    ))


@app.route("/api/estatisticas")
def api_estatisticas():
    cfg = carregar()
    status = _status_bot(cfg)
    return jsonify({
        "status": status,
        "etapa": _etapa_texto(status),
        "pausado": cfg["pausado"],
        **_estatisticas(cfg),
    })


@app.route("/configuracoes", methods=["GET", "POST"])
def configuracoes():
    cfg = carregar()
    msg = None
    tipo = None

    if request.method == "POST":
        try:
            cfg = _ler_formulario(request.form)
            salvar(cfg)
            msg = "Configurações salvas. O bot aplica no próximo ciclo."
            tipo = "ok"
        except ValueError as erro:
            msg = f"Não salvei: {erro}"
            tipo = "erro"
        except Exception as erro:
            msg = f"Não salvei, verifique os valores: {erro}"
            tipo = "erro"

    return render_template_string(
        PAGINA, pagina="config", cfg=cfg, stats=None, msg=msg, tipo=tipo
    )


if __name__ == "__main__":
    # Só acessível no seu computador.
    app.run(host="127.0.0.1", port=5001, debug=False)