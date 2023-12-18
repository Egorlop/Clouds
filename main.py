from datetime import datetime, timedelta
from secrets import token_urlsafe
import clickhouse_connect
import jwt
from fastapi import FastAPI, Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")

client = clickhouse_connect.get_client(host='localhost')
client.command('CREATE DATABASE IF NOT EXISTS admin_db')
client.command('USE admin_db')
client.command('''create table if not exists users
    (
        username Nullable(String),
        password Nullable(String)
    )
    engine = Memory''')

app = FastAPI()
auth = HTTPBasic()

def jwt_token(username: str):
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(days=1)
    }
    token = jwt.encode(payload, "secret", algorithm="HS256")
    return token

def verify_jwt(token: str):
    try:
        payload = jwt.decode(token, "secret", algorithms=["HS256"])
        username = payload["sub"]
        return username
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_client(credentials: HTTPBasicCredentials = Depends(auth)):
    client = clickhouse_connect.get_client(host='localhost')
    client.command('USE admin_db')
    user = client.command(f"SELECT * FROM users where username = '{credentials.username}'")
    if type(user) is not list or user[1] != credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user

def create_db(user):
    dbname = f"db_{user[0]}_{token_urlsafe(8)}"
    dbpass = token_urlsafe(16)
    client = clickhouse_connect.get_client(host='localhost')
    client.command(f"CREATE DATABASE {dbname}")
    client.command(f"CREATE USER {dbname} IDENTIFIED BY '{dbpass}'")
    client.command(f"GRANT ALL ON {dbname} TO {dbname}")
    return dbname, dbname, dbpass

@app.post("/registration")
def register(credentials: HTTPBasicCredentials = Depends(auth)):
    client = clickhouse_connect.get_client(host='localhost')
    client.command('USE admin_db')
    users = client.command(f"SELECT * FROM users where username = '{credentials.username}'")
    if type(users) is list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client exists",
        )
    client.command('USE admin_db')
    users = client.command(f'''insert into users values('{credentials.username}','{credentials.password}')''')
    return {"message": "Client registered"}


@app.post("/authorization")
def authorize(user=Depends(verify_client)):
    token = jwt_token(user[0])
    return {"message": "User authorized", "Client": user[0], "Token": token}

@app.get("/create_db")
def create_database_for_user(token: str = Header(None)):
    username = verify_jwt(token)
    client = clickhouse_connect.get_client(host='localhost')
    client.command('USE admin_db')
    user = client.command(f"SELECT * FROM users where username = '{username}'")
    if type(user) is not list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    dbname, dbuser, dbpass = create_db(user)
    return {"message": "Database created", "db": dbname, "client": dbuser, "password": dbpass}


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})