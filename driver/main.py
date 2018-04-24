import gevent.monkey; gevent.monkey.patch_all()
from gevent.pywsgi import WSGIServer

import logging
import redis
import docker
import base64
import time
import os

from urllib.parse import urlsplit

from bottle import debug, default_app, request, view, TEMPLATE_PATH, static_file
from scalarbook import ScalarBook
from autobrowser import AutoBrowser, AutoTab


# ============================================================================
class Main(object):
    GSESH = 'ssesh:{0}'
    BQ = 'url_q:{0}'

    def __init__(self):
        debug(True)
        TEMPLATE_PATH.insert(0, './templates')
        logging.basicConfig(format='%(asctime)s: [%(levelname)s]: %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            level=logging.WARN)

        self.redis = redis.StrictRedis.from_url('redis://redis/2',
                                                decode_responses=True)

        self.app = default_app()

        self.init_routes()

        self.client = docker.from_env()

    def sesh_id(self):
        return base64.b32encode(os.urandom(10)).decode('utf-8').lower()

    def c_hostname(self, container):
        return container.id[:12]

    def launch_group(self):
        id = self.sesh_id()
        id_key = self.GSESH.format(id)

        print('New Group Id: ' + id)

        scalar = self.client.containers.run('dynpreserve/scalar',
                                             detach=True,
                                             network='scalar_default',
                                             auto_remove=True)

        self.redis.hset(id_key, 'scalar_id', scalar.id)

        pywb = self.client.containers.run('dynpreserve/pywb',
                                           detach=True,
                                           auto_remove=True,
                                           network='scalar_default',
                                           environment={'SCALAR_HOST': self.c_hostname(scalar)})
                                           #volumes_from=scalar.short_id)

        self.redis.hset(id_key, 'pywb_id', self.c_hostname(pywb))

        return {'id': id,
                'scalar': scalar,
                'pywb': pywb
               }

    def delete_group(self, id):
        id_key = self.GSESH.format(id=id)

        sesh_data = self.redis.hgetall(id_key)

        try:
            print('Removing scalar')
            self.cli.containers.get(sesh_data['scalar_id']).remove(v=True, force=True)
        except:
            pass

        try:
            print('Removing pywb')
            self.cli.containers.get(sesh_data['pywb_id']).remove(v=True, force=True)
        except:
            pass

    def new_scalar_archive(self, url):
        book = ScalarBook(url)
        cmd = book.load_book_init_cmd()
        if not cmd:
            return {'error': 'not_valid_url'}

        cinfo = self.launch_group()

        import_reqid = None#self.start_import(cinfo, book, cmd, url)

        auto_reqids = self.start_media_auto(cinfo, book, url)

        return {'id': cinfo['id'],
                'reqid': import_reqid,
                'autos': auto_reqids
               }

    def start_import(self, cinfo, book, cmd, url):
        self.init_scalar(cinfo['scalar'], book, cmd)

        browser = self.start_browser(cinfo, url, 'import_q:', coll=None, tab_class=ImportTabDriver)
        browser.queue_urls([self.get_starting_url(url, cinfo)])

        return browser.reqid

    def start_media_auto(self, cinfo, book, url):
        book.load_media(100)

        auto_1 = self.start_browser(cinfo, url, 'auto_q:', coll='store/record')
        #auto_2 = self.start_browser(cinfo, url, 'auto_q:', coll='store/record')

        auto_1.queue_urls([url])
        auto_1.queue_urls(book.urls)

        return [auto_1.reqid]#, auto_2.reqid]

    def get_starting_url(self, url, cinfo):
        parts = urlsplit(url)
        return 'http://' + self.c_hostname(cinfo['scalar']) + os.path.dirname(parts.path)

    def init_scalar(self, scalar, book, init_cmd):
        try:
            #time.sleep(10)
            exit_code, output = scalar.exec_run(init_cmd)
            #print('OUTPUT', output.decode('utf-8'))
            return exit_code == 0
        except Exception as e:
            print(e)
            return False

    def start_browser(self, cinfo, url, browser_qt, coll=None, tab_class=AutoTab):
        browser_q = browser_qt + cinfo['id']

        cdata = {}

        if coll:
            cdata['coll'] = coll
            cdata['proxy_host'] = self.c_hostname(cinfo['pywb'])

        #if links:
        #    cdata['links'] = self.c_hostname(cinfo['scalar']) + ':scalar'

        browser = AutoBrowser(redis=self.redis,
                              browser_image='chrome:60',
                              browser_q=browser_q,
                              cdata=cdata,
                              tab_class=tab_class,
                              tab_opts={'base_url': url})

        return browser

    def init_routes(self):
        @self.app.get('/')
        @view('index.html')
        def index():
            return {}

        @self.app.get('/archive/delete/<id>')
        def start_scalar(id):
            self.delete_group(id)

        @self.app.get('/archive/new/<url:path>')
        def start_scalar(url):
            return self.new_scalar_archive(url)

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

  window.location.pathname = new URL(url).pathname;
}

"""

    IMPORT_TAB_URL = '/system/dashboard?book_id=1&zone=transfer#tabs-transfer'

    def __init__(self, *args, **kwargs):
        self.stage = self.INIT
        self.base_url = kwargs.get('base_url')
        super(ImportTabDriver, self).__init__(*args, **kwargs)

    def navigate_to(self, url, stage):
        self.send_ws({"method": "Page.navigate", "params": {"url": url}})
        self.stage = stage

    def handle_done_loading(self):
        if self.stage == self.INIT:
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
            print('DONE IMPORTING')


# ============================================================================
if __name__ == "__main__":
    main = Main()
    WSGIServer('0.0.0.0:8375', main.app).serve_forever()


