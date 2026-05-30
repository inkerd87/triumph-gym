import sys
from web_app import app

def test_export():
    with app.test_client() as client:
        # Login
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        
        # Hit export route
        resp = client.get('/report/export?date_from=2026-05-01&date_to=2026-05-31')
        print("Export Status:", resp.status_code)
        print("Content Type:", resp.headers.get("Content-Type"))
        print("Content Disposition:", resp.headers.get("Content-Disposition"))
        
        # Test dashboard
        resp2 = client.get('/')
        print("Dashboard Status:", resp2.status_code)

if __name__ == "__main__":
    test_export()
