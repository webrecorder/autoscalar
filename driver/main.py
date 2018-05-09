import gevent.monkey; gevent.monkey.patch_all()
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

import logging
import json
import redis
import docker
import base64
import time
import os
import requests

from urllib.parse import urlsplit, urlunsplit

from bottle import debug, default_app, request, jinja2_view, TEMPLATE_PATH, static_file
from scalarbook import ScalarBook
from autobrowser import AutoBrowser, AutoTab


# ============================================================================
class Main(object):
    GSESH = 'ssesh:{0}'

    USER_IMAGE = 'dynpreserve/user-scalar:{0}'
    USER_IMAGE_PREFIX = 'dynpreserve/user-scalar'

    SCALAR_BASE_IMAGE = 'dynpreserve/scalar'
    PYWB_IMAGE = 'dynpreserve/pywb'

    START_URL_LABEL = 'dyn.start_url'

    VOL_PREFIX = 'dynpreserve-'

    NETWORK_NAME = 'scalar_default'

    REDIS_URL = 'redis://redis/2'

    NUM_BROWSERS = 4

    def __init__(self):
        debug(True)
        TEMPLATE_PATH.insert(0, './templates')
        logging.basicConfig(format='%(asctime)s: [%(levelname)s]: %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            level=logging.WARN)

        logging.getLogger('autobrowser').setLevel(logging.DEBUG)

        self.redis = redis.StrictRedis.from_url(self.REDIS_URL,
                                                decode_responses=True)

        self.app = default_app()

        self.init_routes()

        self.client = docker.from_env()

    def sesh_id(self):
        return base64.b32encode(os.urandom(10)).decode('utf-8').lower()

    def c_hostname(self, container):
        return container.id[:12]

    def launch_group(self, url=None, image_name=None):
        id = self.sesh_id()
        id_key = self.GSESH.format(id)
        print('Group Id: ' + id)

        if image_name:
            image_name = self.USER_IMAGE.format(image_name)
            try:
                image = self.client.images.get(image_name)
                url = image.labels[self.START_URL_LABEL]

            except Exception as e:
                return {'error': str(e)}

        else:
            if not url:
                return {'error': 'url_missing'}

            image_name = self.SCALAR_BASE_IMAGE

        self.redis.hset(id_key, 'start_url', url)

        volumes = {self.VOL_PREFIX + id: {'bind': '/data', 'mode': 'rw'}}

        scalar = self.client.containers.run(image_name,
                                            detach=True,
                                            network=self.NETWORK_NAME,
                                            auto_remove=True,
                                            volumes=volumes)

        self.redis.hset(id_key, 'scalar_id', scalar.id)

        parts = urlsplit(url)

        local_scalar_host = self.c_hostname(scalar)
        local_url = 'http://' + local_scalar_host + os.path.dirname(parts.path)

        filter_url = parts.scheme + '://' + parts.netloc

        pywb_env = {'SCALAR_HOST': 'http://' + self.c_hostname(scalar),
                    'PYWB_FILTER_PREFIX': filter_url}

        pywb = self.client.containers.run(self.PYWB_IMAGE,
                                          detach=True,
                                          auto_remove=True,
                                          network=self.NETWORK_NAME,
                                          environment=pywb_env,
                                          volumes=volumes)

        self.redis.hset(id_key, 'pywb_id', self.c_hostname(pywb))

        self.wait_for_load(self.c_hostname(pywb), 8080)

        return {'id': id,
                'scalar_host': local_scalar_host,
                'local_url': local_url,
                'url': url,
                'scalar': scalar,
                'pywb': pywb,
               }

    def wait_for_load(self, hostname, port):
        while True:
            try:
                res = requests.get('http://{0}:{1}/'.format(hostname, port))
                break
            except Exception as e:
                print(e)
                print('Waiting for pywb init')
                time.sleep(1)

    def list_images(self):
        try:
            images = self.client.images.list(name=self.USER_IMAGE_PREFIX)
        except Exception as e:
            return {'error': str(e)}

        image_names = [image.tags[0].rsplit(':', 1)[1] for image in images]

        return {'images': image_names}

    def delete_group(self, id):
        id_key = self.GSESH.format(id)

        sesh_data = self.redis.hgetall(id_key)

        try:
            print('Removing scalar')
            self.client.containers.get(sesh_data['scalar_id']).remove(v=True, force=True)
        except Exception as e:
            print(e)

        try:
            print('Removing pywb')
            self.client.containers.get(sesh_data['pywb_id']).remove(v=True, force=True)
        except Exception as e:
            print(e)

        try:
            print('Removing volume')
            volume = self.client.volumes.get(self.VOL_PREFIX + id)
            volume.remove(force=True)
        except Exception as e:
            print(e)

    def commit_image(self, id, image_name):
        id_key = self.GSESH.format(id)

        scalar_id = self.redis.hget(id_key, 'scalar_id')
        if not scalar_id:
            return {'error': 'id_not_found'}

        url = self.redis.hget(id_key, 'start_url') or 'about:blank'

        conf = {'Labels': {self.START_URL_LABEL: url}}

        try:
            scalar = self.client.containers.get(scalar_id)
            res = scalar.exec_run(['/tmp/commit.sh'])

            scalar.commit(self.USER_IMAGE.format(image_name), conf=conf)
            return {'new_id': image_name}

        except Exception as e:
            return {'error': str(e)}

    def new_scalar_archive(self, url, ws):
        self.send_ws(ws, {'msg': 'Check Scalar Url...'})
        book = ScalarBook(url)
        cmd = book.load_book_init_cmd()
        if not cmd:
            self.send_ws(ws, {'msg': 'Not a valid Scalar Url', 'error': 'not_valid'})
            return

        url = book.base_url

        cinfo = self.launch_group(url=url)
        if 'error' in cinfo:
            cinfo['msg'] = 'Error Launching'
            self.send_ws(ws, cinfo)
            return

        self.send_ws(ws, {'msg': 'Starting Import...', 'launch_id': cinfo['id']})
        import_reqid = self.start_import(cinfo, book, cmd, url)

        self.send_ws(ws, {'import_reqid': import_reqid})

        self.send_ws(ws, {'msg': 'Starting Auto Browsers...'})
        auto_res = self.start_media_auto(cinfo, book, url, self.NUM_BROWSERS)

        self.send_ws(ws, {'auto_reqids': auto_res['auto_reqids']})

        while True:
            remaining = self.redis.llen(auto_res['browser_q'])
            self.send_ws(ws, {'msg': 'Crawling Media: {0} urls left'.format(remaining)})
            if remaining == 0 and book.new_url != None:
                break

            time.sleep(5)

        image_name = url.rsplit('/', 1)[-1]
        self.send_ws(ws, {'msg': 'Committing to Image {0}...'.format(image_name)})

        self.commit_image(cinfo['id'], image_name)

        self.send_ws(ws, {'msg': 'Deleting Launch Group'})

        self.delete_group(cinfo['id'])

        self.send_ws(ws, {'msg': 'Done! Image Committed: {0}'.format(image_name)})


    def send_ws(self, ws, data):
        ws.send(json.dumps(data))

    def load_existing_archive(self, image_name):
        cinfo = self.launch_group(image_name=image_name)
        if 'error' in cinfo:
            return cinfo

        browser = self.start_browser(cinfo, prefix='/combined/bn_/',
                                     url=cinfo['url'])

        return {'id': cinfo['id'],
                'reqid': browser.reqid
               }

    def start_import(self, cinfo, book, cmd, url):
        self.init_scalar(cinfo['scalar'], book, cmd)

        tab_opts = {'base_url': url,
                    'book': book,
                    'scalar_host': cinfo['scalar_host']
                   }

        browser = self.start_browser(cinfo, browser_q='import_q:',
                                            tab_class=ImportTabDriver,
                                            tab_opts=tab_opts)

        print('LOCAL URL', cinfo['local_url'])
        browser.queue_urls([cinfo['local_url']])

        return browser.reqid

    def start_media_auto(self, cinfo, book, url, count):
        book.load_media()

        ids = []
        first = True

        for i in range(count):
            autob = self.start_browser(cinfo, browser_q='auto_q:',
                                           prefix='/store/record/bn_/')
            if first:
                autob.queue_urls([url])
                autob.queue_urls(book.urls)
                first = False

            ids.append(autob.reqid)

        return {'auto_reqids': ids,
                'browser_q': 'auto_q:' + cinfo['id']}

    def init_scalar(self, scalar, book, init_cmd):
        try:
            #time.sleep(10)
            exit_code, output = scalar.exec_run(init_cmd)
            #print('OUTPUT', output.decode('utf-8'))
            return exit_code == 0
        except Exception as e:
            print(e)
            return False

    def start_browser(self, cinfo, browser_q='replay_q:',
                      url=None, prefix=None, tab_class=AutoTab, tab_opts=None):
        browser_q += cinfo['id']

        cdata = {}

        if prefix:
            cdata['pywb_prefix'] = prefix
            cdata['proxy_host'] = self.c_hostname(cinfo['pywb'])

        if url:
            cdata['url'] = url

        browser = AutoBrowser(redis=self.redis,
                              browser_image='chrome:60',
                              browser_q=browser_q,
                              cdata=cdata,
                              tab_class=tab_class,
                              tab_opts=tab_opts)

        return browser

    def init_routes(self):
        @self.app.get('/')
        @jinja2_view('index.html')
        def index():
            return {}

        @self.app.get('/launch')
        @jinja2_view('launch.html')
        def launch():
            res = self.list_images()
            return {'images': res.get('images', [])}

        @self.app.get('/archive/list/images')
        def list_images():
            return self.list_images()

        @self.app.get('/archive/delete/<id>')
        def delete_group(id):
            self.delete_group(id)

        @self.app.get('/archive/new/<url:path>')
        def start_new_scalar(url):
            ws = request.environ['wsgi.websocket']
            self.new_scalar_archive(url, ws)
            ws.close()

        @self.app.get('/archive/commit/<id>')
        def commit_image(id):
            return self.commit_image(id, request.query.get('name'))

        @self.app.get('/archive/launch/<image_name>')
        def launch_existing(image_name):
            return self.load_existing_archive(image_name)

        @self.app.get('/static/<filename>')
        def server_static(filename):
            return static_file(filename, root='./static/')


# ============================================================================
class ImportTabDriver(AutoTab):
    INIT = '1'
    LOGIN = '2'
    LOGGED_IN_REDIR = '3'
    LOGGED_IN = '4'
    IMPORTING = '5'
    DONE = '6'

    LOGIN_SCRIPT = """
document.querySelector("form input[name='email']").setAttribute("value", "scalar@example.com");
document.querySelector("form").submit();
"""

    IMPORT_SCRIPT = """
var url = "%s";
var doc = window.frames[0].document;
doc.querySelector("#urlform input.source_url").setAttribute("value", url);
doc.querySelector("#urlform button[type=submit]").click();

var waitLoad = setInterval(do_load, 500);

window.scrollBy(0, 1000);

function do_load() {
  var rdf = doc.querySelector("#source_rdf");
  var submit = doc.querySelector("#commit button[type=submit]");

  if (rdf && rdf.value && rdf.value.indexOf("Loading") == 0 || submit && submit.getAttribute("disabled")) {
    //console.log("Still Loading");
    return;
  }
  clearInterval(waitLoad);

  doc.querySelector("#commit button[type=submit]").click();

  waitLoad = setInterval(do_import, 500);
}

function do_import() {
  var submit = doc.querySelector("#commit button[type=submit]");

  if (submit && submit.getAttribute("disabled")) {
     return;
  }

  window.all_done = true;
  console.log("Done!");
  clearInterval(waitLoad);

  var start_url = new URL(url);
  start_url.hostname = window.location.hostname;
  window.location.href = start_url.href;
}



"""

    IMPORT_TAB_URL = '/system/dashboard?book_id=1&zone=transfer#tabs-transfer'

    def __init__(self, *args, **kwargs):
        self.stage = self.INIT
        self.base_url = kwargs.get('base_url')
        self.book = kwargs.get('book')
        self.scalar_host = kwargs.get('scalar_host')
        super(ImportTabDriver, self).__init__(*args, **kwargs)

    def navigate_to(self, url, stage):
        self.send_ws({"method": "Page.navigate", "params": {"url": url}})
        self.stage = stage

    def handle_done_loading(self):
        if self.stage == self.INIT:
            print('INIT')
            self.import_tab_url = self.curr_url + self.IMPORT_TAB_URL

            self.navigate_to(self.import_tab_url, self.LOGIN)

        elif self.stage == self.LOGIN:
            print('LOGIN')
            self.stage = self.LOGGED_IN_REDIR
            self.eval(self.LOGIN_SCRIPT)

        elif self.stage == self.LOGGED_IN_REDIR:
            print('LOGGED_IN_REDIR', self.import_tab_url)

            self.navigate_to(self.import_tab_url, self.LOGGED_IN)

        elif self.stage == self.LOGGED_IN:
            print('LOGGED_IN')

            self.stage = self.IMPORTING
            self.eval(self.IMPORT_SCRIPT % self.base_url)

        elif self.stage == self.IMPORTING:
            print('IMPORTING TOC')
            try:
                self.book.import_toc(target_host=self.scalar_host,
                                     username='scalar@example.com',
                                     password='')
            except:
                import traceback
                traceback.print_exc()

            self.stage = self.DONE

            #self.browser.queue_urls([book.new_url])
            self.eval('window.location.reload()')
            print('DONE IMPORTING')


# ============================================================================
if __name__ == "__main__":
    main = Main()
    WSGIServer('0.0.0.0:8375', main.app, handler_class=WebSocketHandler).serve_forever()


