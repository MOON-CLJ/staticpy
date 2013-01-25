#!/usr/bin/env python
# -*- coding: utf-8 -*-


from clint import args
from clint.textui import puts, indent, colored
from .utils import get_app_root, get_static_conf, gen_repo_conf, NotFoundAppRoot, defaultHostDict
import simplejson as json
import sys
import os


def pull():
    global_conf = {}

    # 依据static.json获取app root
    try:
        app_root = get_app_root()
        with indent(2, quote=colored.clean('#')):
            puts(colored.blue('App root at: %s' % app_root))
    except NotFoundAppRoot:
        with indent(2, quote=colored.clean('#')):
            puts(colored.red('Not a app dir (or any of the parent directories)'))
        sys.exit(1)
    global_conf['app_root'] = app_root

    # 读取static.json
    try:
        static_conf = get_static_conf(app_root)
        static_conf = static_conf['staticpy']
    except json.decoder.JSONDecodeError, e:
        with indent(8, quote=colored.clean('#')):
            puts(colored.red('JSONDecodeError in static.json: %s' % e))
        sys.exit(1)
    except KeyError:
        with indent(8, quote=colored.clean('#')):
            puts(colored.red('"staticpy" key not in static.json'))
        sys.exit(1)

    # 获取缺省值
    for k in ('js_dir', 'css_dir', 'pic_dir'):
        if static_conf.get(k):
            global_conf[k] = static_conf.get(k)
            del static_conf[k]

    global_conf['host_dict'] = defaultHostDict
    if 'hostDict' in static_conf:
        for k, v in static_conf['hostDict'].iteritems():
            global_conf['host_dict'].setdefault(k, v + '%s.git')
        del static_conf['hostDict']

    # 遍历repo
    for repo_name, conf_json in static_conf.iteritems():
        with indent(4, quote=colored.clean('#')):
            puts(colored.clean('** ' * 10))

        # 继承缺省静态文件路径
        repo_conf = gen_repo_conf(global_conf, conf_json, repo_name)
        print repo_conf


def main():
    if args.not_files[0]:
        pull()

if __name__ == '__main__':
    main()
