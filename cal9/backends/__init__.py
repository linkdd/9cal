from cal9 import config
from cal9.util import DEBUG

def load():
    backend_type = config.config.backend
    DEBUG("Loading backend '{0}'".format(backend_type))

    module = __import__('cal9.backends', fromlist=[backend_type])
    return getattr(module, backend_type)
