from flask import Flask, redirect, render_template_string, url_for

from app.database.repository import registrar_publicacao
from app.whatsapp.formatter import formatar_mensagem
from app.whatsapp.queue import CANAL, fila_pendente

app = Flask(__name__)

PAGINA = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fila de ofertas</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 720px; margin: 0 auto;
           padding: 16px; background: #f2f2f2; color: #222; }
    h2 { margin-top: 8px; }
    .card { background: #fff; border-radius: 10px; padding: 14px;
            margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,.1); overflow: hidden; }
    .card img { float: right; width: 110px; height: 110px; object-fit: cover;
                margin-left: 12px; border-radius: 8px; }
    .nome { font-weight: 600; }
    .meta { color: #666; font-size: 14px; margin: 4px 0 8px; }
    textarea { width: 100%; min-height: 170px; font-size: 14px; box-sizing: border-box;
               padding: 8px; border: 1px solid #ccc; border-radius: 6px; }
    button { padding: 9px 14px; border: 0; border-radius: 6px; cursor: pointer;
             font-size: 14px; margin: 8px 6px 0 0; }
    .copiar { background: #25d366; color: #fff; }
    .enviado { background: #e0e0e0; }
    .vazio { text-align: center; color: #666; padding: 40px 0; }
  </style>
</head>
<body>
  <h2>Fila de ofertas ({{ total }})</h2>

  {% for o in ofertas %}
  <div class="card">
    {% if o.image_url %}<img src="{{ o.image_url }}" alt="">{% endif %}
    <div class="nome">{{ o.name }}</div>
    <div class="meta">{{ '%.0f' % o.discount }}% OFF · {{ o.category }}</div>
    <textarea id="t{{ o.id }}" readonly>{{ o.mensagem }}</textarea>
    <div>
      <button class="copiar" onclick="copiar('t{{ o.id }}', this)">Copiar texto</button>
      <form method="post" action="{{ url_for('marcar_enviado', produto_id=o.id) }}" style="display:inline">
        <button class="enviado" type="submit">Marcar como enviado</button>
      </form>
    </div>
  </div>
  {% else %}
  <div class="vazio">Nenhuma oferta pendente agora. O bot continua coletando.</div>
  {% endfor %}

  <script>
    function copiar(id, botao) {
      const campo = document.getElementById(id);
      campo.select();
      navigator.clipboard.writeText(campo.value).then(function () {
        botao.textContent = "Copiado!";
        setTimeout(function () { botao.textContent = "Copiar texto"; }, 1500);
      });
    }
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    ofertas = fila_pendente(limite=50)

    for oferta in ofertas:
        oferta["mensagem"] = formatar_mensagem(oferta)

    return render_template_string(PAGINA, ofertas=ofertas, total=len(ofertas))


@app.route("/enviado/<produto_id>", methods=["POST"])
def marcar_enviado(produto_id):
    # Registra no canal WhatsApp. Essa oferta sai da fila.
    registrar_publicacao(produto_id, CANAL, None)
    return redirect(url_for("index"))


if __name__ == "__main__":
    # Só acessível no seu computador.
    app.run(host="127.0.0.1", port=5000, debug=False)