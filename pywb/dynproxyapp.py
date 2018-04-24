from pywb.apps.frontendapp import FrontEndApp

import os
import redis
import fakeredis
import logging

from pywb.apps.cli import ReplayCli
from werkzeug.routing import Map, Rule
from pywb.apps.wbrequestresponse import WbResponse


# ============================================================================
class DynProxyPywb(FrontEndApp):
    def __init__(self, config_file='./config.yaml', custom_config=None):
        super(DynProxyPywb, self).__init__(config_file=config_file,
                                           custom_config=custom_config)
        try:
            print('REDIS: ' + os.environ.get('REDIS_URL', ''))
            self.redis = redis.StrictRedis.from_url(os.environ['REDIS_URL'], decode_responses=True)
        except Exception as e:
            print('Default to FakeRedis: ' + str(e))
            self.redis = fakeredis.FakeStrictRedis()

    def proxy_route_request(self, url, environ):
        coll = self.redis.hget('ip:' + environ['REMOTE_ADDR'], 'coll')
        print('COLL', coll)
        if coll:
            return '/{0}/id_/{1}'.format(coll, url)
        else:
            return super(DynProxyPywb, self).proxy_route_request(url, environ)


#=============================================================================
class WaybackCli(ReplayCli):
    def load(self):
        super(WaybackCli, self).load()
        return DynProxyPywb(custom_config=self.extra_config)


#=============================================================================
def wayback(args=None):
    return WaybackCli(args=args,
                      default_port=8080,
                      desc='pywb Wayback Machine Server').run()


#=============================================================================
if __name__ == "__main__":
    wayback()
