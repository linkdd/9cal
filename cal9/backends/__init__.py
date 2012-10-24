from cal9 import config

def load():
    try:
        backend_type = config.config.backend
        module = __import__('cal9.backends', fromlist=[backend_type])
        return getattr(module, backend_type)
    except AttributeError:
        raise ImportError, "There is no backend '{0}'".format(backend_type)
