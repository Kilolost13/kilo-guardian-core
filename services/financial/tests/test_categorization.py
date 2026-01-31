from financial.main import _categorize_item


def test_categorize_various_items():
    samples = {
        'Milk 2.99': 'groceries',
        'Starbucks Latte': 'coffee',
        'Walmart Electronics TV': 'electronics',
        'Uber Trip': 'transport',
        'Spotify Subscription': 'subscription',
        'BP Petrol': 'fuel',
        'McDonald\'s Burger': 'fast_food',
        'IKEA Table': 'home',
        'Pharmacy RX': 'pharmacy',
        'Cinema Ticket': 'entertainment',
        'Dog Food 3kg': 'pet',
    }

    for name, expected in samples.items():
        cat = _categorize_item(name)
        assert cat == expected, f"{name} -> {cat} != {expected}"
