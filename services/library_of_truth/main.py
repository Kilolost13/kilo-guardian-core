from fastapi import FastAPI, HTTPException, Header, Depends, Response
from sqlmodel import SQLModel, create_engine, Session, Field, select
from typing import Optional, List
import os
import glob
import mimetypes
import pdfplumber
import re
from bs4 import BeautifulSoup

# Entry model
class Entry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    book: str  # PDF filename
    page: int  # Page number
    chunk: int = 0  # Chunk number within page
    text: str  # Extracted text content
    title: str = ""
    content: str = ""
    category: str = "general"
    tags: str = ""
    created_at: str = ""

def is_admin(x_admin_key: str = Header(None)):
    admin_key = os.getenv("ADMIN_KEY")
    # if no local ADMIN_KEY configured, allow if no header provided; otherwise consult gateway
    if not admin_key:
        token = x_admin_key
        if not token:
            return True
        # gateway validation disabled - no gateway client available
        raise HTTPException(status_code=403, detail="Admin access required")
    # local ADMIN_KEY set -> strict equality
    if x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Admin access required")
    return True


db_url = "sqlite:////data/library_of_truth.db"
engine = create_engine(db_url, echo=False)



from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Ensure /data directory exists
        os.makedirs("/data", exist_ok=True)

        # Create database tables
        SQLModel.metadata.create_all(engine)

        # NOTE: Auto-parsing disabled to allow faster startup
        # Use POST /parse_books to manually trigger parsing of PDFs and HTML files
        print("[Library of Truth] Service started. Use POST /parse_books to parse library files.")
    except Exception as e:
        print(f"[Library of Truth] Startup error: {e}")
    yield


app = FastAPI(title="Library of Truth Service", lifespan=lifespan)

# Health check endpoint
@app.get("/status")
@app.get("/health")
def status():
    return {"status": "ok"}

BOOKS_DIR = os.path.join(os.path.dirname(__file__), "books")

# startup handled by lifespan



# List all PDFs in the books directory
@app.get("/books")
def list_books():
    pdfs = glob.glob(os.path.join(BOOKS_DIR, "*.pdf"))
    return [{"filename": os.path.basename(f)} for f in pdfs]


# Download a specific PDF
@app.get("/books/{filename}")
def get_book(filename: str):
    file_path = os.path.join(BOOKS_DIR, filename)
    if not os.path.isfile(file_path) or not file_path.endswith(".pdf"):
        raise HTTPException(status_code=404, detail="Book not found")
    with open(file_path, "rb") as f:
        data = f.read()
    return Response(content=data, media_type=mimetypes.guess_type(file_path)[0] or "application/pdf")

# --- HTML Parsing ---
def parse_html_file(html_file: str, session: Session):
    """Parse a single HTML file and store chunks in database"""
    book = os.path.basename(html_file)

    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract text from body, removing script and style tags
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text from body
        body = soup.find('body')
        if not body:
            return

        text = body.get_text(separator='\n', strip=True)

        # Split into chunks (paragraphs or every 500 chars)
        chunks = re.split(r'\n\s*\n', text) if text else []
        if not chunks:
            chunks = [text[i:i+500] for i in range(0, len(text), 500)] if text else []

        # Store chunks (use page=1 for HTML files since they don't have pages)
        for chunk_num, chunk in enumerate(chunks):
            chunk = chunk.strip()
            if chunk:
                entry = Entry(book=book, page=1, chunk=chunk_num, text=chunk)
                session.add(entry)
    except Exception as e:
        print(f"[Library] Error parsing HTML {book}: {e}")

# --- PDF Parsing and Chunking ---
def parse_and_store_pdfs():
    with Session(engine) as session:
        # Parse PDF files
        pdf_files = glob.glob(os.path.join(BOOKS_DIR, "*.pdf"))
        print(f"[Library] Found {len(pdf_files)} PDF files to parse")

        for idx, pdf_file in enumerate(pdf_files, 1):
            book = os.path.basename(pdf_file)
            print(f"[Library] Parsing PDF {idx}/{len(pdf_files)}: {book}")
            try:
                with pdfplumber.open(pdf_file) as pdf:
                    total_pages = len(pdf.pages)
                    print(f"[Library]   Pages in {book}: {total_pages}")
                    for page_num, page in enumerate(pdf.pages, 1):
                        if page_num % 50 == 0:
                            print(f"[Library]   Processing page {page_num}/{total_pages} of {book}")
                        text = page.extract_text() or ""
                        # Split into chunks (paragraphs or every 500 chars)
                        chunks = re.split(r'\n\s*\n', text) if text else []
                        if not chunks:
                            chunks = [text[i:i+500] for i in range(0, len(text), 500)] if text else []
                        for chunk_num, chunk in enumerate(chunks):
                            chunk = chunk.strip()
                            if chunk:
                                entry = Entry(book=book, page=page_num, chunk=chunk_num, text=chunk)
                                session.add(entry)
                print(f"[Library]   Completed parsing {book}")
            except Exception as e:
                print(f"[Library]   ERROR parsing {book}: {e}")
                continue

        # Parse HTML files (recursively search subdirectories)
        html_files = glob.glob(os.path.join(BOOKS_DIR, "**/*.html"), recursive=True)
        print(f"[Library] Found {len(html_files)} HTML files to parse")

        for idx, html_file in enumerate(html_files, 1):
            print(f"[Library] Parsing HTML {idx}/{len(html_files)}: {os.path.basename(html_file)}")
            parse_html_file(html_file, session)

        session.commit()
        print("[Library] ✓ All files parsed successfully")

# Endpoint to trigger parsing (admin only)
@app.post("/parse_books", dependencies=[Depends(is_admin)])
def parse_books():
    parse_and_store_pdfs()
    return {"status": "parsed"}

# --- Search Endpoint ---
@app.get("/search")
def search_books(q: str, limit: int = 5) -> List[dict]:
    # Simple keyword search
    with Session(engine) as session:
        stmt = select(Entry).where(Entry.text.ilike(f"%{q}%")).limit(limit)
        results = session.exec(stmt).all()
        return [
            {"book": e.book, "page": e.page, "text": e.text}
            for e in results
        ]

@app.post("/", dependencies=[Depends(is_admin)])
def add_entry(e: Entry):
    with Session(engine) as session:
        session.add(e)
        session.commit()
        session.refresh(e)
        return e
