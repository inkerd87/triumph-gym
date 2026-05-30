import sys
from web_app import app

def test_schedule():
    with app.test_client() as client:
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        resp = client.get('/schedule')
        print("Schedule page status:", resp.status_code)
        
if __name__ == "__main__":
    test_schedule()
