"""
Receipt Parser - Extract structured data from OCR text for expense tracking.

Parses receipt text to extract:
- Total amount (primary focus)
- Vendor/merchant name
- Date
- Category suggestions

Technical decisions:
1. Regex-based parsing (fast, deterministic, no training needed)
2. Focus on total amount first (most critical for expense tracking)
3. Flexible matching for various receipt formats
4. Category inference from vendor name
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ReceiptParser")


class ReceiptParser:
    """
    Parser for extracting structured data from receipt OCR text.

    Technical approach:
    - Regex patterns for total amount detection
    - Vendor name extraction from top of receipt
    - Date parsing with multiple format support
    - Category suggestion based on vendor keywords
    """

    # Common total amount keywords (ordered by specificity)
    TOTAL_KEYWORDS = [
        r"total\s*(?:amount)?",
        r"amount\s*due",
        r"balance\s*due",
        r"grand\s*total",
        r"subtotal",
        r"sum\s*total",
    ]

    # Currency patterns (supports $, USD, etc.)
    CURRENCY_PATTERN = r"(?:\$|USD\s*)?"

    # Amount pattern (supports formats like 12.34, 1,234.56)
    AMOUNT_PATTERN = r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?)"

    # Date patterns (MM/DD/YYYY, MM-DD-YYYY, etc.)
    DATE_PATTERNS = [
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",  # MM/DD/YYYY or MM-DD-YYYY
        r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})",  # YYYY-MM-DD
        r"(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{2,4})",  # DD MMM YYYY
    ]

    # Category keywords (vendor name → category mapping)
    CATEGORY_KEYWORDS = {
        "Food": [
            "restaurant",
            "cafe",
            "coffee",
            "pizza",
            "burger",
            "grill",
            "diner",
            "grocery",
            "market",
            "food",
            "bakery",
            "deli",
            "bistro",
            "kitchen",
            "mcdonald",
            "subway",
            "starbucks",
            "chipotle",
            "panera",
            "whole foods",
            "safeway",
            "kroger",
            "walmart",
            "target",
            "trader joe",
        ],
        "Gas": [
            "gas",
            "fuel",
            "chevron",
            "shell",
            "exxon",
            "mobil",
            "bp",
            "arco",
            "valero",
            "texaco",
            "conoco",
            "sunoco",
            "76",
            "citgo",
        ],
        "Medical": [
            "pharmacy",
            "cvs",
            "walgreens",
            "rite aid",
            "hospital",
            "clinic",
            "medical",
            "health",
            "doctor",
            "dental",
            "vision",
            "urgent care",
        ],
        "Bills": [
            "electric",
            "power",
            "utility",
            "water",
            "gas company",
            "internet",
            "cable",
            "phone",
            "wireless",
            "verizon",
            "at&t",
            "t-mobile",
            "comcast",
        ],
        "Shopping": [
            "amazon",
            "ebay",
            "store",
            "shop",
            "retail",
            "clothing",
            "fashion",
            "electronics",
            "best buy",
            "home depot",
            "lowes",
        ],
        "Transportation": [
            "uber",
            "lyft",
            "taxi",
            "transit",
            "parking",
            "toll",
            "metro",
            "bus",
        ],
    }

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse OCR text to extract structured receipt data.

        Args:
            text: Raw OCR text from receipt image

        Returns:
            Dictionary with:
                - total: Extracted total amount (float)
                - total_raw: Original total string
                - vendor: Vendor/merchant name
                - date: Transaction date
                - suggested_category: Inferred category
                - confidence: Parser confidence (0-100)
                - raw_text: Original text
        """
        text_lower = text.lower()

        result = {
            "total": self._extract_total(text_lower),
            "total_raw": None,
            "vendor": self._extract_vendor(text),
            "date": self._extract_date(text_lower),
            "suggested_category": None,
            "confidence": 0,
            "raw_text": text,
        }

        # Store raw total string if found
        if result["total"] is not None:
            result["total_raw"] = f"${result['total']:.2f}"

        # Infer category from vendor name
        if result["vendor"]:
            result["suggested_category"] = self._infer_category(result["vendor"])

        # Calculate confidence
        confidence_score = 0
        if result["total"] is not None:
            confidence_score += 60  # Total is most important
        if result["vendor"]:
            confidence_score += 20
        if result["date"]:
            confidence_score += 10
        if result["suggested_category"]:
            confidence_score += 10

        result["confidence"] = confidence_score

        logger.info(
            f"Parsed receipt: {result['vendor']} - ${result['total']} ({confidence_score}% confidence)"
        )

        return result

    def _extract_total(self, text: str) -> Optional[float]:
        """
        Extract total amount from receipt text.

        Strategy:
        1. Look for common total keywords
        2. Find amount immediately after keyword
        3. Prefer largest amount if multiple candidates
        4. Return as float

        Args:
            text: Lowercase receipt text

        Returns:
            Total amount as float, or None if not found
        """
        candidates = []

        # Try each total keyword pattern
        for keyword in self.TOTAL_KEYWORDS:
            # Build pattern: keyword + optional colon/space + currency + amount
            pattern = (
                keyword + r"\s*:?\s*" + self.CURRENCY_PATTERN + self.AMOUNT_PATTERN
            )

            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                amount_str = match.group(1)  # The amount capture group
                try:
                    # Remove commas and convert to float
                    amount = float(amount_str.replace(",", ""))
                    candidates.append(amount)
                    logger.debug(
                        f"Found total candidate: ${amount:.2f} (keyword: {keyword})"
                    )
                except ValueError:
                    continue

        if not candidates:
            # Fallback: Look for any amount preceded by $ or followed by common end-of-line patterns
            fallback_pattern = r"\$" + self.AMOUNT_PATTERN + r"(?:\s|$)"
            matches = re.finditer(fallback_pattern, text)
            for match in matches:
                amount_str = match.group(1)
                try:
                    amount = float(amount_str.replace(",", ""))
                    if amount > 0.50:  # Ignore very small amounts (likely item prices)
                        candidates.append(amount)
                        logger.debug(f"Found fallback total candidate: ${amount:.2f}")
                except ValueError:
                    continue

        if candidates:
            # Return the largest amount (most likely to be the total)
            total = max(candidates)
            logger.info(f"Extracted total: ${total:.2f}")
            return total

        logger.warning("No total amount found in receipt text")
        return None

    def _extract_vendor(self, text: str) -> Optional[str]:
        """
        Extract vendor/merchant name from receipt text.

        Strategy:
        1. Vendor name is usually in first 3 lines
        2. Look for longest capitalized phrase
        3. Clean up common prefixes/suffixes

        Args:
            text: Original (case-preserved) receipt text

        Returns:
            Vendor name string, or None if not found
        """
        lines = text.split("\n")

        # Check first 3 lines for vendor name
        for line in lines[:3]:
            line = line.strip()

            # Skip empty lines or very short lines
            if len(line) < 3:
                continue

            # Skip lines that look like addresses or dates
            if re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", line):
                continue
            if re.search(
                r"\d{3,5}\s+[a-z]+", line, re.IGNORECASE
            ):  # Street address pattern
                continue

            # Clean up common receipt prefixes
            line = re.sub(
                r"^(receipt|tax invoice|invoice)[\s:]*", "", line, flags=re.IGNORECASE
            )

            # If line has mostly uppercase letters or is title case, likely vendor name
            if len(line) > 3 and (line.isupper() or line.istitle()):
                vendor = line.strip()
                logger.info(f"Extracted vendor: {vendor}")
                return vendor

        # Fallback: Return first non-empty line
        for line in lines[:5]:
            line = line.strip()
            if len(line) > 3:
                vendor = line[:50]  # Limit length
                logger.warning(f"Using fallback vendor: {vendor}")
                return vendor

        logger.warning("No vendor name found in receipt text")
        return None

    def _extract_date(self, text: str) -> Optional[str]:
        """
        Extract transaction date from receipt text.

        Args:
            text: Lowercase receipt text

        Returns:
            Date string in YYYY-MM-DD format, or None if not found
        """
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # Try to parse and normalize to YYYY-MM-DD
                try:
                    # Try common formats
                    for fmt in [
                        "%m/%d/%Y",
                        "%m-%d-%Y",
                        "%m/%d/%y",
                        "%m-%d-%y",
                        "%Y-%m-%d",
                        "%Y/%m/%d",
                        "%d %b %Y",
                        "%d %B %Y",
                    ]:
                        try:
                            dt = datetime.strptime(date_str, fmt)
                            normalized = dt.strftime("%Y-%m-%d")
                            logger.info(f"Extracted date: {normalized}")
                            return normalized
                        except ValueError:
                            continue
                except Exception as e:
                    logger.debug(f"Date parsing failed: {e}")
                    continue

        logger.warning("No date found in receipt text")
        return None

    def _infer_category(self, vendor: str) -> Optional[str]:
        """
        Infer spending category from vendor name.

        Args:
            vendor: Vendor/merchant name

        Returns:
            Category name ('Food', 'Gas', 'Medical', 'Bills', 'Other')
        """
        vendor_lower = vendor.lower()

        # Check each category's keywords
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in vendor_lower:
                    logger.info(f"Inferred category: {category} (matched: {keyword})")
                    return category

        # Default category if no match
        logger.info("No category match found, defaulting to 'Other'")
        return "Other"


# Singleton instance
_parser: Optional[ReceiptParser] = None


def get_receipt_parser() -> ReceiptParser:
    """Get the global receipt parser instance."""
    global _parser
    if _parser is None:
        _parser = ReceiptParser()
    return _parser


# Test function
if __name__ == "__main__":
    print("Testing Receipt Parser...")
    print("=" * 70)

    # Test case 1: Simple receipt
    test_receipt_1 = """
STARBUCKS COFFEE
123 Main St
Seattle, WA 98101

Date: 12/11/2025
Time: 08:30 AM

Grande Latte         $4.95
Blueberry Muffin     $3.50

Subtotal             $8.45
Tax                  $0.76
TOTAL               $9.21

Thank you!
"""

    parser = get_receipt_parser()
    result1 = parser.parse(test_receipt_1)

    print("\nTest Case 1: Starbucks Receipt")
    print(f"  Vendor: {result1['vendor']}")
    print(
        f"  Total: ${result1['total']:.2f}"
        if result1["total"]
        else "  Total: Not found"
    )
    print(f"  Date: {result1['date']}")
    print(f"  Suggested Category: {result1['suggested_category']}")
    print(f"  Confidence: {result1['confidence']}%")

    # Test case 2: Gas station receipt
    test_receipt_2 = """
CHEVRON
456 Highway 101
San Jose, CA

12/11/2025  14:23

Unleaded Regular
15.234 gal @ $3.899

TOTAL              $59.38

CREDIT CARD
"""

    result2 = parser.parse(test_receipt_2)

    print("\nTest Case 2: Gas Station Receipt")
    print(f"  Vendor: {result2['vendor']}")
    print(
        f"  Total: ${result2['total']:.2f}"
        if result2["total"]
        else "  Total: Not found"
    )
    print(f"  Date: {result2['date']}")
    print(f"  Suggested Category: {result2['suggested_category']}")
    print(f"  Confidence: {result2['confidence']}%")

    # Test case 3: Grocery receipt
    test_receipt_3 = """
WHOLE FOODS MARKET
789 Park Ave

Date: 12/11/2025

ORGANIC APPLES       $5.99
BREAD                $4.50
MILK                 $3.99
EGGS                 $5.49

SUBTOTAL            $19.97
TAX                  $1.80
TOTAL DUE           $21.77
"""

    result3 = parser.parse(test_receipt_3)

    print("\nTest Case 3: Grocery Receipt")
    print(f"  Vendor: {result3['vendor']}")
    print(
        f"  Total: ${result3['total']:.2f}"
        if result3["total"]
        else "  Total: Not found"
    )
    print(f"  Date: {result3['date']}")
    print(f"  Suggested Category: {result3['suggested_category']}")
    print(f"  Confidence: {result3['confidence']}%")

    print("\n" + "=" * 70)
    print("Receipt parser test complete!")
