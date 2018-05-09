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
        _, res = self.redis.blpop(self.media_q)
        res = json.loads(res)

        try:
            print('*** Crawl Worker Loading: ' + res['url'])
            r = requests.get(self.host_prefix + '/store/record/id_/' + res['url'], stream=True)
            try:
                r.raw.read(1024)
                r.raw.close()
            except:
                pass
            #for chunk in r.iter_content(8192):
            #    pass

        except:
            traceback.print_exc()


# ============================================================================
if __name__ == "__main__":
    c = CaptureWorker(8080)
    time.sleep(1)
    c()
