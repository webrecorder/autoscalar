from gevent import monkey; monkey.patch_all()

import os
import redis
import time
import requests
import logging
import json
import gevent
import websocket
import traceback

import re
from urllib.parse import quote

logger = logging.getLogger('autobrowser')
DEBUG_ALL = False


# ============================================================================
class AutoBrowser(object):
    CDP_JSON = 'http://{ip}:9222/json'
    CDP_JSON_NEW = 'http://{ip}:9222/json/new'

    REQ_BROWSER_URL = 'http://shepherd:9020/request_browser/{browser}'
    INIT_BROWSER_URL = 'http://shepherd:9020/init_browser?reqid={0}'

    REQ_KEY = 'req:{id}'

    WAIT_TIME = 0.5

    NEW_PAGE_WAIT_TIME = 40.0

    def __init__(self, redis, browser_image, browser_q,
                 reqid=None, cdata=None, num_tabs=1,
                 pubsub=False, tab_class=None, tab_opts=None):

        self.redis = redis

        self.browser_id = browser_image
        self.browser_q = browser_q

        self.cdata = cdata

        self.reqid = reqid

        self.num_tabs = num_tabs

        self.tab_class = tab_class or AutoTab
        self.tab_opts = tab_opts or {}

        self.running = False

        if pubsub:
            self.pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
            gevent.spawn(self.recv_pubsub_loop)
        else:
            self.pubsub = None

        self.init(self.reqid)

        logger.debug('Auto Browser Inited: ' + self.reqid)

    def listener(self, *args, **kwargs):
        pass

    def queue_urls(self, urls, hops=0):
        for url in urls:
            self.redis.rpush(self.browser_q, json.dumps({'url': url, 'hops': hops}))

    def get_ip_for_reqid(self, reqid):
        ip = self.redis.hget('req:' + reqid, 'ip')
        return ip

    def reinit(self):
        if self.running:
            return

        self.init()

        logger.debug('Auto Browser Re-Inited: ' + self.reqid)

    def init(self, reqid=None):
        self.tabs = []
        ip = None
        tab_datas = None

        self.close()

        # attempt to connect to existing browser/tab
        if reqid:
            #ip = self.browser_mgr.get_ip_for_reqid(reqid)
            ip = self.get_ip_for_reqid(reqid)
            if ip:
                tab_datas = self.find_browser_tabs(ip)

            # ensure reqid is removed
            if not tab_datas:
                self.listener('browser_removed', reqid)

        # no tab found, init new browser
        if not tab_datas:
            reqid, ip, tab_datas = self.init_new_browser()

        self.reqid = reqid
        self.ip = ip
        self.tabs = []

        for tab_data in tab_datas:
            tab = self.tab_class(self, tab_data, **self.tab_opts)
            self.tabs.append(tab)

        self.listener('browser_added', reqid)

        if self.pubsub:
            self.pubsub.subscribe('from_cbr_ps:' + reqid)

    def find_browser_tabs(self, ip, url=None, require_ws=True):
        try:
            res = requests.get(self.CDP_JSON.format(ip=ip))
            tabs = res.json()
        except:
            return {}

        filtered_tabs = []

        for tab in tabs:
            #logger.debug(str(tab))

            if require_ws and 'webSocketDebuggerUrl' not in tab:
                continue

            if tab.get('type') == 'page' and (not url or url == tab['url']):
                filtered_tabs.append(tab)

        return filtered_tabs

    def get_tab_for_url(self, url):
        tabs = self.find_browser_tabs(self.ip, url=url, require_ws=False)
        if not tabs:
            return None

        id_ = tabs[0]['id']
        for tab in self.tabs:
            if tab.tab_id == id_:
                return tab

        return None

    def add_browser_tab(self, ip):
        try:
            res = requests.get(self.CDP_JSON_NEW.format(ip=ip))
            tab = res.json()
        except Exception as e:
            logger.error('*** ' + str(e))

        return tab

    def stage_new_browser(self, browser_id, data):
        try:
            req_url = self.REQ_BROWSER_URL.format(browser=browser_id)
            res = requests.post(req_url, data=data)

        except Exception as e:
            logger.debug(str(e))
            msg = 'Browser <b>{0}</b> could not be requested'.format(browser_id)
            return {'error_message': msg}

        reqid = res.json().get('reqid')

        if not reqid:
            msg = 'Browser <b>{0}</b> is not available'.format(browser_id)
            return {'error_message': msg}

        return reqid

    def init_new_browser(self):
        #launch_res = self.browser_mgr.request_new_browser(self.cdata)
        #reqid = launch_res['reqid']
        reqid = self.stage_new_browser(self.browser_id, self.cdata)

        # wait for browser init
        while True:
            res = requests.get(self.INIT_BROWSER_URL.format(reqid))

            try:
                res = res.json()
            except Exception as e:
                logger.debug('Browser Init Failed: ' + str(e))
                return None, None, None

            if 'cmd_port' in res:
                break

            #if reqid not in self.req_cache:
            #    logger.debug('Waited too long, cancel browser launch')
            #    return False

            logger.debug('Waiting for Browser: ' + str(res))
            time.sleep(self.WAIT_TIME)

        logger.debug('Launched: ' + str(res))

        self.running = True

        # wait to find first tab
        while True:
            tab_datas = self.find_browser_tabs(res['ip'])
            if tab_datas:
                logger.debug(str(tab_datas))
                break

            time.sleep(self.WAIT_TIME)
            logger.debug('Waiting for first tab')

        # add other tabs
        for tab_count in range(self.num_tabs - 1):
            tab_data = self.add_browser_tab(res['ip'])
            tab_datas.append(tab_data)

        return reqid, res['ip'], tab_datas

    def pubsub_listen(self):
        try:
            for item in self.pubsub.listen():
                yield item
        except:
            return

    def recv_pubsub_loop(self):
        logger.debug('Start PubSub Listen')

        for item in self.pubsub_listen():
            try:
                if item['type'] != 'message':
                    continue

                msg = json.loads(item['data'])
                logger.debug(str(msg))

                if msg['ws_type'] == 'remote_url':
                    pass

                elif msg['ws_type'] == 'autoscroll_resp':
                    tab = self.get_tab_for_url(msg['url'])
                    if tab:
                        tab.behavior_done()

            except:
                traceback.print_exc()

    def send_pubsub(self, msg):
        if not self.reqid:
            return

        channel = 'to_cbr_ps:' + self.reqid
        msg = json.dumps(msg)
        self.redis.publish(channel, msg)

    def close(self):
        self.running = False

        if self.pubsub:
            self.pubsub.unsubscribe()

        if self.reqid:
            self.listener('browser_removed', self.reqid)

        for tab in self.tabs:
            tab.close()

        self.reqid = None


# ============================================================================
class CallRDP(object):
    def __init__(self, func, method=''):
        self.func = func
        self.method = method

    def __getattr__(self, name):
        return CallRDP(self.func, self.method + '.' + name if self.method else name)

    def __call__(self, **kwargs):
        callback = kwargs.pop('callback', None)
        self.func({"method": self.method,
                   "params": kwargs}, callback=callback)


# ============================================================================
class AutoTab(object):
    def __init__(self, browser, tab_data, *args, **kwargs):
        self.tab_id = tab_data['id']
        self.browser = browser
        self.redis = browser.redis
        self.browser_q = browser.browser_q
        self.listener = browser.listener

        self.tab_data = tab_data
        self._behavior_done = False
        self._replaced_with_devtools = False

        self.rdp = CallRDP(self.send_ws)

        self.id_count = 0
        self.frame_id = ''
        self.curr_mime = ''
        self.curr_url = ''
        self.hops = 0

        self.scopes = []

        self.index_check_url = None

        self.callbacks = {}

        self._init_ws()

        cookies = kwargs.get('cookies')
        if cookies:
            logger.debug('SENDING COOKIES: ' + str(cookies))
            for cookie in cookies:
                params = {'name': cookie['name'],
                          'value': cookie['value'],
                          'url': 'http://' + cookie['domain'] + '/',
                          'path': '/'
                         }

                #self.send_ws({"method": "Network.setCookie", "params": params})
                self.rdp.Network.setCookie(**params)

            #self.send_ws({"method": "Network.setCookies", "params": {"cookies": cookies}}, cookies_resp)
            time.sleep(1.0)

        gevent.spawn(self.recv_ws_loop)

        # quene next url!
        self._next_ge = None
        self.queue_next(now=True)

    def _init_ws(self):
        self.ws = websocket.create_connection(self.tab_data['webSocketDebuggerUrl'])

        self.rdp.Page.enable()

        #self.rdp.Network.enable(maxTotalBufferSize=0, maxResourceBufferSize=0, maxPostDataSize=0)
        self.rdp.Debugger.enable()
        #self.rdp.Debugger.setSkipAllPauses(skip=True)
        self.rdp.DOMDebugger.setEventListenerBreakpoint(eventName='playing')

    def replace_devtools(self):
        self._replaced_with_devtools = False
        while self.browser.running:
            logger.debug('Waiting for devtools to close')
            time.sleep(5.0)
            try:
                self._init_ws()
                return
            except Exception as e:
                logger.debug(str(e))

    def queue_next(self, now=False):
        self._behavior_done = False

        # extend recording openness
        #self.auto.recording.is_open()
        logger.debug('Queue Next')

        try:
            if self._next_ge:
                self._next_ge.kill()
                self._next_ge = None
        except:
            pass

        if now:
            self._next_ge = gevent.spawn(self.wait_queue)
        else:
            self._next_ge = gevent.spawn_later(self.browser.NEW_PAGE_WAIT_TIME,
                                               self.wait_queue)

    def already_recorded(self, url):
        if not self.index_check_url:
            return False

        url = self.index_check_url + '&url=' + quote(url)
        try:
            res = requests.get(url)
            return res.text != ''
        except Exception as e:
            logger.debug(str(e))
            return False

    def should_visit(self, url):
        """ return url that should be visited, or None to skip this url
        """
        if '#' in url:
            url = url.split('#', 1)[0]

        if self.already_recorded(url):
            logger.debug('Skipping Dupe: ' + url)
            return None

        if self.scopes:
            for scope in self.scopes:
                if scope.search(url):
                    logger.debug('In scope: ' + scope.pattern)
                    return url

            return None

        return url

    def wait_queue(self):
        # reset to empty url to indicate previous page is done
        self.listener('tab_added', self.browser.reqid, self.tab_id, '')
        url_req_data = None
        url_req = None

        while self.browser.running:
            name, url_req_data = self.redis.blpop(self.browser_q)
            url_req = json.loads(url_req_data)

            url_req['url'] = self.should_visit(url_req['url'])
            if url_req['url']:
                break

        if not url_req:
            logger.debug('Auto Running?: ' + str(self.browser.running))
            return

        def save_frame(resp):
            frame_id = resp['result'].get('frameId')
            if frame_id:
                self.frame_id = frame_id

        try:
            logger.debug('Queuing Next: ' + str(url_req))

            self.hops = url_req.get('hops', 0)
            self.curr_url = url_req['url']

            #self.send_ws({"method": "Page.navigate", "params": {"url": self.curr_url}},
            #             save_frame)
            self.rdp.Page.navigate(url=self.curr_url, callback=save_frame)

            self.listener('tab_added', self.browser.reqid, self.tab_id, url_req['url'])

        except Exception as e:
            logger.error(' *** ' + str(e))
            if url_req_data:
                self.redis.rpush(self.browser_q, url_req_data)

    def recv_ws_loop(self):
        logger.debug('Tab Loop Started')
        try:
            while self.browser.running:
                try:
                    resp = self.ws.recv()
                    resp = json.loads(resp)
                except Exception as re:
                    if self._replaced_with_devtools:
                        self.replace_devtools()
                        continue
                    else:
                        raise

                try:
                    method = resp.get('method')

                    if 'result' in resp and 'id' in resp:
                        self.handle_result(resp)

                    elif method == 'Page.frameNavigated':
                        self.handle_frameNavigated(resp)

                    elif method == 'Page.loadEventFired':
                        self.handle_done_loading()

                    elif method == 'Inspector.detached':
                        self.handle_InspectorDetached(resp)

                    elif method == 'Debugger.paused':
                        self.handle_DebuggerPaused(resp)
                        self.rdp.Debugger.resume()

                except Exception as re:
                    logger.warning('*** Error handling response')
                    logger.warning(str(re))

                # LOG ALL ERROR MESSAGES
                if DEBUG_ALL or 'error' in resp:
                    logger.debug(str(resp))

        except Exception as e:
            logger.error(str(e))

        finally:
            self.close()
            logger.debug('Tab Loop Done')

    def behavior_done(self):
        if self._behavior_done:
            return

        self._behavior_done = True
        self.load_links()

    def load_links(self):
        if not self.hops:
            self.queue_next()
            return False

        def handle_links(resp):
            links = json.loads(resp['result']['result']['value'])

            #logger.debug('Links')
            #logger.debug(str(links))

            for link in links:
                url_req = {'url': link}
                # set hops if >0
                if self.hops > 1:
                    url_req['hops'] = self.hops - 1

                self.redis.rpush(self.browser_q, json.dumps(url_req))

            self.queue_next()

        self.eval('JSON.stringify(window.extractLinks ? window.extractLinks() : [])', handle_links)

    def handle_result(self, resp):
        callback = self.callbacks.pop(resp['id'], None)
        if callback:
            try:
                callback(resp)
            except Exception as e:
                logger.debug(str(e))
        else:
            logger.debug('No Callback found for: ' + str(resp['id']))

    def handle_DebuggerPaused(self, resp):
        #logger.debug('*** PAUSED')
        #logger.debug(str(resp))

        if resp['params']['data']['eventName'] == 'listener:playing':
            self.queue_next(now=True)

    def handle_InspectorDetached(self, resp):
        if resp['params']['reason'] == 'replaced_with_devtools':
            self._replaced_with_devtools = True

    def handle_frameStoppedLoading(self, resp):
        frame_id = resp['params']['frameId']

        # ensure top-frame stopped loading
        if frame_id != self.frame_id:
            return

        self.handle_done_loading()

    def handle_done_loading(self):
        # if not html, continue
        if self.curr_mime != 'text/html':
            self.queue_next(now=True)
            return

        if False and self.autoscroll:
            logger.debug('AutoScroll Start')
            self.browser.send_pubsub({'ws_type': 'autoscroll'})
            gevent.spawn_later(30, self.behavior_done)
        else:
            self.load_links()

    def handle_frameNavigated(self, resp):
        frame = resp['params']['frame']

        # ensure target frame
        if frame['id'] != self.frame_id:
            return

        # if not top frame, skip
        if frame.get('parentId'):
            return

        self.curr_mime = frame['mimeType']

        # if text/html, already should have been added
        #if self.curr_mime != 'text/html':
        #    page = {'url': frame['url'],
        #            'title': frame['url'],
        #            'timestamp': self.cdata['request_ts'] or timestamp_now(),
        #            'browser': self.cdata['browser'],
        #           }

        #    self.auto.recording.add_page(page, False)

    def send_ws(self, data, callback=None):
        self.id_count += 1
        data['id'] = self.id_count
        if callback:
            self.callbacks[self.id_count] = callback

        if self.ws:
            self.ws.send(json.dumps(data))
        else:
            logger.debug('WS Already Closed')

    def eval(self, expr, callback=None):
        #self.send_ws({"method": "Runtime.evaluate", "params": {"expression": expr}}, callback)
        self.rdp.Runtime.evaluate(expression=expr, callback=callback)

    def close(self):
        try:
            if self.ws:
                self.ws.close()

            self.listener('tab_remove', self.browser.reqid, self.tab_id)
        except:
            pass

        finally:
            self.ws = None


# ============================================================================
if __name__ == "__main__":
    AutoManager().start()
