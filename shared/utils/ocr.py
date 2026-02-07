import re
import cv2
import numpy as np
from PIL import Image
from typing import Any, List, Dict, Optional, Tuple

def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """Preprocess image to improve OCR accuracy."""
    img_array = np.array(image)
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    return Image.fromarray(thresh)

def parse_frequency(text: str) -> int:
    """Extract medication frequency from text."""
    try:
        text_lower = text.lower()
        m = re.search(r"(\d+)\s*x\s*/?\s*day", text_lower)
        if m: return max(1, int(m.group(1)))
        if "twice daily" in text_lower or "two times a day" in text_lower: return 2
        if "three times" in text_lower: return 3
        every_hours = re.search(r"every\s+(\d+)\s*hour", text_lower)
        if every_hours:
            hours = int(every_hours.group(1))
            if hours > 0: return max(1, round(24 / hours))
    except Exception: pass
    return 1

def parse_times(text: str) -> List[str]:
    """Extract time patterns (HH:MM) from text."""
    return [t.strip() for t in re.findall(r"\b(\d{1,2}:\d{2})\s*(?:am|pm|AM|PM)?\b", text)]

def parse_receipt_items(text: str) -> Tuple[List[Dict[str, Any]], Optional[float]]:
    """Heuristically parse receipt text into items and detected total."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    items = []
    detected_total = None
    price_re = re.compile(r"([-+]?\d+[.,]\d{2})")

    for line in reversed(lines[-10:]):
        if re.search(r"\b(total|amount due|grand total|balance)\b", line, re.IGNORECASE):
            m = price_re.search(line)
            if m:
                detected_total = float(m.group(1).replace(',', '.'))
                break

    for line in lines:
        if re.search(r"\b(total|subtotal|tax|change|amount due|visa|mastercard|card)\b", line, re.IGNORECASE):
            continue
        m = price_re.search(line)
        if m:
            price = float(m.group(1).replace(',', '.'))
            name_part = price_re.sub('', line).strip()
            name_part = re.sub(r"^\d+\s*[xX]\s*", '', name_part).strip()
            if not name_part: name_part = "item"
            items.append({"name": name_part, "price": price})

    return items, detected_total

def categorize_finance_item(name: str) -> str:
    """Categorize a transaction based on its description/name."""
    n = re.sub(r"[^a-z0-9 ]", " ", name.lower())
    mapping = {
        'groceries': ['milk', 'bread', 'cheese', 'eggs', 'grocery', 'supermarket', 'aldi', 'lidl', 'wholefoods', 'tesco'],
        'restaurants': ['restaurant', 'cafe', 'diner', 'burger', 'pizza', 'bistro', 'mcdonald', 'kfc', 'starbucks'],
        'transport': ['uber', 'taxi', 'train', 'bus', 'lyft', 'fuel', 'gas'],
        'utilities': ['electric', 'water', 'gas bill', 'internet', 'utility'],
        'health': ['pharmacy', 'drug', 'rx', 'doctor', 'clinic', 'hospital'],
        'entertainment': ['movie', 'cinema', 'netflix', 'spotify', 'theatre']
    }
    for cat, keys in mapping.items():
        if any(k in n for k in keys): return cat
    return 'other'
