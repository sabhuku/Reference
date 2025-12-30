"""
Dummy College Catalog API

A simple API that simulates a college library catalog for development and testing.
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import random
from datetime import datetime, timedelta
import uvicorn
import os

app = FastAPI(
    title="Dummy College Catalog API",
    description="A mock API for testing college catalog integration",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample data for the catalog
SAMPLE_BOOKS = [
    {
        "id": f"BOOK-{i:04d}",
        "title": f"Sample Book {i} Title",
        "authors": [f"Author {i} Lastname", f"Co-Author {i} Surname"],
        "publication_year": 2020 + (i % 4),
        "item_type": "Book",
        "call_number": f"QA76.{7000 + i} .S65 {2020 + (i % 4)}",
        "available_copies": random.randint(1, 5),
        "total_copies": random.randint(2, 8),
        "location": random.choice(["Main Library, Floor 2", "Science Library, Floor 1"]),
        "description": f"This is a sample book description for testing purposes. Book {i} covers important topics in the field.",
        "subjects": ["Computer Science", "Testing", f"Topic {i % 5}"],
        "isbn": f"978-{random.randint(1000000000, 9999999999)}",
        "publisher": "Sample University Press",
        "edition": f"{i % 5 + 1}st Edition" if (i % 5 + 1) == 1 else f"{i % 5 + 1}th Edition",
        "language": "English",
        "pages": str(random.randint(100, 800)),
        "added_date": (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat()
    }
    for i in range(1, 101)  # Generate 100 sample books
]

# Add some variety to the items
for i in range(20, 40):
    SAMPLE_BOOKS[i]["item_type"] = "E-Book"
    SAMPLE_BOOKS[i]["available_copies"] = 1  # Unlimited e-books
    SAMPLE_BOOKS[i]["total_copies"] = 1
    SAMPLE_BOOKS[i]["location"] = "Online Access"

# Add some journals and articles
SAMPLE_JOURNALS = [
    {
        "id": f"JOUR-{i:04d}",
        "title": f"Journal of Sample Studies Vol. {i}, No. {j}",
        "authors": [f"Researcher {i} Name", f"Co-Researcher {j} Surname"],
        "publication_year": 2020 + (i % 4),
        "item_type": "Journal",
        "volume": i % 10 + 1,
        "issue": j + 1,
        "pages": f"{i*10+1}-{i*10+15}",
        "issn": f"1234-{5678 + i:04d}",
        "available_copies": 1,
        "total_copies": 1,
        "location": "Periodicals Section, Floor 3",
        "description": f"Academic journal article on various topics in sample studies.",
        "subjects": ["Research", "Academic", f"Field {(i % 5) + 1}"],
        "publisher": "Academic Press",
        "language": "English",
        "added_date": (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat()
    }
    for i in range(1, 21)
    for j in range(1, 5)  # 4 issues per volume
]

# Combine all items
CATALOG_ITEMS = SAMPLE_BOOKS + SAMPLE_JOURNALS

# Models
class CatalogItem(BaseModel):
    id: str
    title: str
    authors: List[str]
    publication_year: int
    item_type: str
    available_copies: int
    total_copies: int
    location: str
    description: str
    subjects: List[str]
    added_date: str
    # Additional fields that might be present
    call_number: Optional[str] = None
    isbn: Optional[str] = None
    issn: Optional[str] = None
    volume: Optional[int] = None
    issue: Optional[int] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    edition: Optional[str] = None
    language: Optional[str] = None

class SearchResults(BaseModel):
    total: int
    page: int
    per_page: int
    items: List[CatalogItem]

# Routes
@app.get("/")
async def read_root():
    return {"message": "Welcome to the Dummy College Catalog API"}

@app.get("/search", response_model=SearchResults)
async def search_items(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    item_type: Optional[str] = Query(None, description="Filter by item type (Book, Journal, E-Book)"),
    year_from: Optional[int] = Query(None, ge=1900, le=2100, description="Filter by publication year (from)"),
    year_to: Optional[int] = Query(None, ge=1900, le=2100, description="Filter by publication year (to)"),
    available_only: bool = Query(False, description="Only show available items")
):
    """
    Search the catalog with various filters
    """
    # Simple search implementation (case-insensitive)
    q_lower = q.lower()
    
    # Filter items based on search query and filters
    filtered_items = []
    for item in CATALOG_ITEMS:
        # Skip if doesn't match item type filter
        if item_type and item.get("item_type") != item_type:
            continue
            
        # Skip if outside year range
        if year_from and item.get("publication_year", 0) < year_from:
            continue
        if year_to and item.get("publication_year", 3000) > year_to:
            continue
            
        # Skip if not available and available_only is True
        if available_only and item.get("available_copies", 0) <= 0:
            continue
            
        # Check if query matches title, author, or subject
        matches = (
            q_lower in item["title"].lower() or
            any(q_lower in author.lower() for author in item["authors"]) or
            any(q_lower in subject.lower() for subject in item["subjects"])
        )
        
        if matches:
            filtered_items.append(item)
    
    # Apply pagination
    total = len(filtered_items)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_items = filtered_items[start:end]
    
    # Convert to CatalogItem to ensure proper serialization
    catalog_items = []
    for item in paginated_items:
        # Ensure pages is a string
        if 'pages' in item and item['pages'] is not None:
            item['pages'] = str(item['pages'])
        catalog_items.append(CatalogItem(**item))
    
    return SearchResults(
        total=total,
        page=page,
        per_page=per_page,
        items=catalog_items
    )

@app.get("/items/{item_id}", response_model=CatalogItem)
async def get_item(item_id: str):
    """
    Get details for a specific catalog item
    """
    for item in CATALOG_ITEMS:
        if item["id"] == item_id:
            # Ensure pages is a string
            if 'pages' in item and item['pages'] is not None:
                item['pages'] = str(item['pages'])
            return CatalogItem(**item)
    raise HTTPException(status_code=404, detail="Item not found")

if __name__ == "__main__":
    # Create the directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "filename": "logs/catalog_api.log",
                    "formatter": "default",
                },
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
            },
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "loggers": {
                "uvicorn": {"level": "INFO", "handlers": ["file", "console"]},
                "uvicorn.error": {"level": "INFO", "handlers": ["file", "console"]},
                "uvicorn.access": {
                    "level": "INFO",
                    "handlers": ["file", "console"],
                    "propagate": False,
                },
            },
        },
    )
