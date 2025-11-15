#!/usr/bin/env python3
"""Test script to validate filter logic on cached pages or sample data."""

import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deal_watcher.filters.auto_filter import AutoFilter
from deal_watcher.filters.reality_filter import RealityFilter
from deal_watcher.utils.logger import setup_logger

logger = setup_logger('test_filters', level='DEBUG')

# Sample test cases
BMW_TEST_CASES = [
    {
        "id": "1",
        "title": "BMW E46 330i Manual",
        "description": "BMW 330i E46, 6 valec benzin, manuálna prevodovka, plná výbava",
        "price": 8500,
        "should_match": True,
        "reason": "E46 330i with 6-cylinder, petrol, manual"
    },
    {
        "id": "2",
        "title": "BMW 328i E36 Coupe",
        "description": "Predám BMW 328i E36 Coupe, M52B28 motor, benzín, manuál, pekný stav",
        "price": 6500,
        "should_match": True,
        "reason": "E36 328i with M52B28 engine code, petrol, manual"
    },
    {
        "id": "3",
        "title": "BMW 520i E39",
        "description": "BMW 520i E39 touring, M54B22 motor, 6-valec benzín, manuálna prevodovka",
        "price": 4500,
        "should_match": True,
        "reason": "E39 520i with M54B22 engine, 6-cyl, petrol, manual"
    },
    {
        "id": "4",
        "title": "BMW 320d E46",
        "description": "BMW 320d E46, diesel, manuál, top stav",
        "price": 7000,
        "should_match": False,
        "reason": "Diesel, not petrol (should reject)"
    },
    {
        "id": "5",
        "title": "BMW 330i E46 Automatic",
        "description": "BMW 330i E46, 6 valec benzin, automatická prevodovka",
        "price": 9000,
        "should_match": False,
        "reason": "Automatic transmission (should reject)"
    },
    {
        "id": "6",
        "title": "BMW 318i E46",
        "description": "BMW 318i E46, 4 valec benzin, manuál",
        "price": 5000,
        "should_match": False,
        "reason": "4-cylinder, not 6-cylinder (should reject)"
    },
]

REALITY_TEST_CASES = [
    {
        "id": "1",
        "title": "Pozemok 5 hektárov",
        "description": "Predám pozemok 5 hektárov (50000 m²), cena 250000 EUR",
        "price": 250000,
        "should_match": True,
        "reason": "5 hectares = 50,000 m², under 400k"
    },
    {
        "id": "2",
        "title": "Dom s veľkým pozemkom",
        "description": "Rodinný dom s pozemkom 45000 m², úžitková plocha 150 m², cena 380000 EUR",
        "price": 380000,
        "should_match": True,
        "reason": "45,000 m² land, should ignore 150 m² floor area"
    },
    {
        "id": "3",
        "title": "Chata s pozemkom 4.2 ha",
        "description": "Chata na parcele 4.2 hektára, cena dohodou",
        "price": None,
        "should_match": True,
        "reason": "4.2 ha = 42,000 m², over threshold"
    },
    {
        "id": "4",
        "title": "Pozemok lacno",
        "description": "Predám pozemok 60000 m², cena 3.5 EUR/m²",
        "price": 3.5,
        "should_match": False,
        "reason": "Price per m² (should reject)"
    },
    {
        "id": "5",
        "title": "Dom v meste",
        "description": "Rodinný dom, podlahová plocha 200 m², pozemok 800 m²",
        "price": 350000,
        "should_match": False,
        "reason": "Only 800 m² land (too small)"
    },
    {
        "id": "6",
        "title": "Luxusná vila",
        "description": "Vila s pozemkom 50000 m², cena 600000 EUR",
        "price": 600000,
        "should_match": False,
        "reason": "Price over 400k limit (should reject)"
    },
]


def test_auto_filter():
    """Test BMW auto filter."""
    print("\n" + "=" * 60)
    print("Testing BMW Auto Filter")
    print("=" * 60)

    # Load filter config
    config = {
        "keywords_any": [
            "E36", "E46", "E39",
            "320i", "323i", "325i", "328i", "330i",
            "520i", "523i", "525i", "528i", "530i"
        ],
        "keywords_all": ["benzin", "manuál"],
        "keywords_engine": [
            "6 valec", "6-valec", "6 cylinder", "šesťvalec",
            "M50", "M52", "M54",
            "M50B20", "M50B25", "M52B25", "M52B28", "M52TU",
            "M54B22", "M54B25", "M54B30"
        ],
        "keywords_excluded": ["havarovan", "automat", "automatická", "automatic"],
        "price_max": None,
        "price_min": None
    }

    filter_obj = AutoFilter(config)

    passed = 0
    failed = 0

    for test_case in BMW_TEST_CASES:
        listing = {
            'external_id': test_case['id'],
            'title': test_case['title'],
            'description': test_case['description'],
            'price': test_case['price']
        }

        # Test with detailed=True (full filter)
        result = filter_obj.matches(listing, detailed=True)
        expected = test_case['should_match']

        status = "✓ PASS" if result == expected else "✗ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"\n{status} - Test {test_case['id']}")
        print(f"  Title: {test_case['title']}")
        print(f"  Expected: {'MATCH' if expected else 'REJECT'}")
        print(f"  Got: {'MATCH' if result else 'REJECT'}")
        print(f"  Reason: {test_case['reason']}")

    print(f"\n{'=' * 60}")
    print(f"BMW Filter Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")

    return failed == 0


def test_reality_filter():
    """Test reality filter."""
    print("\n" + "=" * 60)
    print("Testing Reality Filter")
    print("=" * 60)

    config = {
        "price_max": 400000,
        "area_min": 40000,
        "area_type": "land",
        "keywords_excluded": ["stavebný pozemok"],
        "reject_price_per_m2": True
    }

    filter_obj = RealityFilter(config)

    passed = 0
    failed = 0

    for test_case in REALITY_TEST_CASES:
        listing = {
            'external_id': test_case['id'],
            'title': test_case['title'],
            'description': test_case['description'],
            'price': test_case['price']
        }

        # Test with detailed=True (full filter)
        result = filter_obj.matches(listing, detailed=True)
        expected = test_case['should_match']

        status = "✓ PASS" if result == expected else "✗ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"\n{status} - Test {test_case['id']}")
        print(f"  Title: {test_case['title']}")
        print(f"  Expected: {'MATCH' if expected else 'REJECT'}")
        print(f"  Got: {'MATCH' if result else 'REJECT'}")
        print(f"  Reason: {test_case['reason']}")

    print(f"\n{'=' * 60}")
    print(f"Reality Filter Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")

    return failed == 0


def main():
    """Run all filter tests."""
    print("\n" + "=" * 60)
    print("Deal Watcher - Filter Validation Tests")
    print("=" * 60)

    auto_ok = test_auto_filter()
    reality_ok = test_reality_filter()

    print("\n" + "=" * 60)
    print("Overall Results")
    print("=" * 60)
    print(f"BMW Filter: {'✓ PASS' if auto_ok else '✗ FAIL'}")
    print(f"Reality Filter: {'✓ PASS' if reality_ok else '✗ FAIL'}")

    if auto_ok and reality_ok:
        print("\n✓ All filter tests passed!")
        return 0
    else:
        print("\n✗ Some filter tests failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
