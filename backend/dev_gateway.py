"""One-command, dependency-free, loopback-only gateway for the local lab.

This is for convenient development when Docker is unavailable, NOT production.
"""
import http.client
import mimetypes
import os
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

STATIC=Path(__file__).resolve().parent.parent/'dashboard'

class Gateway(BaseHTTPRequestHandler):
    def log_message(self,format,*args): pass
    def do_GET(self): self.handle_route()
    def do_POST(self): self.handle_route()
    def do_PUT(self): self.handle_route()
    def do_DELETE(self): self.handle_route()
    def handle_route(self):
        parsed=urlsplit(self.path)
        # Reject ambiguous HTTP framing and absolute targets at the development proxy.
        # This simple gateway does not implement chunked request decoding.
        if self.headers.get('Transfer-Encoding') or parsed.scheme or parsed.netloc:
            return self.error(400)
        if parsed.path=='/metrics':
            return self.error(403)
        if parsed.path.startswith('/api/'):
            try:
                conn=http.client.HTTPConnection('127.0.0.1',int(os.getenv('PORT','8091')),timeout=5)
                content_length=self.headers.get('Content-Length')
                try:
                    size=int(content_length) if content_length else 0
                except (ValueError, TypeError):
                    return self.error(400)
                if size<0 or size>32768:
                    return self.error(413)
                payload=self.rfile.read(size) if size else None
                forward={k:self.headers[k] for k in ('Authorization','Content-Type') if k in self.headers}
                conn.request(self.command,self.path,body=payload,headers=forward)
                response=conn.getresponse()
                body=response.read()
                self.send_response(response.status)
                for key,value in response.getheaders():
                    if key.lower() in {'content-type','x-request-id','x-coursesphere-instance','cache-control','content-security-policy','x-content-type-options'}:
                        self.send_header(key,value)
                self.send_header('Content-Length',str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                conn.close()
            except (ConnectionError,TimeoutError,OSError,ValueError):
                self.error(502)
            return
        if self.command!='GET': return self.error(405)
        if parsed.path in ('/','/lab','/lab/'):
            target=STATIC/'index.html'
        elif parsed.path in ('/lab/style.css','/lab/app.js'):
            target=STATIC / parsed.path.rsplit('/',1)[1]
        else:
            return self.error(404)
        body=target.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type',mimetypes.guess_type(target.name)[0] or 'text/html')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; object-src 'none'")
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=()')
        self.send_header('Cross-Origin-Opener-Policy','same-origin')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def error(self,status):
        self.send_response(status)
        self.send_header('Content-Length','0')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=()')
        self.end_headers()

if __name__=='__main__':
    port=int(os.getenv('GATEWAY_PORT','8080'))
    print(f'Local dashboard: http://127.0.0.1:{port}/lab/',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Gateway).serve_forever()
