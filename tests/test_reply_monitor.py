import pytest
from response_management.reply_monitor import is_system_email, IGNORE_SENDERS, IGNORE_DOMAINS

def test_is_system_email_empty_values():
    assert is_system_email("") == True
    assert is_system_email(None) == True
    assert is_system_email("   ") == True

def test_is_system_email_valid_emails():
    assert is_system_email("user@company.com") == False
    assert is_system_email("john.doe@startup.io") == False
    assert is_system_email("contact@mybusiness.net") == False

def test_is_system_email_ignore_senders():
    # Test a few exact matches from IGNORE_SENDERS
    assert is_system_email("noreply@domain.com") == True
    assert is_system_email("mailer-daemon@example.org") == True
    assert is_system_email("support@techcompany.com") == True
    assert is_system_email("info@website.com") == True

def test_is_system_email_ignore_domains():
    # Test a few exact matches from IGNORE_DOMAINS
    assert is_system_email("user@google.com") == True
    assert is_system_email("contact@amazon.com") == True
    assert is_system_email("steve@apple.com") == True
    assert is_system_email("random@facebook.com") == True

def test_is_system_email_substring_matches():
    # Test substring matching in the local part
    assert is_system_email("system-update@domain.com") == True
    assert is_system_email("my-newsletter@news.com") == True
    assert is_system_email("billing-department@store.com") == True
    assert is_system_email("do-donotreply@domain.com") == True

def test_is_system_email_edge_cases():
    # Uppercase
    assert is_system_email("NOREPLY@DOMAIN.COM") == True
    assert is_system_email("USER@GOOGLE.COM") == True

    # Leading/trailing whitespaces
    assert is_system_email("  support@domain.com  ") == True
    assert is_system_email("\tuser@apple.com\n") == True

    # No @ symbol
    assert is_system_email("invalidemail") == False
    assert is_system_email("noreply") == True # "noreply" in local part (which is the whole string) -> True

def test_is_system_email_all_ignore_senders():
    for sender in IGNORE_SENDERS:
        assert is_system_email(f"{sender}@somedomain.com") == True
        assert is_system_email(f"prefix-{sender}-suffix@somedomain.com") == True

def test_is_system_email_all_ignore_domains():
    for domain in IGNORE_DOMAINS:
        assert is_system_email(f"legit-user@{domain}") == True
