from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import User, Token, SessionLocal
from pydantic import BaseModel
from passlib.context import CryptContext
import datetime
from jose import jwt
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

TOKEN_EXPIRATION_MINUTES = 60
secret_key = os.getenv("SECRET_KEY")

pass_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserCreate(BaseModel):
    username: str
    password: str


class SignupResponse(BaseModel):
    message: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/signup/", response_model=SignupResponse)
async def signup(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username Already Registered")
    hashed_password = pass_context.hash(user.password)
    db_user = User(username=user.username, password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User Registered Successfully"}


@app.post("/login/")
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user is None or not pass_context.verify(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Incorrect Username or Password")
    token = Token(token=generate_token(db_user), user_id=db_user.id)
    db.add(token)
    db.commit()
    return {"access_token": token.token, "token_type": "bearer"}


def generate_token(user: User):
    expiration = datetime.datetime.utcnow() + datetime.timedelta(
        minutes=TOKEN_EXPIRATION_MINUTES
    )
    token = jwt.encode({"sub": user.username, "exp": expiration}, secret_key)
    return token


@app.post("/logout/")
def logout(token: str, db: Session = Depends(get_db)):
    db_token = db.query(Token).filter(Token.token == token).first()
    if db_token:
        db.delete(db_token)
        db.commit()
    return {"message": "User Logged Out"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
