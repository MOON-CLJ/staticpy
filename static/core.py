#!/usr/bin/env python
# -*- coding: utf-8 -*-


from clint import args
from clint.textui import puts, indent, colored
from clint.utils import mkdir_p
from .utils import get_app_root, get_static_conf, gen_repo_conf, \
    dir_dir_modified, file_dir_modified, file_file_modified, \
    cp_file2file, cp_file2dir, cp_dir2dir, \
    get_remote_url, clone, fetch, checkout, build, add_tmpdir2gitignore, \
    NotFoundAppRoot, NotMatchCommit, defaultHostDict
import simplejson as json
import subprocess
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
            puts(colored.yellow('Processing %s' % repo_name))

        # 继承缺省静态文件路径
        repo_conf = gen_repo_conf(global_conf, conf_json, repo_name)

        # 记录tmp仓库更新前,本地相对于仓库有修改的文件
        local_mdfied = set()
        if os.path.exists(repo_conf['tmpdir']) and repo_conf.get('file'):
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

        # checkout到指定commit
        try:
            checkout(repo_conf['tmpdir'], repo_conf['commit'])
            with indent(4, quote=colored.clean('#')):
                puts(colored.green('Checkout to %s' % repo_conf['commit']))
        except NotMatchCommit:
            sys.exit(1)

        # 执行build命令
        if repo_conf.get('build'):
            for cmd in repo_conf['build']:
                try:
                    build(repo_conf['tmpdir'], cmd)
                    with indent(4, quote=colored.clean('#')):
                        puts(colored.green('Execute %s success' % cmd))
                except (OSError, subprocess.CalledProcessError):
                    with indent(4, quote=colored.clean('#')):
                        puts(colored.red('Execute %s fail in [%s]' % (cmd, repo_conf['tmpdir'])))
                    sys.exit(1)

        # 拷贝文件
        if repo_conf.get('file'):
            with indent(4, quote=colored.clean('#')):
                puts(colored.green('Copying files'))

            for source, target in repo_conf['file'].iteritems():
                # isdir, isfile的判断，若不存在，统一为False
                # 所以若需要先创建target所需的folder
                # 即source的folder最后的'/'可省略，但target的folder最后的'/'不能省略
                # 否则被视为文件，而创建folder失败, 导致拷贝失败
                if not os.path.exists(target) and '/' in target:
                    mkdir_p(target[:target.rfind('/')])

                if os.path.isdir(source):
                    if os.path.isdir(target):
                        cp_dir2dir(source, target, local_mdfied)
                elif os.path.isfile(source):
                    if os.path.isdir(target):
                        cp_file2dir(source, target, local_mdfied)
                    else:
                        # 此处不能用isfile判断，因为文件有可能不存在
                        cp_file2file(source, target, local_mdfied)


def main():
    if args.not_files[0]:
        pull()

if __name__ == '__main__':
    main()
