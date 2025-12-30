from typing import List, Optional, Dict
import aiohttp
import asyncio
from .types import Publication
from .config import CROSSREF_API_URL, GOOGLE_BOOKS_API_URL, CROSSREF_MAILTO, GOOGLE_BOOKS_API_KEY

async def async_get_json(url: str, params: Dict[str, str]) -> Dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()

async def async_search_crossref(query_text: str, rows: int = 1) -> Optional[Publication]:
    params = {
        "query.bibliographic": query_text,
        "rows": str(rows),
        "mailto": CROSSREF_MAILTO
    }
    try:
        data = await async_get_json(CROSSREF_API_URL, params)
        items = data.get("message", {}).get("items", [])
        # Process items and return Publication object
        # Implementation similar to the synchronous version
        return None if not items else items[0]
    except Exception:
        return None

async def async_search_google_books(query_text: str, max_results: int = 5) -> Optional[Publication]:
    params = {
        "q": query_text,
        "maxResults": str(max_results)
    }
    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY
        
    try:
        data = await async_get_json(GOOGLE_BOOKS_API_URL, params)
        items = data.get("items", [])
        # Process items and return Publication object
        # Implementation similar to the synchronous version
        return None if not items else items[0]
    except Exception:
        return None

async def async_lookup_work(query_text: str) -> Optional[Publication]:
    """
    Asynchronously search both APIs in parallel and return the first valid result
    """
    crossref_task = asyncio.create_task(async_search_crossref(query_text))
    books_task = asyncio.create_task(async_search_google_books(query_text))
    
    done, _ = await asyncio.wait(
        [crossref_task, books_task],
        return_when=asyncio.FIRST_COMPLETED
    )
    
    for task in done:
        result = await task
        if result:
            return result
            
    # If first API failed, wait for the second
    remaining = [t for t in [crossref_task, books_task] if not t.done()]
    if remaining:
        results = await asyncio.gather(*remaining, return_exceptions=True)
        for result in results:
            if isinstance(result, dict):
                return result
                
    return None