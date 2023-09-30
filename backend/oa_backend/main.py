from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time, secrets, hashlib, base64, os, pickle

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
)

SECRET = os.environ["BACKEND_WRITE_SECRET"].encode('utf-8')


class Temps(BaseModel):
  unixts: int  # Unix Timestamp
  readings: dict[str, float]  # Temperatures


average = lambda xs: sum(xs) / len(xs)


def average_temps(xs: list[Temps]) -> Temps:
  return Temps(unixts=xs[0].unixts,
               readings={
                   key: average([x.readings[key] for x in xs])
                   for key in xs[0].readings.keys()
               })


recent_count = 20 * 60
temps_recent = []

downsampling_amt = 10
downsampling_window = []
last_2h_count = (120 * 60) / downsampling_amt
last_2h_temps = []


def save_data():
  global temps_recent, last_2h_temps
  with open("snapshot.pkl", "wb") as f:
    pickle.dump(
        {
            "temps_recent": temps_recent,
            "last_2h_temps": last_2h_temps,
        }, f)


def try_restore_data():
  global temps_recent, last_2h_temps
  try:
    with open("snapshot.pkl", "rb") as f:
      obj = pickle.load(f)
      temps_recent = obj["temps_recent"]
      last_2h_temps = obj["last_2h_temps"]
  except:
    print("FAILED TO RESTORE (may just be first startup)")


try_restore_data()


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
  global downsampling_window
  downsampling_window.append(temps)
  if len(downsampling_window) >= downsampling_amt:
    last_2h_temps.append(average_temps(downsampling_window))
    downsampling_window = []
  while len(last_2h_temps) > last_2h_count:
    last_2h_temps.pop(0)
  save_data()
  return {"w-ok": True}


@app.get("/api/r/temps_recent")
async def get_recent_temperatures():
  return {
      "recent": temps_recent,
  }


@app.get("/api/r/temp_data")
async def get_temperature_data():
  return {
      "downsampled": last_2h_temps,
      "duration": "2 Hours",
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

