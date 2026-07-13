from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BookItem:
    title: str
    price: str
    availability: str
    rating: str
    product_url: str
    source_category: str
    source_url: str
    crawled_at: str
    description: Optional[str] = None
    upc: Optional[str] = None
    product_type: Optional[str] = None
    tax: Optional[str] = None
    number_of_reviews: Optional[str] = None
