from app.database.connection import conectar


def criar_tabelas():
    conexao = conectar()
    cursor = conexao.cursor()

    try:
        # Tabela de produtos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                original_price REAL NOT NULL,
                category TEXT,
                product_url TEXT,
                affiliate_url TEXT,
                image_url TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Verifica se a tabela de publicações já existe
        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'publications'
        """)

        tabela_existe = cursor.fetchone() is not None

        if not tabela_existe:
            cursor.execute("""
                CREATE TABLE publications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    external_message_id TEXT,
                    published_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,

                    UNIQUE(product_id, channel),

                    FOREIGN KEY (product_id)
                    REFERENCES products(id)
                )
            """)

        else:
            cursor.execute("PRAGMA table_info(publications)")
            colunas = [coluna[1] for coluna in cursor.fetchall()]

            # Migra a estrutura antiga para a nova
            if "channel" not in colunas:
                cursor.execute("PRAGMA foreign_keys = OFF")
                cursor.execute("BEGIN")

                cursor.execute("""
                    CREATE TABLE publications_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id TEXT NOT NULL,
                        channel TEXT NOT NULL,
                        external_message_id TEXT,
                        published_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        status TEXT NOT NULL,

                        UNIQUE(product_id, channel),

                        FOREIGN KEY (product_id)
                        REFERENCES products(id)
                    )
                """)

                cursor.execute("""
                    INSERT INTO publications_new (
                        id,
                        product_id,
                        channel,
                        external_message_id,
                        published_at,
                        status
                    )
                    SELECT
                        id,
                        product_id,
                        'telegram',
                        telegram_message_id,
                        published_at,
                        status
                    FROM publications
                """)

                cursor.execute("DROP TABLE publications")
                cursor.execute("""
                    ALTER TABLE publications_new
                    RENAME TO publications
                """)

                conexao.commit()
                cursor.execute("PRAGMA foreign_keys = ON")

        # Histórico de cada mensagem enviada ao grupo, com o conteúdo completo.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mensagens_enviadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                external_message_id TEXT,
                enviado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                nome TEXT,
                categoria TEXT,
                preco REAL,
                imagem_url TEXT,
                link_produto TEXT,
                link_afiliado TEXT,
                texto TEXT NOT NULL,

                FOREIGN KEY (product_id)
                REFERENCES products(id)
            )
        """)

        conexao.commit()

        print("Banco de dados inicializado!")
        print("Estrutura de publicações preparada para múltiplos canais.")

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()