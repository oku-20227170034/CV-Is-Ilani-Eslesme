import urllib.request
import urllib.error
import json

url = 'http://127.0.0.1:8000/api/v1/job-matcher/analyze'
data = json.dumps({'cv_text': 'test cv', 'position': 'yazilim'}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

try:
    res = urllib.request.urlopen(req)
    out = res.read().decode('utf-8')
    with open('test_output.json', 'w', encoding='utf-8') as f:
        f.write(out)
    print("Success! Output saved to test_output.json")
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code}")
    out = e.read().decode('utf-8')
    with open('test_output.json', 'w', encoding='utf-8') as f:
        f.write(out)
    print("Error body saved to test_output.json")
except Exception as e:
    print(f"Other Error: {e}")
