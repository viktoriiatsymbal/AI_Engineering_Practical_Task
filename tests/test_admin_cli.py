import pytest

from src.admin_cli import (
    filter_reviews,
    parse_confirmation,
    parse_list_command)

def test_parse_confirmation_accepts_yes_and_y():
    assert parse_confirmation("yes") == "approve"
    assert parse_confirmation("y") == "approve"

def test_parse_confirmation_accepts_no_and_n():
    assert parse_confirmation("no") == "reject"
    assert parse_confirmation("n") == "reject"

def test_parse_confirmation_rejects_unknown_value():
    with pytest.raises(ValueError):
        parse_confirmation("maybe")

def test_parse_list_command_supports_required_modes():
    assert parse_list_command("list") == "pending"
    assert parse_list_command("list pending") == "pending"
    assert parse_list_command("list all") == "all"
    assert parse_list_command("list approved") is None

def test_pending_filter_includes_both_unfinished_states():
    reviews = [
        {"review_state": "pending_admin"},
        {"review_state": "awaiting_confirmation"},
        {"review_state": "approved"}]
    assert filter_reviews(reviews, "pending") == reviews[:2]

def test_all_filter_returns_every_review():
    reviews = [
        {"review_state": "pending_admin"},
        {"review_state": "approved"}]
    assert filter_reviews(reviews, "all") == reviews