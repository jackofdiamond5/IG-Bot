import time
import schedule
import threading
from dotenv import load_dotenv
from schedule import Scheduler


# load all variables in the .env file
def load_env_variables():
    load_dotenv()


# schedule tasks at a specific time or in a specific timeframe
# runs on a separate thread
# scheduler = settings.ParallelScheduler()
# scheduler.every().day.at("00:00").do(job)
# cease = scheduler.run_continuously()
# cease.set() will stop the scheduler
class ParallelScheduler(Scheduler):
    def __init__(self):
        Scheduler.__init__(self)

    # https://github.com/mrhwick/schedule/blob/master/schedule/__init__.py#L63
    def run_continuously(self, interval=1):
        stop_continuous_running = threading.Event()

        class ScheduleThread(threading.Thread):
            @classmethod
            def run(cls):
                while not stop_continuous_running.is_set():
                    self.run_pending()
                    time.sleep(interval)
        continuous_thread = ScheduleThread()
        continuous_thread.start()
        return stop_continuous_running
