import sys
from web_app import app

def run_test():
    with app.test_client() as client:
        # First login
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        
        # Then get schedule
        resp = client.get('/schedule')
        print("Schedule status:", resp.status_code)
        if resp.status_code == 500:
            print("Server error!")
            print(resp.text)

if __name__ == "__main__":
    run_test()
