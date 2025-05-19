from plyer import notification
import time, pathlib

def always_true():
    return True

class Notifier:
    def __init__(self, title: str, info: str, state=always_true):
        self.title, self.info = title, info
        self.status_check = state

    def send(self):
        dir = pathlib.Path(__file__).parent.absolute().as_posix() + '/grouch.ico'
        notification.notify(
            title=self.title,
            message=self.info,
            app_icon=dir,
            timeout=7
        )
        time.sleep(7)

    def run(self):
        while not self.status_check():
            continue
        self.send()

    def run_async(self):
        if self.status_check():
            self.send()

    def run_force(self):
        self.send()
