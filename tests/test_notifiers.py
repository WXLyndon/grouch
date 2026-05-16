import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import notifier
import notifierMac


class NotifierTests(unittest.TestCase):
    def test_regular_notifier_run_sleeps_between_false_checks(self):
        states = [False, True]

        def state():
            return states.pop(0)

        notif = notifier.Notifier("Title", "Info", state)
        notif.send = Mock()

        with patch.object(notifier.time, "sleep") as sleep:
            notif.run(check_interval=5)

        sleep.assert_called_once_with(5)
        notif.send.assert_called_once_with()

    def test_mac_notifier_run_sleeps_between_false_checks(self):
        states = [False, True]

        def state():
            return states.pop(0)

        notif = notifierMac.Notifier("Title", "Info", state)
        notif.send = Mock()

        with patch.object(notifierMac.time, "sleep") as sleep:
            notif.run(check_interval=5)

        sleep.assert_called_once_with(5)
        notif.send.assert_called_once_with()

    def test_mac_notifier_uses_subprocess_argv_without_shell(self):
        title = 'Course "Open"'
        info = "Line one\nLine 'two'"
        notif = notifierMac.Notifier(title, info)

        with patch.object(notifierMac.subprocess, "run") as run:
            run.return_value.returncode = 0
            notif.send()

        run.assert_called_once_with(
            ["osascript", "-e", notifierMac.CMD, title, info],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_mac_notifier_warns_when_subprocess_fails(self):
        notif = notifierMac.Notifier("Title", "Info")

        with patch.object(notifierMac.subprocess, "run") as run:
            run.return_value.returncode = 1
            run.return_value.stderr = "syntax error"
            run.return_value.stdout = ""
            with patch.object(notifierMac.sys, "stderr") as stderr:
                with patch("builtins.print") as print_mock:
                    notif.send()

        print_mock.assert_called_once_with(
            "Warning: Could not send macOS notification: syntax error",
            file=stderr,
        )


if __name__ == "__main__":
    unittest.main()
