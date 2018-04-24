from gevent.monkey import patch_all; patch_all()
from dynproxyapp import DynProxyPywb

application = DynProxyPywb()

