import subprocess
import time

CMD = '''
on run argv
  display notification (item 2 of argv) with title (item 1 of argv)
end run
'''

DEFAULT_CHECK_INTERVAL = 30


def always_true():
    return True


class Notifier:
    def __init__(self, title: str, info: str, state=always_true):
        self.title, self.info = title, info
        self.status_check = state

    def send(self):
        subprocess.run(
            ["osascript", "-e", CMD, self.title, self.info],
            check=False,
        )

    def run(self, check_interval=DEFAULT_CHECK_INTERVAL):
        while not self.status_check():
            time.sleep(check_interval)
        self.send()

    def run_async(self):
        if self.status_check():
            self.send()

    def run_force(self):
        self.send()
