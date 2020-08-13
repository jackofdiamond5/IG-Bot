import time
import threading
from schedule import Scheduler

# schedule tasks at a specific time or in a specific timeframe
# runs on a separate thread
# scheduler = settings.ParallelScheduler()
# scheduler.every().day.at("00:00").do(job)
# cease = scheduler.run_continuously()
# cease.set() will stop the scheduler


class ParallelScheduler(Scheduler):
    def __init__(self):
        Scheduler.__init__(self)

    def run_continuously(self, interval=1):
        "run the scheduler on a separate thread until 'stop_continuous_running' is 'true'"
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


# TODO tasks scheduler

# async def job():
#     NotImplemented

# def job_runner():
#     asyncio.run(job())

# scheduler = ParallelScheduler()
# scheduler.every().friday.at("22:00").do(job_runner)
# scheduler.run_continuously()