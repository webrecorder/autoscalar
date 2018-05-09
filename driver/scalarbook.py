import requests
import os
import re
from urllib.parse import urlsplit


# ============================================================================
class ScalarBook(object):
    MEDIA_URL = '{0}/rdf/instancesof/media'

    BOOK_URL = '{0}/rdf'

    URL_PROP = 'http://simile.mit.edu/2003/10/ontologies/artstor#url'

    SOURCE_LOC = 'http://simile.mit.edu/2003/10/ontologies/artstor#sourceLocation'

    TITLE_FIELD = 'http://purl.org/dc/terms/title'

    NAME_FIELD = 'http://xmlns.com/foaf/0.1/name'

    DESC_FIELD = 'http://purl.org/dc/terms/description'

    REF_FIELD = 'http://purl.org/dc/terms/references'

    URN_FIELD = 'http://scalar.usc.edu/2012/01/scalar-ns#urn'

    VERSION_FIELD = 'http://scalar.usc.edu/2012/01/scalar-ns#version'

    EXT_TITLE = re.compile('([^<]+)[^:]+:\s*([^<]+)')

    def __init__(self, base_url, internal_url='',
                 name='', email=None, password=None):

        self.base_url = base_url
        self.email = email
        self.name = name
        self.title = ''
        self.desc = ''
        self.password = password

        self.sesh = requests.Session()

        self.urls = []
        self.internal_url = internal_url or self.base_url

        self.new_url = None

    def do_register(self, name=None):
        self.name = name or self.name
        register_url = self.base_url + 'system/register'

        data = {'action': 'do_register',
                'redirect_url': self.base_url,
                'email': self.email,
                'fullname': self.name,
                'password': self.password,
                'password_2': self.password,
                'tos': 1
               }

        res = self.sesh.post(register_url, data=data)

        return res.url == self.base_url

    def do_login(self, login_url, email='', password=''):
        email = email or self.email
        password = password or self.password

        try:
            #if not email or not password:
            #    return False

            #res = self.sesh.get(login_url)
            #if not res.history or 'login' not in res.url:
            #    return False

            #post_url = res.url.split('?')[0]
            data = {'action': 'do_login',
                    'redirect_url': '/',
                    'msg': 1,
                    'email': email,
                    'password': password
                   }

            res = self.sesh.post(login_url, data=data, allow_redirects=False)
            if res.headers['Location'] == '/':
                return True

        except:
            import traceback
            traceback.print_exc()

    def get_book_rdf_json(self, url, suffix='/rdf', assert_url=True):
        try:
            res = self.sesh.get(url + suffix, params={'format': 'json'})

            data = res.json()

            if assert_url:
                assert data[url]

            return data
        except Exception as e:
            print(e)
            return None

    def load_book_init_cmd(self):
        url = self.base_url

        if url.endswith('/index'):
            url = url.rsplit('/', 1)[0]

        data = self.get_book_rdf_json(url)
        if not data:
            url = url.rsplit('/', 1)[0]
            data = self.get_book_rdf_json(url)
            if not data:
                return []

        self.base_url = url

        base_info = data[self.base_url]

        try:
            for n, v in data.items():
                if self.NAME_FIELD in v:
                    self.name = v[self.NAME_FIELD][0]['value']
                    break

            self.title = base_info.get(self.TITLE_FIELD)[0]['value']
            self.desc = base_info.get(self.DESC_FIELD)[0]['value']
        except:
            pass

        # path
        parts = urlsplit(self.base_url)
        path = os.path.dirname(parts.path)
        slug = os.path.basename(parts.path)

        m = self.EXT_TITLE.match(self.title)
        if m:
            self.title = m.group(1)
            self.subtitle = m.group(2)
        else:
            self.subtitle = ''

        def quote_esc(val):
            return val.replace("'", "''")

        cmdlist = [self.name, path, slug, self.title, self.subtitle, self.desc]

        return ['/tmp/import.sh'] + [quote_esc(cmd) for cmd in cmdlist]

    def load_media(self, num_results=100):
        url = self.MEDIA_URL.format(self.base_url)

        start = 0

        params = {'format': 'json',
                  'start': start,
                  'results': num_results}

        while True:
            params['start'] = start
            print('Loading: {0} to {1}'.format(start, start + num_results))
            res = self.sesh.get(url, params=params)
            data = res.json()
            if not data:
                break

            self.parse_media(data)
            start += num_results

        print('Done')
        print('')
        print('\n'.join(self.urls))
        print('NUM: ' + str(len(self.urls)))

    def parse_media(self, data):
        for n, v in data.items():
            urls = v.get(self.SOURCE_LOC)
            if not urls:
                urls = v.get(self.URL_PROP, [])

            for prop_data in urls:
                if prop_data.get('type') == 'uri':
                    value = prop_data.get('value')
                    if not value:
                        continue

                    #local_url = self.internal_url.rsplit('/', 1)[0]
                    #if value.startswith(local_url):
                    #    load_url = value
                    #else:
                    load_url = n

                    self.urls.append(load_url)

    def import_toc(self, target_host, username, password):
        toc_list = self.load_toc()

        if not toc_list:
            return

        parts = urlsplit(self.base_url)

        find_prefix = parts.scheme + '://' + parts.netloc
        replace_prefix = 'http://' + target_host

        new_url = self.base_url.replace(find_prefix, replace_prefix)
        print(new_url)

        toc_list = [page.replace(find_prefix, replace_prefix) for page in toc_list]
        print(toc_list)

        id_list = self.get_toc_ids(new_url, toc_list)
        print('DATA', id_list)

        login_url = os.path.dirname(new_url) + '/system/login'
        dashboard_url = os.path.dirname(new_url) + '/system/dashboard'

        res = self.do_login(login_url, username, password)
        print('LOGIN', login_url, res)

        print(dashboard_url)

        res = self.sesh.post(dashboard_url, data=id_list)

        self.new_url = new_url

    def load_toc(self):
        data = self.get_book_rdf_json(self.base_url)

        toc = data.get(self.base_url + '/toc')

        toc = toc.get(self.REF_FIELD, [])

        toc_list = []

        for entry in toc:
            url = entry.get('value').split('#', 1)[0]
            toc_list.append(url)

        return toc_list

    def get_toc_ids(self, target_url, toc_list):
        data = self.get_book_rdf_json(target_url, suffix='/rdf/instancesof/page', assert_url=False)

        #id_list = 'action=do_save_style&book_id=1'
        id_list = [('action', 'do_save_style'), ('book_id', '1')]

        # Match ids
        for url in toc_list:
            try:
                version_url = data[url][self.VERSION_FIELD][0]['value']
                print('V', version_url)
                id = data[version_url][self.URN_FIELD][0]['value'].rsplit(':', 1)[-1]
                #id_list += '&book_version_{0}=1'.format(id)
                id_list.append(('book_version_' + id, '1'))
            except Exception as e:
                print(e)

        return id_list

def load1():
    return ScalarBook('http://blackquotidian.com/anvc/black-quotidian')

def load2():
    return ScalarBook('http://whenmelodiesgather.supdigital.org/wmg',
                  email='ilya.kreymer@rhizome.org',
                  password='melodiesarchivetest')


def load3():
    return ScalarBook('http://scalar.usc.edu/works/re-visualizing-care')

if __name__ == '__main__':
    import sys
    book = ScalarBook(sys.argv[1])
    book.load_toc()
    #print(' '.join(book.load_book_init_cmd()))

#scalar_export = load3()

#scalar_export.do_login()
#params = scalar_export.load_book_info()

#print('docker exec -it scalar_scalar_1 /tmp/import.sh ' + params)



#scalar_import = ScalarBook('http://localhost:8091/',
#                           email='scalar@example.com',
#                           password='test')

#scalar_import.do_register(scalar_export.name)
#scalar_import.do_create_book(scalar_export)





