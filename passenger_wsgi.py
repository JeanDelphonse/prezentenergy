import sys, os, traceback
sys.path.insert(0, os.path.dirname(__file__))                                                                                        
  
try:
    from app import create_app
    application = create_app("production")
except Exception:
    err = traceback.format_exc()
    def application(environ, start_response):
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [err.encode()]