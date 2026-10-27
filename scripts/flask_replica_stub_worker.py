#!/usr/bin/env python3
"""Local-only worker: actual patched Flask app + synthetic service adapters.

Only used for controlled AppSec/SRE tests. NEVER starts the upstream API against
real Firebase or any external service; the app is created by the HTTP test harness.
"""
import os
from werkzeug.serving import make_server
from integration.test_original_http_stubbed import load_app, SOURCES


def main():
    host='127.0.0.1'
    port=int(os.environ['COURSESPHERE_TEST_PORT'])
    name=os.environ['COURSESPHERE_TEST_INSTANCE']
    if name not in ('flask-a', 'flask-b') or not (1024 <= port <= 65535):
        raise SystemExit('Unsafe test worker settings')
    app=load_app(SOURCES['after'], 'original_flask_replicated_'+name.replace('-', '_'))

    @app.after_request
    def instance_header(response):
        response.headers['X-CourseSphere-Test-Instance']=name
        return response

    server=make_server(host, port, app, threaded=True,
                      request_handler=app.config.get('SAFE_REQUEST_HANDLER'))
    print('local Flask test worker started', flush=True)
    server.serve_forever()


if __name__=='__main__':
    main()
