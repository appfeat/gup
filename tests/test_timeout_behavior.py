import gup.__main__ as gup
import subprocess
import time

class FakeProc:
    def __init__(self, finish_after):
        self.start = time.time()
        self.finish_after = finish_after

    def poll(self):
        if time.time() - self.start > self.finish_after:
            return 0
        return None

    def kill(self):
        pass

def test_wait_with_countdown_completes():
    proc = FakeProc(finish_after=1)
    assert gup.wait_with_countdown(proc, timeout=3)

def test_wait_with_countdown_times_out():
    proc = FakeProc(finish_after=10)
    assert not gup.wait_with_countdown(proc, timeout=1)
