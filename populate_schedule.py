import random
from datetime import datetime, timedelta

from models.database import SessionLocal
from models.session import ClassSession
from models.trainer import Trainer


def populate_schedule():
    db = SessionLocal()
    try:
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
            for _j in range(num_classes):
                trainer = random.choice(trainers)
                title = random.choice(class_titles)
                hour = random.randint(9, 20)
                minute = random.choice([0, 15, 30, 45])

                start_time = datetime.combine(current_date, datetime.min.time()) + timedelta(
                    hours=hour, minutes=minute
                )
                duration = random.choice([45, 60, 90])

                db.add(
                    ClassSession(
                        trainer_id=trainer.id,
                        start_time=start_time,
                        duration_minutes=duration,
                        title=title,
                    )
                )

        db.commit()
        print("Schedule populated successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    populate_schedule()
