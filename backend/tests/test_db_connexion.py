import sys
sys.path.append(".")

from app.db.database import engine 

try : 
    with engine.connect() as conn :
        print("connected succesfully to the db")
except Exception as e:
    print(f"failed to connect to db {e}")