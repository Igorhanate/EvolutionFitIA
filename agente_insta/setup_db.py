from sqlalchemy import inspect
from agente_insta.db import engine, Base
from agente_insta import modelos  # registra o modelo


def main():
    Base.metadata.create_all(bind=engine)
    nomes = inspect(engine).get_table_names()
    if "posts_gerados" in nomes:
        print("OK: tabela 'posts_gerados' existe no banco.")
    else:
        print("ERRO: tabela nao encontrada.")


if __name__ == "__main__":
    main()
