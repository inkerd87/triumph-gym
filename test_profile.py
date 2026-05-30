import requests
resp = requests.get('http://127.0.0.1:5000/clients/1')
print(resp.status_code)
print(resp.text)
