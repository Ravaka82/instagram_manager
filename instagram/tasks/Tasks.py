import schedule
import time
from datetime import datetime
from threading import Thread

from instagram.core.instagram_service import InstagramService

class TaskScheduler:
    execution_time = datetime(2024, 1, 11, 23, 19)  # Date et heure d'exécution statiques

    @staticmethod
    def faire_coucou():
        print("Coucou!")

    @staticmethod
    def job():
        #current_time = datetime.now()
        #print("current_time = ", current_time)
        #if current_time >= TaskScheduler.execution_time:
        TaskScheduler.publication()
        return schedule.CancelJob  # Annule la tâche après son exécution
    @staticmethod   
    def publication():
        service = InstagramService()
        service.publication_planifier()
            


# Planifie la tâche toutes les minutes
schedule.every(1).minute.do(TaskScheduler.job)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)  # Attend 1 seconde pour éviter une boucle infinie trop rapide

# Démarre la planification dans un thread séparé
def start_scheduler():
    scheduler_thread = Thread(target=run_schedule)
    scheduler_thread.daemon = True
    scheduler_thread.start()
