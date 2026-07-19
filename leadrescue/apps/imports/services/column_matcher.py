import difflib

CONFIDENCE_THRESHOLD = 0.6

FIELD_SYNONYMS = {
    # Lead Fields
    "name": ["name", "client name", "full name", "contact name", "customer name", "lead name"],
    "phone": ["phone", "ph no", "phone number", "mobile", "contact", "contact number", "mobile no", "whatsapp number"],
    "email": ["email", "email address", "e-mail"],
    "budget": ["budget", "budget min", "min budget", "budget from", "budget max", "max budget", "budget to", "amount"],
    "location": ["location", "preferred location", "area", "locality", "city"],
    "bhk": ["bhk", "preferred bhk", "unit type", "config", "configuration", "bedrooms"],
    "source": ["source", "lead source", "platform", "channel", "medium"],
    "status": ["status", "lead status", "stage"],
    "notes": ["notes", "note", "remark", "remarks", "comment", "comments", "description"],
    
    # Property Fields
    "title": ["title", "property title", "property name", "name", "heading"],
    "price": ["price", "amount", "cost", "rate", "value", "asking price", "selling price"],
    "city": ["city", "location", "place", "town"],
    "locality": ["locality", "area", "sector", "neighborhood", "neighbourhood", "subarea"],
    "bhk": ["bhk", "bedrooms", "beds", "rooms", "configuration", "type"],
    "description": ["description", "desc", "details", "info", "about", "notes"],
}


def _normalize(text):
    """Lowercase and strip whitespace for clean matching."""
    return str(text).strip().lower()


def match_columns(uploaded_headers, target_fields):
    """
    Intelligently maps CSV/Excel headers to our internal fields using exact matching
    and difflib SequenceMatcher for fuzzy matching.
    
    Returns a dictionary mapping internal fields to uploaded headers, 
    and a dict tracking confidence levels for each field.
    """
    mapped = {}
    confidences = {}
    
    # Restrict to only the target_fields we care about for this model
    relevant_synonyms = {k: v for k, v in FIELD_SYNONYMS.items() if k in target_fields}
    
    # For each target field, find the best header match
    # Structure: candidate_matches[header] = [(field, confidence), ...]
    candidate_matches = {h: [] for h in uploaded_headers}
    
    for field, synonyms in relevant_synonyms.items():
        for header in uploaded_headers:
            norm_header = _normalize(header)
            
            best_score = 0.0
            
            # Exact match gives 1.0 confidence
            if norm_header in synonyms:
                best_score = 1.0
            else:
                # Fuzzy match
                for syn in synonyms:
                    score = difflib.SequenceMatcher(None, norm_header, syn).ratio()
                    if score > best_score:
                        best_score = score
            
            if best_score > CONFIDENCE_THRESHOLD:
                candidate_matches[header].append((field, best_score))
                
    # Resolve conflicts: No target field can be matched by more than one uploaded column
    # If a column has multiple field matches, it picks the highest confidence.
    # If a field has multiple column matches, the column with the highest confidence gets it.
    
    # Flatten into a list of (header, field, confidence) sorted by confidence descending
    all_potential_matches = []
    for header, matches in candidate_matches.items():
        for field, score in matches:
            all_potential_matches.append((header, field, score))
            
    # Sort highest confidence first
    all_potential_matches.sort(key=lambda x: x[2], reverse=True)
    
    used_headers = set()
    used_fields = set()
    
    for header, field, score in all_potential_matches:
        if header not in used_headers and field not in used_fields:
            mapped[field] = header
            confidences[field] = score
            used_headers.add(header)
            used_fields.add(field)

    return mapped, confidences
