# Academic Search Sources

This document describes the search sources available in the reference manager and how to add more.

## Currently Active Sources

### 1. **Crossref** (Primary - Academic Papers)
- **Coverage**: 140+ million scholarly works
- **Best for**: Journal articles, conference papers, books with DOIs
- **API**: Free, no key required
- **Status**: ✅ Active (Primary source)

### 2. **Google Books** (Books)
- **Coverage**: Millions of books
- **Best for**: Books, textbooks, monographs
- **API**: Requires API key (optional, free tier available)
- **Status**: ✅ Active (Requires API key in config)

### 3. **Semantic Scholar** (NEW - Multi-disciplinary)
- **Coverage**: 200+ million papers
- **Best for**: Computer science, neuroscience, biomedical research
- **API**: Free, no key required
- **Status**: ✅ Active (Fallback after Crossref)

### 4. **arXiv** (NEW - Preprints)
- **Coverage**: 2+ million preprints
- **Best for**: Physics, Math, Computer Science, Biology preprints
- **API**: Free, no key required
- **Status**: ✅ Active (Fallback after Semantic Scholar)

## Search Order

When you search for a paper, the system tries sources in this order:

1. **For Books** (detected by keywords like "book", "edition", "volume"):
   - Google Books → Crossref

2. **For Papers**:
   - Crossref → Semantic Scholar → arXiv → Google Books (fallback)

## Additional Sources You Can Add

### Easy to Add (Free, No API Key)

#### **PubMed** (Medical/Life Sciences)
- **URL**: https://www.ncbi.nlm.nih.gov/home/develop/api/
- **Coverage**: 35+ million biomedical citations
- **API**: Free, no key required (rate limited)
- **Best for**: Medical, biomedical, life sciences research

#### **OpenAlex** (Multi-disciplinary)
- **URL**: https://docs.openalex.org/
- **Coverage**: 250+ million works
- **API**: Free, no key required
- **Best for**: Comprehensive academic coverage (replacement for Microsoft Academic)

#### **Europe PMC** (Life Sciences)
- **URL**: https://europepmc.org/RestfulWebService
- **Coverage**: 40+ million publications
- **API**: Free, no key required
- **Best for**: Life sciences and biomedical research

### Requires API Key (Free Tier Available)

#### **Springer Nature API**
- **URL**: https://dev.springernature.com/
- **Coverage**: Springer journals and books
- **API**: Free tier available (requires registration)

#### **IEEE Xplore API**
- **URL**: https://developer.ieee.org/
- **Coverage**: IEEE publications
- **API**: Free tier available (requires registration)

## How to Add a New Source

### Step 1: Create a Search Function

Add a new function in `src/referencing/referencing.py`:

```python
def search_newsource_single(query_text: str) -> Optional[Dict[str, Any]]:
    """
    Search for a single work using NewSource API.
    """
    url = "https://api.newsource.org/search"
    params = {'query': query_text}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Parse the response and return normalized format
        return {
            "source": "newsource",
            "pub_type": "journal-article",
            "authors": [...],  # Extract authors
            "year": "2023",     # Extract year
            "title": "...",     # Extract title
            "journal": "...",   # Extract journal
            "publisher": "",
            "location": "",
            "volume": "",
            "issue": "",
            "pages": "",
            "doi": "",
        }
    except Exception as e:
        logger.error(f"Error searching NewSource: {str(e)}")
        return None
```

### Step 2: Add to Search Chain

Update the `lookup_single_work` function to include your new source:

```python
if not meta:
    logger.info("Trying NewSource...")
    meta = search_newsource_single(query_text)
```

### Step 3: Test

Restart the app and search for a paper. Check the logs to see which source was used.

## Configuration

### Google Books API Key

To enable Google Books searches, add your API key to the environment or config:

```bash
export GOOGLE_BOOKS_API_KEY="your-api-key-here"
```

Or add to a `.env` file in the project root.

## Performance Tips

1. **Caching**: All search results are cached automatically
2. **Rate Limiting**: Built-in rate limiting prevents API throttling
3. **Fallback Chain**: If one source fails, the system automatically tries the next
4. **Parallel Searches**: For future enhancement, consider searching multiple sources in parallel

## Source Priority Recommendations

- **For Computer Science**: Semantic Scholar, arXiv, Crossref
- **For Medical/Life Sciences**: PubMed, Europe PMC, Crossref
- **For Physics/Math**: arXiv, Crossref
- **For Books**: Google Books, Crossref
- **For General Academic**: Crossref, Semantic Scholar, OpenAlex

## Troubleshooting

### No Results Found
- Check if the query is specific enough
- Try different search terms
- Check the logs to see which sources were tried
- Some sources may be temporarily unavailable

### API Rate Limiting
- The system has built-in rate limiting
- If you hit limits, results will be cached for future use
- Consider adding API keys for higher rate limits

## Future Enhancements

1. **Parallel Searching**: Search multiple sources simultaneously
2. **Result Ranking**: Combine results from multiple sources and rank by relevance
3. **Source Selection**: Let users choose which sources to search
4. **Custom Source Priority**: Allow users to configure source priority
5. **More Metadata**: Extract additional fields like abstracts, keywords, citations
