import sys, os, threading, time, urllib.request
sys.path.insert(0, os.getcwd())
import headless_server as hs
api, srv = hs._make_server('127.0.0.1', 8899, None)
t = threading.Thread(target=srv.serve_forever, daemon=True)
t.start()
time.sleep(1.0)
try:
    r = urllib.request.urlopen('http://127.0.0.1:8899/', timeout=10)
    body = r.read()
    print('HTTP', r.status, 'bytes', len(body))
    print('has title:', ('AI' in body.decode('utf-8', 'replace')))
except Exception as e:
    print('ERR', type(e).__name__, e)
try:
    r = urllib.request.urlopen('http://127.0.0.1:8899/api/ping', timeout=20)
    print('API', r.status, r.read()[:120])
except Exception as e:
    print('API ERR', type(e).__name__, e)
srv.shutdown()
print('done')
