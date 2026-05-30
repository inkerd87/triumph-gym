import sys
import random
from datetime import datetime, timedelta
from web_app import app
from models.database import get_db
from models.session import ClassSession
from models.trainer import Trainer

def populate_schedule():
    with app.app_context():
        db = next(get_db())
        
        trainers = db.query(Trainer).all()
        if not trainers:
            print("No trainers found, cannot populate schedule.")
            return

        today = datetime.now().date()
        class_titles = ["Йога", "Кроссфит", "Пилатес", "Сайклинг", "Бокс", "Стретчинг", "TRX", "Zumba"]
        
        start_date = today - timedelta(days=7)
        for i in range(15):
            current_date = start_date + timedelta(days=i)
            num_classes = random.randint(2, 4)
            for j in range(num_classes):
                trainer = random.choice(trainers)
                title = random.choice(class_titles)
                hour = random.randint(9, 20)
                minute = random.choice([0, 15, 30, 45])
                
                start_time = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)
                duration = random.choice([45, 60, 90])
                
                session = ClassSession(
                    trainer_id=trainer.id,
                    start_time=start_time,
                    duration_minutes=duration,
                    title=title
                )
                db.add(session)
        
        db.commit()
        print("Schedule populated successfully!")

if __name__ == "__main__":
    populate_schedule()
