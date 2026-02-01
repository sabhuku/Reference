# Retrieval Result Metadata Schema

## Overview
To improve user trust and auditability, we strictly attach metadata to all retrieval results. This metadata explains *why* a result was returned and *how confident* the system is in that result.

## Schema Attributes

The following attributes are dynamically attached to `Publication` objects returned by the `ReferenceManager`.

| Attribute | Type | Description | Values / Range |
|-----------|------|-------------|----------------|
| `match_type` | `str` | Type of match logic used. | `exact_title`, `partial_title`, `fuzzy`, `author_match`, `single_best` |
| `confidence_score` | `float` | Normalized confidence score. | `0.0` - `1.0` |
| `retrieval_method` | `str` | Mechanism used to retrieve result. | `api` (parallel), `api_sequential`, `cache` |
| `source` | `str` | Underlying data source. | `crossref`, `pubmed`, `google_books`, `unknown_single` |
| `is_selected` | `bool` | Whether this is the top-ranked result. | `True` / `False` |
| `selection_details` | `dict` | Breakdown of scoring criteria (only for selected). | `{ "score": 105, "criteria": {...} }` |

## Example Result Object (JSON representation)

```json
{
  "title": "Deep Learning for Search",
  "authors": ["Smith, J.", "Doe, A."],
  "year": "2023",
  "doi": "10.1234/example",
  "journal": "Journal of IR",
  "match_type": "exact_title",
  "confidence_score": 0.86,
  "retrieval_method": "api",
  "source": "crossref",
  "is_selected": true,
  "selection_details": {
    "score": 105,
    "criteria": {
      "source": 5,
      "title_exact": 100,
      "year_2020_plus": 5,
      "has_doi": 3
    }
  }
}
```

## UI Surfacing Plan (Future)

1.  **Trust Badge**: Display a small color-coded badge based on `confidence_score`.
    *   Green: > 0.8
    *   Yellow: 0.5 - 0.8
    *   Red: < 0.5

2.  **Audit Tooltip**: Hovering over the "Best Match" label should show the `selection_details` criteria, e.g., "Exact Title Match (+100), Recent (+5)".

3.  **Source Indicator**: Explicitly show "Source: CrossRef" or "Source: Google Books" to let users know where data comes from.

4.  **Selection Reason**: For the top result, render the structured reasons in a "Why this result?" expandable section.
