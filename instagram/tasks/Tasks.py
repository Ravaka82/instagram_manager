import schedule
import time
from datetime import datetime
from threading import Thread, Lock
import os

from instagram.core.instagram_service import InstagramService

class TaskScheduler:
    lock = Lock()  
    last_execution_time = None 

    @staticmethod
    def faire_coucou():
        print("Coucou! ", datetime.now())
        
    @staticmethod
    def publication():
        service = InstagramService()
        service.publication_planifier()

    @staticmethod
    def job():
        with TaskScheduler.lock: 
            now = datetime.now()
            
           
            if (TaskScheduler.last_execution_time is None or
                TaskScheduler.last_execution_time.minute != now.minute):
                if now.second == 0 and now.microsecond < 500000:  
                    TaskScheduler.publication()
                    TaskScheduler.last_execution_time = now


schedule.every(1).minute.at(":00").do(TaskScheduler.job)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(0.1) 

def start_scheduler():
    if os.environ.get("RUN_MAIN") == "true":  
        scheduler_thread = Thread(target=run_schedule)
        scheduler_thread.daemon = True
        scheduler_thread.start()


start_scheduler()
