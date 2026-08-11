import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from ai_ceo.decision_engine import is_safe_command

class TestDecisionEngine(unittest.TestCase):
    def test_safe_commands(self):
        # Base valid commands without arguments
        self.assertTrue(is_safe_command("python intelligence/lead_finder.py"))
        self.assertTrue(is_safe_command("python3 intelligence/lead_enricher.py"))

        # Valid commands with safe arguments
        self.assertTrue(is_safe_command("python outreach/whatsapp_sender.py --send"))
        self.assertTrue(is_safe_command("python response_management/reply_monitor.py --auto-approve"))
        self.assertTrue(is_safe_command("python scale/campaign_manager.py --create new_campaign"))
        self.assertTrue(is_safe_command("python3 intelligence/lead_finder.py arg1 arg-2 arg_3"))
        self.assertTrue(is_safe_command("python outreach/email_sender.py --limit=50"))

        # Whitespace handling
        self.assertTrue(is_safe_command("  python intelligence/lead_finder.py  "))

    def test_invalid_commands(self):
        # Not starting with python
        self.assertFalse(is_safe_command("bash script.sh"))
        self.assertFalse(is_safe_command("./intelligence/lead_finder.py"))
        self.assertFalse(is_safe_command("ruby script.rb"))
        self.assertFalse(is_safe_command("echo 'hello'"))

        # Empty or None
        self.assertFalse(is_safe_command(""))
        self.assertFalse(is_safe_command(None))

        # Missing script name
        self.assertFalse(is_safe_command("python "))
        self.assertFalse(is_safe_command("python"))
        self.assertFalse(is_safe_command("python3"))

        # Not in the whitelist
        self.assertFalse(is_safe_command("python scripts/malicious.py"))
        self.assertFalse(is_safe_command("python intelligence/unknown.py"))
        self.assertFalse(is_safe_command("python manage.py runserver"))
        self.assertFalse(is_safe_command("python3 ai_ceo/decision_engine.pyc")) # slight variation

    def test_malicious_arguments(self):
        # Shell metacharacters
        self.assertFalse(is_safe_command("python intelligence/lead_finder.py && rm -rf /"))
        self.assertFalse(is_safe_command("python intelligence/lead_finder.py ; ls"))
        self.assertFalse(is_safe_command("python intelligence/lead_finder.py | grep test"))
        self.assertFalse(is_safe_command("python intelligence/lead_finder.py > output.txt"))
        self.assertFalse(is_safe_command("python intelligence/lead_finder.py < input.txt"))
        self.assertFalse(is_safe_command("python intelligence/lead_finder.py `whoami`"))
        self.assertFalse(is_safe_command("python intelligence/lead_finder.py $(whoami)"))
        self.assertFalse(is_safe_command("python intelligence/lead_finder.py arg &"))
        self.assertFalse(is_safe_command("python intelligence/lead_finder.py *"))
        self.assertFalse(is_safe_command("python intelligence/lead_finder.py ?"))
        self.assertFalse(is_safe_command("python intelligence/lead_finder.py \\n"))
        self.assertFalse(is_safe_command("python intelligence/lead_finder.py \\t"))
        self.assertFalse(is_safe_command("python intelligence/lead_finder.py $HOME"))

        # Multiple metacharacters
        self.assertFalse(is_safe_command("python intelligence/lead_finder.py --arg=value ; rm -rf /"))

if __name__ == '__main__':
    unittest.main()
