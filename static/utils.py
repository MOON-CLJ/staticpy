#!/usr/bin/env python
# -*- coding: utf-8 -*-

from subprocess import Popen, PIPE
from clint.utils import tsplit
from clint.textui import puts, indent, colored
import subprocess
import os
import sys
import errno
import simplejson as json
import time
import difflib
import shlex
import shutil
import termios
import tty


defaultHostDict = {
    'github': 'git://github.com/%s.git',
    'bitbucket': 'git://bitbucket.org/%s.git',
    'local': '%s',
}

allowedFileTypes = [
    'html', 'jade', 'js', 'coffee',
    'css', 'styl', 'sass', 'scss',
    'png', 'jpg', 'jpeg', 'gif',
]


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
    repo_conf['host'] = global_conf['host_dict'][conf_json['host']] if 'host' in conf_json else global_conf['host_dict']['github']
    repo_conf['host'] = repo_conf['host'] % repo_name
    repo_conf['commit'] = conf_json.get('commit') or conf_json.get('tag')
    repo_conf['commit'] = str(repo_conf['commit'])
    repo_conf['build'] = conf_json.get('build')
    repo_conf['tmpdir'] = os.path.join(global_conf['app_root'], '.staticpytmp/%s' % repo_name)
    repo_conf['file'] = conf_json.get('file')
    if repo_conf.get('file'):
        for k, v in repo_conf['file'].items():  # 这里采用items而非iteritems
            kk, vv = k.strip(), v.strip()
            if kk.startswith('/'):
                kk = kk[1:]
            if vv.startswith('/'):
                vv = vv[1:]
            kk = os.path.join(repo_conf['tmpdir'], kk)
            vv = os.path.join(global_conf['app_root'], vv)

            del repo_conf['file'][k]
            repo_conf['file'][kk] = vv

    return repo_conf


def get_remote_url(repo_dir):
    """假定只有一个remote url,返回它"""
    cwd = os.getcwd()
    os.chdir(repo_dir)
    r = Popen(['git', 'remote', '-v'], stdout=PIPE).communicate()[0]
    os.chdir(cwd)
    remote_url = tsplit(r, ['\n', '\t', ' '])[1]

    return remote_url


def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def is_file_modified(source_file, target_file):
    """返回两个文件是否有diff, 若target_file不存在,返回None, 没有diff返回[]"""
    if not os.path.exists(target_file):
        return None

    fromlines = open(source_file, 'U').readlines()
    tolines = open(target_file, 'U').readlines()
    fromdate = time.ctime(os.stat(source_file).st_mtime)
    todate = time.ctime(os.stat(target_file).st_mtime)

    return list(difflib.context_diff(fromlines, tolines, source_file, target_file, fromdate, todate))


def dir_dir_modified(source_dir, target_dir):
    """返回source_dir里对应target_dir有修改的文件路径集合"""
    modified_files = set()
    for root, dirs, files in os.walk(source_dir):
        for f in files:
            source_file = os.path.join(root, f)
            modified_files |= file_dir_modified(source_file, target_dir)

    return modified_files


def file_dir_modified(source_file, target_dir):
    """返回source_file在target_dir对应文件有修改的文件路径集合"""
    target_file = os.path.join(target_dir, os.path.split(source_file)[-1])
    return file_file_modified(source_file, target_file)


def file_file_modified(source_file, target_file):
    """返回source_file与target_file对应文件有修改的文件路径集合"""
    return set([source_file]) if is_file_modified(source_file, target_file) else set()


def cp_dir2dir(source_dir, target_dir, should_be_notice_files):
    for root, dirs, files in os.walk(source_dir):
        for f in files:
            source_file = os.path.join(root, f)
            cp_file2dir(source_file, target_dir, should_be_notice_files)


def cp_file2dir(source_file, target_dir, should_be_notice_files):
    target_file = os.path.join(target_dir, os.path.split(source_file)[-1])
    cp_file2file(source_file, target_file, should_be_notice_files)


def cp_file2file(source_file, target_file, should_be_notice_files):
    if source_file.rsplit('.', 1)[1] not in allowedFileTypes:
        return
    if is_file_modified(source_file, target_file):
        if source_file in should_be_notice_files:
            if notice_if_cover_file(source_file, target_file):
                shutil.copy(source_file, target_file)
                with indent(6, quote=colored.clean('#')):
                    puts(colored.cyan('Update %s ->  %s' % (cleaner_path(source_file), cleaner_path(target_file))))
        else:
            shutil.copy(source_file, target_file)
            with indent(6, quote=colored.clean('#')):
                puts(colored.cyan('Auto update %s ->  %s' % (cleaner_path(source_file), cleaner_path(target_file))))
    elif is_file_modified(source_file, target_file) is None:
        shutil.copy(source_file, target_file)
        with indent(6, quote=colored.clean('#')):
            puts(colored.cyan('Copy %s ->  %s' % (cleaner_path(source_file), cleaner_path(target_file))))


def cleaner_path(target_path):
    cwd = os.getcwd()
    return os.path.relpath(target_path, cwd)


def notice_if_cover_file(source_file, target_file):
    print '%s have been modified in local, do you want to cover(y/n/i[gnore])? ' % target_file,
    ans = getch()
    print
    while 1:
        if ans == '\x03':
            raise sys.exit('Terminated')

        ans = ans.strip().lower()
        if ans == 'y':
            return True
        elif ans == 'n':
            raise sys.exit('You can continue when you finish editing this file %s' % target_file)
        elif ans == 'i':
            return False
        else:
            print 'Cannot figure out your input, shoule be (y/n/i[gnore]): ',
            ans = getch()
            print


def clone(remote_url, tmp_repo_dir):
    args = ['git', 'clone', remote_url, tmp_repo_dir]
    subprocess.check_output(args)


def fetch(tmp_repo_dir):
    args = ['git', 'fetch', tmp_repo_dir]
    subprocess.check_output(args)


def checkout(tmp_repo_dir, commit):
    cwd = os.getcwd()
    os.chdir(tmp_repo_dir)
    args = ['git', 'checkout', commit, '-qf']
    try:
        subprocess.check_output(args)
    except subprocess.CalledProcessError:
        raise NotMatchCommit()
    os.chdir(cwd)


def build(tmp_repo_dir, cmd):
    cwd = os.getcwd()
    os.chdir(tmp_repo_dir)
    args = shlex.split(cmd)
    subprocess.check_output(args)
    os.chdir(cwd)


def add_tmpdir2gitignore(app_root):
    gitignore_path = os.path.join(app_root, '.gitignore')
    try:
        ignores = open(gitignore_path, 'U').readlines()
        if not '.staticpytmp\n' in ignores:
            ignores.append('.staticpytmp\n')
            open(gitignore_path, 'w').write(''.join(ignores))
    except IOError, e:
        if e.errno == errno.ENOENT:
            pass


class NotFoundAppRoot(IOError):
    pass


class NotMatchCommit(Exception):
    pass
