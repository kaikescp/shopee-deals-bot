
import sqlite3
from pathlib import Path

# Caminho absoluto do projeto
BASE_DIR = Path(__file__).resolve().parents[2]

# Diretório onde ficará o banco
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATA_DIR / "shopee_deals.db"


def conectar():
    conexao = sqlite3.connect(DATABASE_PATH)

    conexao.row_factory = sqlite3.Row

    return conexao
