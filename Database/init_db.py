from connection import engine, Base
import models

Base.metadata.create_all(bind=engine)
print("Таблицы в PostgreSQL успешно созданы!")