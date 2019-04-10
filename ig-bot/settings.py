import time
import threading
from dotenv import load_dotenv
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


# load all variables in the .env file
def load_env_variables():
    load_dotenv()


def get_orgname(config_json):
    return config_json.get("orgName", None)


def get_sprint_name(config_json):
    return config_json.get("projects", {}).get("currentSprint", {}).get("name", None)


def get_sprint_columns(config_json):
    return config_json.get("projects", {}).get("currentSprint", {}).get("columns", None)


def get_main_proj(config_json):
    return config_json.get("projects", {}).get("masterBacklog", None).get("name", None)


def get_proj_columns(config_json, proj_name):
    projects = config_json.get("projects")
    proj_types = [name for name in projects]
    for p_type in proj_types:
        name = projects.get(p_type, {}).get("name", None)
        if name == proj_name:
            # the first column should be "Todo"
            # the second column should be "In progress"
            # the third column should be "Done"
            return projects.get(p_type, {}).get("columns", [])
