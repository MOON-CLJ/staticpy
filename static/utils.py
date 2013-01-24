import os


def get_app_root():
    cwd = os.getcwd()

    while cwd != '/':
        if 'static.json' in os.listdir(cwd):
            return cwd
        cwd = os.path.dirname(cwd)
    else:
        raise NotFoundAppRoot()


class NotFoundAppRoot(IOError):
    pass
