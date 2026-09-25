"""Serve docs/ in this process and run the browser checks against it.

A separately backgrounded server does not reliably survive between commands here, and
the checks need a real HTTP origin: the injection fallback does not load every data file,
so layers that depend on them appear to be missing.
"""
import functools, http.server, os, runpy, sys, threading
ROOT = '/Users/christianstrobele/code/migration-bw'
# The handler must be pinned to docs/ explicitly: it otherwise resolves paths against
# the working directory at request time, which this script changes back to the repo root.
srv = http.server.ThreadingHTTPServer(
    ('127.0.0.1', 8042),
    functools.partial(http.server.SimpleHTTPRequestHandler,
                      directory=os.path.join(ROOT, 'docs')))
threading.Thread(target=srv.serve_forever, daemon=True).start()
os.chdir(ROOT)
sys.argv = ['browser_smoke.py', '--url', 'http://127.0.0.1:8042', '--require-geometry']
try:
    runpy.run_path(os.path.join(ROOT, 'tests/browser_smoke.py'), run_name='__main__')
finally:
    srv.shutdown()
