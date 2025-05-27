# app/schemas/search.py
from typing import List, Optional, Union
from pydantic import BaseModel

class SearchSuggestion(BaseModel):
    id: Union[int, str]
    name: str
    slug: str
    image: Optional[str] = None
    category: Optional[str] = None

class SearchSuggestionsResponse(BaseModel):
    suggestions: List[SearchSuggestion]