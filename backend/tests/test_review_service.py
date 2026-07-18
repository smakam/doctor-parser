from app.services.review_service import normalize_registration_number


def test_normalize_registration_number():
    assert normalize_registration_number(" mh-12345 ") == "MH-12345"
    assert normalize_registration_number("tn  42  abc") == "TN 42 ABC"
    assert normalize_registration_number("   ") is None
    assert normalize_registration_number(None) is None
