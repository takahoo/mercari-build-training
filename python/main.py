import json
import os
import logging
import pathlib
import logging
import hashlib
import sqlite3
from fastapi import FastAPI, Form, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import List, Optional


app = FastAPI()
items_file = "items.json"

UPLOAD_FOLDER = "images"

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

logging.basicConfig(level=logging.DEBUG)

# Define the path to the images & sqlite3 database
images = pathlib.Path(__file__).parent.resolve() / "images"
db = pathlib.Path(__file__).parent.resolve() / "db" / "mercari.sqlite3"
database_path = "/app/db/mercari.sqlite3"
db_dir = os.path.dirname(database_path)
os.makedirs(db_dir, exist_ok=True)

# Ensure images directory exists
images_dir = pathlib.Path("images")
images_dir.mkdir(parents=True, exist_ok=True)

def get_db():
    conn = sqlite3.connect(database_path, check_same_thread=False)  # Use database_path
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    try:
        yield conn
    finally:
        conn.close()


# STEP 5-1: set up the database connection
def setup_database():
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            image_name TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_database()
    yield


app = FastAPI(lifespan=lifespan)

logger = logging.getLogger("uvicorn")
logger.level = logging.INFO
images = pathlib.Path(__file__).parent.resolve() / "images"

origins = [os.environ.get("FRONT_URL", "http://localhost:3000")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

class HelloResponse(BaseModel):
    message: str
    
class Item(BaseModel):
    name: str
    category: str
    image_name: str

@app.get("/", response_model=HelloResponse)
def hello():
    return HelloResponse(**{"message": "Hello, world!"})

class AddItemResponse(BaseModel):
    message: str

def insert_item(item: Item, db: sqlite3.Connection):
    # STEP 4-1: add an implementation to store an item
    cursor=db.cursor()
    
    #カテゴリがあるか確認
    cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (item.category,))
    cursor.execute("SELECT id FROM categories WHERE name = ?", (item.category,))
    category_id = cursor.fetchone()[0]
    
    cursor.execute(
        "INSERT INTO items (name, category_id, image_name) VALUES (?, ?, ?)",
        (item.name, category_id, item.image_name),
    )
    db.commit()
    
 #   try:
  #      with open("items.json", "r") as f:
#           data = json.load(f)
#    except (FileNotFoundError, json.JSONDecodeError):
#        data = {"items": []}
#
#        # Append new item
#    data["items"].append({"name": item.name, "category": item.category, "image_name": item.image_name})
#
#        # Write back to the file
#    with open("items.json", "w", encoding="utf-8") as f:
#        json.dump(data, f, indent=2, ensure_ascii=False)

# add_item is a handler to add a new item for POST /items .
@app.post("/items")
async def add_item(
    name: str = Form(...),
    category: str = Form(...),
    image: Optional[UploadFile] = File(None),
    db: sqlite3.Connection = Depends(get_db),
):    
    image_name = ""  # Default to empty string if no image is uploaded
    if image is not None:
        file_bytes = await image.read()
        image_hash = hashlib.sha256(file_bytes).hexdigest()
        image_name = f"{image_hash}.jpg"
        image_path = images_dir / image_name
        with open(image_path, "wb") as f:
            f.write(file_bytes)#

    if not name or not category:
        raise HTTPException(status_code=400, detail="name is required")

    insert_item(Item(name=name, category=category, image_name=image_name), db)  

    return AddItemResponse(**{"message": f"item received: {name}"})


# get_image is a handler to return an image for GET /images/{filename} .
@app.get("/image/{image_name}")
async def get_image(image_name:str):
    # Create image path
    image = images / image_name

    if not image_name.endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Image path does not end with .jpg")

    if not image.exists():
        logger.debug(f"Image not found: {image}")
        image = images / "default.jpg"

    return FileResponse(image)
        
@app.get("/items")
def get_all_items(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()

    cursor.execute("SELECT items.id, items.name, categories.name AS category, items.image_name FROM items INNER JOIN categories ON items.category_id = categories.id")
    items = cursor.fetchall()
    return {"items": [dict(item) for item in items]}

@app.get("/items/{item_id}")
def get_item(item_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT items.id, items.name, categories.name AS category, items.image_name FROM items INNER JOIN categories ON items.category_id = categories.id WHERE items.id = ?", (item_id,))
    item = cursor.fetchone()

    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    return dict(item)

