"""Real HTTP regression: structured events and no token-bearing transport URL."""
import io
import json
import logging
import unittest
from integration.test_original_http_stubbed import HAS_FLASK, SOURCES, load_app, local_http, http_call

@unittest.skipUnless(HAS_FLASK, 'Real Flask required')
class StructuredLogsHTTP(unittest.TestCase):
    def test_json_event_emitted_without_query_token_or_raw_chat_id(self):
        app=load_app(SOURCES['after'], 'work_structured_logs')
        output=io.StringIO(); transport=io.StringIO()
        application_handler=logging.StreamHandler(output)
        application_handler.setFormatter(logging.Formatter('%(message)s'))
        transport_handler=logging.StreamHandler(transport)
        app.logger.addHandler(application_handler)
        logging.getLogger('werkzeug').addHandler(transport_handler)
        try:
            with local_http(app) as base:
                status,_,headers=http_call(base,'/users/info?id_token=SYNTHETIC_URL_SECRET')
                self.assertEqual(status,401)
                http_call(base,'/chats/PRIVATE_CHAT_MARKER','DELETE')
            events=[json.loads(line) for line in output.getvalue().splitlines()
                    if json.loads(line).get('event') == 'http_request']
            self.assertEqual(len(events),2)
            self.assertEqual(events[0]['request_id'],headers['X-Request-ID'])
            self.assertEqual(events[0]['status'],401)
            self.assertEqual(events[1]['route'],'/chats/<chat_id>')
            self.assertNotIn('SYNTHETIC_URL_SECRET',output.getvalue()+transport.getvalue())
            self.assertNotIn('PRIVATE_CHAT_MARKER',output.getvalue()+transport.getvalue())
        finally:
            app.logger.removeHandler(application_handler)
            logging.getLogger('werkzeug').removeHandler(transport_handler)

if __name__=='__main__':unittest.main(verbosity=2)
