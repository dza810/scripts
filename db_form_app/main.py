
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

app = FastAPI()

# Get the directory of the current file to build absolute paths
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
DB_FILE = BASE_DIR / "database.json"

def read_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def write_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

class Customer(BaseModel):
    name: str
    email: str

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    customers = read_db()
    return templates.TemplateResponse(
        request=request, name="index.html", context={"customers": customers}
    )

@app.get("/customers")
def get_customers():
    return read_db()

@app.post("/customers")
async def create_customer(customer: Customer):
    db_data = read_db()
    db_data.append(customer.model_dump())
    write_db(db_data)
    return customer

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
