import unittest
from unittest.mock import patch, MagicMock
from intelligence.email_verifier import check_mx_record

class TestEmailVerifier(unittest.TestCase):

    @patch('intelligence.email_verifier.dns.resolver.resolve')
    def test_check_mx_record_success(self, mock_resolve):
        """Test that check_mx_record returns True when MX records are found."""
        # Setup the mock to return a list with at least one element
        mock_resolve.return_value = [MagicMock()]

        result = check_mx_record("example.com")

        self.assertTrue(result)
        mock_resolve.assert_called_once_with("example.com", 'MX')

    @patch('intelligence.email_verifier.dns.resolver.resolve')
    def test_check_mx_record_empty(self, mock_resolve):
        """Test that check_mx_record returns False when no MX records are returned."""
        # Setup the mock to return an empty list
        mock_resolve.return_value = []

        result = check_mx_record("example.com")

        self.assertFalse(result)
        mock_resolve.assert_called_once_with("example.com", 'MX')

    @patch('intelligence.email_verifier.dns.resolver.resolve')
    def test_check_mx_record_exception(self, mock_resolve):
        """Test that check_mx_record returns False when an exception is raised."""
        # Setup the mock to raise an exception
        mock_resolve.side_effect = Exception("DNS lookup failed")

        result = check_mx_record("example.com")

        self.assertFalse(result)
        mock_resolve.assert_called_once_with("example.com", 'MX')

if __name__ == '__main__':
    unittest.main()
