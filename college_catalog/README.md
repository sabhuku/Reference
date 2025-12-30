# Dummy College Catalog API

A mock API service that simulates a college library catalog for development and testing purposes.

## Features

- Search functionality with pagination
- Filter by item type, availability, and publication year
- Sample data for books, e-books, and journals
- RESTful API endpoints
- CORS enabled for local development
- Detailed logging

## Setup

1. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the server:
   ```bash
   python main.py
   ```

The API will be available at `http://localhost:8000`

## API Endpoints

### Search Catalog
- `GET /search?q={query}&page=1&per_page=10`
  - Query parameters:
    - `q`: Search query (required)
    - `page`: Page number (default: 1)
    - `per_page`: Items per page (default: 10, max: 100)
    - `item_type`: Filter by type (Book, Journal, E-Book)
    - `year_from`/`year_to`: Filter by publication year
    - `available_only`: Only show available items (true/false)

### Get Item Details
- `GET /items/{item_id}`
  - Returns detailed information about a specific item

## Sample Data

The API includes sample data for:
- 100 books (including 20 e-books)
- 80 journal articles (20 volumes × 4 issues each)

## Integration with Reference Assistant

To use this with the Reference Assistant, update the configuration to include this as a search source.

## Development

- The server automatically reloads when code changes are detected
- Logs are saved to `logs/catalog_api.log`
- Sample data is generated on startup in `main.py`

## License

MIT
