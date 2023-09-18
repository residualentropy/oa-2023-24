from fastapi import FastAPI
from pydantic import BaseModel
import time, secrets, hashlib, base64, os

app = FastAPI()

SECRET = os.environ["BACKEND_WRITE_SECRET"].encode('utf-8')


class Temps(BaseModel):
  unixts: int  # Unix Timestamp
  readings: dict[str, float]  # Temperatures


recent_count = 20 * 60
temps_recent = []


class TempUpdate(BaseModel):
  temps: Temps
  token: int


AUTH_PERIOD_LENGTH = 30


def current_period():
  return int(time.time() // AUTH_PERIOD_LENGTH)


@app.get("/")
async def root():
  return {"help": "This is a backend server. See /docs for endpoints. "}


saved_period = None
saved_challenge = None
saved_resp = None
tokens_granted = []


def compute_challenge_response(challenge: bytes) -> str:
  return base64.urlsafe_b64encode(
      hashlib.sha384(challenge + SECRET).digest()).decode('utf-8')


@app.get("/auth/get_challenge")
async def get_challenge():
  global saved_period, saved_challenge, saved_resp
  period = current_period()
  if period != saved_period:
    saved_challenge = f"{period}-{secrets.randbits(256)}".encode('utf-8')
    saved_period = period
    saved_resp = compute_challenge_response(saved_challenge)
  return {"challenge": saved_challenge}


@app.get("/auth/get_token")
async def get_token(challenge: str, response: str):
  if challenge.encode('utf-8') != saved_challenge:
    return {"ok": False, "problem": "challenge-expired", "should-retry": True}
  if response != saved_resp:
    return {
        "ok": False,
        "problem": "incorrect-response",
        "should-retry": False
    }
  token = secrets.randbits(256)
  tokens_granted.append(token)
  return {"ok": True, "token": token}


def has_auth_write(token: int):
  return token in tokens_granted


@app.post("/api/w/temps")
async def update_temperatures(update: TempUpdate):
  if not has_auth_write(update.token):
    print("/!\\ GOT BAD TOKEN!!!!")
    return {"w-ok": False, "auth-error": "bad-token"}
  temps = update.temps
  print(temps)
  temps_recent.append(temps)
  while len(temps_recent) > recent_count:
    temps_recent.pop(0)
  return {"w-ok": True}


@app.get("/api/r/temps_recent")
async def get_recent_temperatures():
  return {
      "recent": temps_recent,
  }


@app.get("/api/r/sensor_names")
async def get_sensor_names():
  return {
      "names": {
          "a": "Evaporator",
          "b": "Top Shelf, Back Left",
          "c": "Top Shelf, Front Right",
          "d": "Drawer, Front Right, At Top",
          "e": "Inside Door",
      },
  }

