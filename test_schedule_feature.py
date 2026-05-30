import sys
from web_app import app
from datetime import datetime

def run_test():
    with app.test_client() as client:
        # First login
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        
        # Test GET current week
        resp = client.get('/schedule?week_offset=0')
        print("GET /schedule:", resp.status_code)
        
        # Test POST create class
        today = datetime.now().strftime("%Y-%m-%d")
        resp = client.post('/schedule', data={
            'action': 'create',
            'week_offset': '0',
            'title': 'Тестовая Тренировка',
            'date': today,
            'time': '12:00',
            'duration': '45',
            'trainer_id': '1'
        })
        print("POST /schedule create:", resp.status_code)
        
        # Test GET again to check if it's there
        resp = client.get('/schedule?week_offset=0')
        print("GET /schedule check created:", resp.status_code)
        if "Тестовая Тренировка" in resp.text:
            print("Successfully found 'Тестовая Тренировка' in schedule!")
        else:
            print("Error: Class not found in schedule html!")
            
if __name__ == "__main__":
    run_test()
