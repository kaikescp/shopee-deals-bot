# Shopee Deals Bot

Bot em Python que busca ofertas de produtos na API de afiliados da Shopee, filtra pelos critérios definidos e publica no Telegram. Também monta uma fila de ofertas para envio manual no WhatsApp.

## Como funciona

1. **Coleta**: a cada intervalo configurado, o bot consulta a API de afiliados da Shopee usando palavras-chave em rodízio. Cada palavra retorna até um número limite de produtos.
2. **Filtro de relevância**: só entram produtos cujo nome contém todas as palavras da busca (ignorando plurais e stopwords), com comissão, vendas e avaliação mínimas definidas no painel.
3. **Filtro de repetidos**: o bot compara o título de cada candidato com os já publicados (similaridade de palavras, índice de Jaccard). Títulos parecidos não são postados de novo.
4. **Publicação**: enquanto houver ofertas na fila, o bot publica uma por vez no Telegram, com link de afiliado, e registra a publicação no banco de dados.
5. **Fila do WhatsApp**: as mesmas ofertas ficam disponíveis numa página local, com a mensagem pronta para copiar.

## Requisitos

- Python 3.12 (o projeto usa arquivos `.pyc` de 3.12)
- Pacotes: `flask`, `requests`, `python-dotenv`
- Conta de afiliado da Shopee com App ID e App Secret
- Bot do Telegram criado com o BotFather e um chat ou canal de destino

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install flask requests python-dotenv
```

## Configuração

1. Copie `.env.example` para `.env` e preencha:

| Variável | Descrição |
|---|---|
| `SHOPEE_APP_ID` | App ID da API de afiliados |
| `SHOPEE_APP_SECRET` | App Secret da API de afiliados |
| `TELEGRAM_BOT_TOKEN` | Token do bot do Telegram |
| `TELEGRAM_CHAT_ID` | ID do chat ou canal de destino |
| `MIN_COMISSAO`, `MIN_VENDAS`, `MIN_AVALIACAO` | Critérios mínimos (opcionais; também podem ser ajustados no painel) |
| `MODO_TESTE` | `1` adiciona aviso de teste nas mensagens |
| `LIMIAR_SIMILARIDADE` | Sensibilidade do filtro de repetidos (padrão `0.45`) |

2. O arquivo `config.json` é criado e atualizado pelo painel. Ele guarda palavras-chave, intervalos e critérios.

**Nunca commite o `.env`.** Ele contém credenciais de API e do Telegram.

## Executando

O bot e os painéis são processos separados:

```bash
# Bot (coleta e publicação)
python -m app.main

# Painel de controle: http://127.0.0.1:5001
python -m app.controle_painel

# Fila de ofertas para WhatsApp: http://127.0.0.1:5000
python -m app.whatsapp.painel
```

No painel de controle você pode pausar o bot, alterar palavras-chave e critérios, e parar o processo. As mudanças valem sem reiniciar, porque o bot relê o `config.json` a cada ciclo.

## Estrutura

```
app/
├── main.py                 # Ciclo principal: coleta e publicação
├── config.py               # Leitura e gravação do config.json e dos sinais de status
├── collectors/             # Consulta à API de afiliados da Shopee
├── affiliate/              # Autenticação (assinatura SHA256) e geração de links
├── filters/                # Filtro de repetidos (e filtro de desconto, não usado no ciclo atual)
├── telegram/               # Montagem e envio das mensagens no Telegram
├── whatsapp/               # Fila e formatação para WhatsApp, com página local
├── database/               # SQLite: produtos, publicações e mensagens enviadas
└── controle_painel.py      # Painel de controle (Flask)
```

Os arquivos de dados (`data/*.db`, `bot_status.json`, `rodizio.json`) são criados em execução e não entram no repositório.

## Limitações conhecidas

- O WhatsApp não é publicado automaticamente. A página de fila gera o texto e você envia manualmente.
- A API de afiliados da Shopee tem limite de requisições. Quando o limite é atingido, o bot aguarda e retoma a partir da palavra-chave que ficou pendente.
- Os nomes dos campos da mutation de geração de links ainda não foram confirmados com a documentação oficial e devem ser validados antes de uso em produção.

## Aviso

Este projeto é uma ferramenta de estudo e automação pessoal. Respeite os termos de uso da Shopee, do Telegram e do WhatsApp, e as regras do programa de afiliados.
