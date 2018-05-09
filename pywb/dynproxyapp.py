from gevent.monkey import patch_all; patch_all()

from pywb.apps.frontendapp import FrontEndApp

import os
import redis
import fakeredis
import logging

from pywb.apps.cli import ReplayCli
from werkzeug.routing import Map, Rule
from pywb.apps.wbrequestresponse import WbResponse
from pywb.warcserver.warcserver import register_source
from pywb.warcserver.index.indexsource import LiveIndexSource, NotFoundException


# ============================================================================
class DynProxyPywb(FrontEndApp):
    def __init__(self, config_file='./config.yaml', custom_config=None):
        register_source(PrefixFilterIndexSource)

        super(DynProxyPywb, self).__init__(config_file=config_file,
                                           custom_config=custom_config)
        try:
            print('REDIS: ' + os.environ.get('CLIENT_REDIS_URL', ''))
            self.redis = redis.StrictRedis.from_url(os.environ['CLIENT_REDIS_URL'], decode_responses=True)
        except Exception as e:
            print('Default to FakeRedis: ' + str(e))
            self.redis = fakeredis.FakeStrictRedis()

    def proxy_route_request(self, url, environ):
        key = 'ip:' + environ['REMOTE_ADDR']
        prefix = self.redis.hget(key, 'pywb_prefix')
        if prefix:
            return prefix + url
        else:
            return super(DynProxyPywb, self).proxy_route_request(url, environ)


#=============================================================================
class PrefixFilterIndexSource(LiveIndexSource):
    def __init__(self):
        super(LiveIndexSource, self).__init__()
        self.filter_prefix = os.environ.get('PYWB_FILTER_PREFIX', '')
        self.redirect_prefix = os.environ.get('SCALAR_HOST', '')

    def get_load_url(self, params):
        url = params['url']

        if self.filter_prefix:
            print('TESTING: ' + url)
            if url.startswith(self.filter_prefix):
                url = self.redirect_prefix + url[len(self.filter_prefix):]
                print('NEW URL: ' + url)
            else:
                print('Skipping')
                raise NotFoundException('Skipping: ' + url)

        return url

    @classmethod
    def init_from_config(cls, config):
        return cls.init_from_string(config['type'])

    @classmethod
    def init_from_string(cls, value):
        if value == 'live_filter':
            return cls()

        return None


#=============================================================================
class WaybackCli(ReplayCli):
    def load(self):
        super(WaybackCli, self).load()
        return DynProxyPywb(custom_config=self.extra_config)


#=============================================================================
def wayback(args=None):
    #import gevent
    #gevent.spawn(CaptureWorker(8080))

    return WaybackCli(args=args,
                      default_port=8080,
                      desc='pywb Wayback Machine Server').run()


#=============================================================================
if __name__ == "__main__":
    wayback()
else:
    application = DynProxyPywb()

