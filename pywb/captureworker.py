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

            # first check head request
            head_response = self.sesh.head(res['url'], allow_redirects=True)

            if self.requeue(res, head_response):
                return

            req_url = self.host_prefix + '/store/record/oe_/' + res['url']

            with self.sesh.get(req_url, stream=True, allow_redirects=True) as r:
                self.requeue(res, r)
        except:
            traceback.print_exc()

    def requeue(self, res, r):
        # requeue with 'html_url' if current page may be html
        if not res.get('html_url'):
            return False

        if self.maybe_html(r.headers.get('Content-Type'), res['url']):
            #print('REQUEING',  res['url'])
            #self.redis.rpush(self.browser_q, json.dumps(res))
            new_query = {'url': res['html_url'], 'hops': 0}
            print('QUEING',  new_query)
            self.redis.rpush(self.browser_q, json.dumps(new_query))
            return True

        return False

    def maybe_html(self, content_type, url):
        content_type = content_type or ''
        content_type = content_type.split(';', 1)[0].rstrip()
        print('MIME', content_type)

        if content_type in ('text/html', 'application/x-html'):
            return True

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
