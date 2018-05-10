#from gevent.monkey import patch_all; patch_all()

import requests
import redis
import os
import json
import time
import traceback


# ============================================================================
class CaptureWorker(object):
    def __init__(self, port):
        self.redis = redis.StrictRedis.from_url(os.environ['QUEUE_REDIS_URL'], decode_responses=True)
        print('Worker Redis: ' + os.environ['QUEUE_REDIS_URL'])
        self.sesh = requests.Session()

        self.media_q = os.environ['MEDIA_Q']
        self.browser_q = os.environ['BROWSER_Q']

        self.host_prefix = 'http://localhost:' + str(port)
        self.running = True

        import socket
        print(socket.socket)

    def __call__(self):
        print('Worker Loop Started from: ' + self.media_q)
        while self.running:
            try:
                self.run()
            except:
                traceback.print_exc()
                time.sleep(1)

    def run(self):
        print('Waiting for url')
        _, data = self.redis.blpop(self.media_q)
        res = json.loads(data)
        self.sesh = requests.Session()

        try:
            print('*** Crawl Worker Loading: ' + res['url'])
            req_url = self.host_prefix + '/store/record/id_/' + res['url']
            with self.sesh.get(req_url, stream=True) as r:
                # requeue with 'html_url' if current page may be html
                if res.get('html_url'):
                    if self.maybe_html(r.headers.get('Content-Type', ''), res['url']):
                        self.redis.rpush(self.browser_q, data)
                        print('REQUEING',  res['html_url'])

        except:
            traceback.print_exc()

    def maybe_html(self, content_type, url):
        content_type = content_type.split(';', 1)[0].rstrip()
        if content_type in ('text/html', 'application/x-html'):
            return True

        print('MIME', content_type)

        if content_type:
            return False

        # assume if no ext then likely html
        if '.' not in url:
            return True
        else:
            return False


# ============================================================================
if __name__ == "__main__":
    c = CaptureWorker(8080)
    time.sleep(1)
    c()
