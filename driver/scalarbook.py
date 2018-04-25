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

    def do_login(self):
        try:
            if not self.email or not self.password:
                return False

            res = self.sesh.get(self.base_url)
            if not res.history or 'login' not in res.url:
                return False

            post_url = res.url.split('?')[0]
            data = {'action': 'do_login',
                    'redirect_url': self.base_url,
                    'msg': 1,
                    'email': self.email,
                    'password': self.password
                   }

            res = self.sesh.post(post_url, data=data, allow_redirects=False)
            if res.headers['Location'] == self.base_url:
                return True

        except:
            import traceback
            traceback.print_exc()

    def test_book_url(self, url):
        try:
            res = self.sesh.get(url + '/rdf', params={'format': 'json'})

            data = res.json()

            assert data[url]

            return data
        except Exception as e:
            return None

    def load_book_init_cmd(self):
        url = self.base_url

        if url.endswith('/index'):
            url = url.rsplit('/', 1)[0]

        data = self.test_book_url(url)
        if not data:
            url = url.rsplit('/', 1)[0]
            data = self.test_book_url(url)
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

                    if value.startswith(self.internal_url):
                        load_url = value
                    else:
                        load_url = n

                    self.urls.append(load_url)

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
    print(' '.join(book.load_book_init_cmd()))

#scalar_export = load3()

#scalar_export.do_login()
#params = scalar_export.load_book_info()

#print('docker exec -it scalar_scalar_1 /tmp/import.sh ' + params)



#scalar_import = ScalarBook('http://localhost:8091/',
#                           email='scalar@example.com',
#                           password='test')

#scalar_import.do_register(scalar_export.name)
#scalar_import.do_create_book(scalar_export)





