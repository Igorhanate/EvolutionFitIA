"""
Script local para ativar assinatura de teste.
Uso: DATABASE_URL=<url> python scripts/activate_test.py <telefone> [plano]

Exemplo:
  DATABASE_URL=postgresql://... python scripts/activate_test.py 5511999328525 anual
"""
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.usuario import Usuario
from app.models.assinatura import Assinatura

PLAN_DURATIONS = {"trimestral": 90, "anual": 365}


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/activate_test.py <telefone> [anual|trimestral]")
        sys.exit(1)

    phone = "".join(filter(str.isdigit, sys.argv[1]))
    plano = sys.argv[2] if len(sys.argv) > 2 else "anual"
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        print("Erro: variável DATABASE_URL não definida")
        sys.exit(1)

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    user = db.query(Usuario).filter(Usuario.telefone == phone).first()
    if not user:
        user = Usuario(telefone=phone, nome="Teste")
        db.add(user)
        db.flush()
        print(f"Usuário criado: id={user.id}")
    else:
        print(f"Usuário existente: id={user.id}")

    hoje = date.today()
    duracao = PLAN_DURATIONS.get(plano, 365)
    transaction_id = f"TEST-{phone}"

    existing = db.query(Assinatura).filter(Assinatura.hotmart_transaction_id == transaction_id).first()
    if existing:
        existing.data_fim = hoje + timedelta(days=duracao)
        existing.status = "ativo"
        print(f"Assinatura atualizada: id={existing.id}, plano={plano}, válida até {existing.data_fim}")
    else:
        assinatura = Assinatura(
            user_id=user.id,
            plano=plano,
            data_inicio=hoje,
            data_fim=hoje + timedelta(days=duracao),
            status="ativo",
            hotmart_transaction_id=transaction_id,
        )
        db.add(assinatura)
        print(f"Assinatura criada: plano={plano}, válida até {hoje + timedelta(days=duracao)}")

    db.commit()
    db.close()
    print("Concluído.")


if __name__ == "__main__":
    main()
