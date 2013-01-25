import os
import simplejson as json


defaultHostDict = {
    'github': 'git://github.com/%s.git',
    'bitbucket': 'git://bitbucket.org/%s.git',
    'local': '%s',
}


def get_app_root():
    cwd = os.getcwd()

    while cwd != '/':
        if 'static.json' in os.listdir(cwd):
            return cwd
        cwd = os.path.dirname(cwd)
    else:
        raise NotFoundAppRoot()


def get_static_conf(app_root):
    conf = json.load(file(os.path.join(app_root, 'static.json'), 'r'))
    return conf


def gen_repo_conf(global_conf, conf_json, repo_name):
    repo_conf = {}
    # 继承缺省静态文件路径
    for k in ('js_dir', 'css_dir', 'pic_dir'):
        repo_conf[k] = conf_json.get(k, global_conf.get(k))
        if repo_conf[k]:
            repo_conf[k] = os.path.join(global_conf['app_root'], repo_conf[k].lstrip('/'))

    repo_conf['host'] = global_conf['host_dict'][conf_json['host']] if 'host' in conf_json else global_conf['host_dict']['github']
    repo_conf['host'] = repo_conf['host'] % repo_name
    return repo_conf


class NotFoundAppRoot(IOError):
    pass
