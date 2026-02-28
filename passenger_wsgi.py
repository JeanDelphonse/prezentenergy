import sys, os, traceback
_here = os.path.dirname(__file__)
sys.path.insert(0, _here)
sys.path.insert(0, os.path.join(_here, "vendor"))                                                                                        
  
try:
    from app import create_app
    application = create_app("production")
except Exception:
    err = traceback.format_exc()
    def application(environ, start_response):
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [err.encode()]