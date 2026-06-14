from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

#URL di connessione: dialect+driver://username:password@host:port/database
SQLALCHEMY_DATABASE_URL = "mariadb+mariadbconnector://user:password@database:3306/minerva"

#creazione del motore del database
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#classe base da cui erediteranno tutte le tabelle
Base = declarative_base()

#funzione "dependency" che FastAPI userà per aprire e chiudere la connessione ad ogni richiesta API
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()