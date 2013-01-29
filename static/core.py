#!/usr/bin/env python
# -*- coding: utf-8 -*-


from clint import args
from clint.textui import puts, indent, colored
from .utils import get_app_root, get_static_conf, gen_repo_conf, \
    dir_dir_modified, file_dir_modified, file_file_modified, \
    get_remote_url, clone, fetch, add_tmpdir2gitignore, \
    NotFoundAppRoot, defaultHostDict
import simplejson as json
import shutil
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

        # 记录tmp仓库更新前,本地相对于仓库有修改的文件
        local_mdfied = set()
        if os.path.exists(repo_conf['tmpdir']) and 'file' in repo_conf:
            for source, target in repo_conf['file'].iteritems():
                if os.path.isdir(source):
                    if os.path.isdir(target):
                        local_mdfied |= dir_dir_modified(source, target)
                elif os.path.isfile(source):
                    if os.path.isdir(target):
                        local_mdfied |= file_dir_modified(source, target)
                    elif os.path.isfile(target):
                        local_mdfied |= file_file_modified(source, target)

        # 更新tmp仓库，注意如果某个repo的host变了而repo名没变，检查remote url
        # 首先将.staticpytmp 添加到.gitignore
        add_tmpdir2gitignore(global_conf['app_root'])
        if os.path.exists(repo_conf['tmpdir']):
            if repo_conf['host'] == get_remote_url(repo_conf['tmpdir']):
                fetch(repo_conf['tmpdir'])
            else:
                shutil.rmtree(repo_conf['tmpdir'])
                clone(repo_conf['host'], repo_conf['tmpdir'])
        else:
            clone(repo_conf['host'], repo_conf['tmpdir'])


def main():
    if args.not_files[0]:
        pull()

if __name__ == '__main__':
    main()
