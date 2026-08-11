import unittest
from unittest.mock import patch, MagicMock
import smtplib

from intelligence.email_verifier import verify_smtp


class TestEmailVerifier(unittest.TestCase):
    def test_invalid_format(self):
        result = verify_smtp("invalid_email")
        self.assertFalse(result["format_valid"])
        self.assertEqual(result["reason"], "Invalid email format")

    @patch("intelligence.email_verifier.socket.gethostbyname")
    def test_domain_not_exists(self, mock_gethostbyname):
        mock_gethostbyname.side_effect = Exception("Domain not found")
        result = verify_smtp("test@nonexistent.com")
        self.assertTrue(result["format_valid"])
        self.assertFalse(result["domain_exists"])
        self.assertEqual(result["status"], "invalid")
        self.assertIn("does not exist", result["reason"])

    @patch("intelligence.email_verifier.check_mx_record")
    @patch("intelligence.email_verifier.socket.gethostbyname")
    def test_no_mx_record(self, mock_gethostbyname, mock_check_mx):
        mock_gethostbyname.return_value = "1.2.3.4"
        mock_check_mx.return_value = False
        result = verify_smtp("test@nomx.com")
        self.assertTrue(result["domain_exists"])
        self.assertFalse(result["mx_record_found"])
        self.assertEqual(result["status"], "risky")
        self.assertEqual(result["confidence"], 30)
        self.assertIn("No mail server found", result["reason"])

    @patch("intelligence.email_verifier.smtplib.SMTP")
    @patch("intelligence.email_verifier.dns.resolver.resolve")
    @patch("intelligence.email_verifier.check_mx_record")
    @patch("intelligence.email_verifier.socket.gethostbyname")
    def test_valid_smtp_handshake(
        self, mock_gethostbyname, mock_check_mx, mock_resolve, mock_smtp
    ):
        mock_gethostbyname.return_value = "1.2.3.4"
        mock_check_mx.return_value = True

        mock_record = MagicMock()
        mock_record.preference = 10
        mock_record.exchange = "mail.example.com"
        mock_resolve.return_value = [mock_record]

        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
        mock_smtp_instance.rcpt.return_value = (250, b"2.1.5 Ok")

        result = verify_smtp("test@example.com")

        self.assertTrue(result["smtp_handshake"])
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["confidence"], 95)
        self.assertEqual(result["reason"], "Mailbox confirmed via SMTP")

    @patch("intelligence.email_verifier.smtplib.SMTP")
    @patch("intelligence.email_verifier.dns.resolver.resolve")
    @patch("intelligence.email_verifier.check_mx_record")
    @patch("intelligence.email_verifier.socket.gethostbyname")
    def test_invalid_smtp_handshake(
        self, mock_gethostbyname, mock_check_mx, mock_resolve, mock_smtp
    ):
        mock_gethostbyname.return_value = "1.2.3.4"
        mock_check_mx.return_value = True

        mock_record = MagicMock()
        mock_record.preference = 10
        mock_record.exchange = "mail.example.com"
        mock_resolve.return_value = [mock_record]

        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
        mock_smtp_instance.rcpt.return_value = (550, b"5.1.1 User unknown")

        result = verify_smtp("invalid@example.com")

        self.assertFalse(result["smtp_handshake"])
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["confidence"], 0)
        self.assertEqual(result["reason"], "Mailbox does not exist (550)")

    @patch("intelligence.email_verifier.smtplib.SMTP")
    @patch("intelligence.email_verifier.dns.resolver.resolve")
    @patch("intelligence.email_verifier.check_mx_record")
    @patch("intelligence.email_verifier.socket.gethostbyname")
    def test_uncertain_smtp_response(
        self, mock_gethostbyname, mock_check_mx, mock_resolve, mock_smtp
    ):
        mock_gethostbyname.return_value = "1.2.3.4"
        mock_check_mx.return_value = True

        mock_record = MagicMock()
        mock_record.preference = 10
        mock_record.exchange = "mail.example.com"
        mock_resolve.return_value = [mock_record]

        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
        mock_smtp_instance.rcpt.return_value = (500, b"Syntax error")

        result = verify_smtp("uncertain@example.com")

        self.assertFalse(result["smtp_handshake"])
        self.assertEqual(result["status"], "risky")
        self.assertEqual(result["confidence"], 50)
        self.assertIn("Uncertain SMTP response: 500", result["reason"])

    @patch("intelligence.email_verifier.smtplib.SMTP")
    @patch("intelligence.email_verifier.dns.resolver.resolve")
    @patch("intelligence.email_verifier.check_mx_record")
    @patch("intelligence.email_verifier.socket.gethostbyname")
    def test_smtp_connect_error(
        self, mock_gethostbyname, mock_check_mx, mock_resolve, mock_smtp
    ):
        mock_gethostbyname.return_value = "1.2.3.4"
        mock_check_mx.return_value = True

        mock_record = MagicMock()
        mock_record.preference = 10
        mock_record.exchange = "mail.example.com"
        mock_resolve.return_value = [mock_record]

        mock_smtp.return_value.__enter__.side_effect = smtplib.SMTPConnectError(
            421, b"Service not available"
        )

        result = verify_smtp("connecterror@example.com")

        self.assertFalse(result["smtp_handshake"])
        self.assertEqual(result["status"], "likely_valid")
        self.assertEqual(result["confidence"], 70)
        self.assertIn("server blocks external SMTP checks", result["reason"])

    @patch("intelligence.email_verifier.smtplib.SMTP")
    @patch("intelligence.email_verifier.dns.resolver.resolve")
    @patch("intelligence.email_verifier.check_mx_record")
    @patch("intelligence.email_verifier.socket.gethostbyname")
    def test_smtp_timeout(
        self, mock_gethostbyname, mock_check_mx, mock_resolve, mock_smtp
    ):
        mock_gethostbyname.return_value = "1.2.3.4"
        mock_check_mx.return_value = True

        mock_record = MagicMock()
        mock_record.preference = 10
        mock_record.exchange = "mail.example.com"
        mock_resolve.return_value = [mock_record]

        mock_smtp.return_value.__enter__.side_effect = Exception("timed out")

        result = verify_smtp("timeout@example.com")

        self.assertFalse(result["smtp_handshake"])
        self.assertEqual(result["status"], "likely_valid")
        self.assertEqual(result["confidence"], 65)
        self.assertIn("timeout suggests real server blocking checks", result["reason"])

    @patch("intelligence.email_verifier.smtplib.SMTP")
    @patch("intelligence.email_verifier.dns.resolver.resolve")
    @patch("intelligence.email_verifier.check_mx_record")
    @patch("intelligence.email_verifier.socket.gethostbyname")
    def test_smtp_inconclusive(
        self, mock_gethostbyname, mock_check_mx, mock_resolve, mock_smtp
    ):
        mock_gethostbyname.return_value = "1.2.3.4"
        mock_check_mx.return_value = True

        mock_record = MagicMock()
        mock_record.preference = 10
        mock_record.exchange = "mail.example.com"
        mock_resolve.return_value = [mock_record]

        mock_smtp.return_value.__enter__.side_effect = Exception(
            "generic network error"
        )

        result = verify_smtp("inconclusive@example.com")

        self.assertFalse(result["smtp_handshake"])
        self.assertEqual(result["status"], "risky")
        self.assertEqual(result["confidence"], 45)
        self.assertIn("SMTP inconclusive", result["reason"])


if __name__ == "__main__":
    unittest.main()
