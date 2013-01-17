import sys
import os
import time
import yaml
import shutil
import shlex
from argparse import ArgumentParser
import subprocess
from subprocess import Popen, PIPE
import difflib
import termios
import tty


def populate_argument_parser(parser):
    parser.add_argument("cmd", nargs="+", choices=["pull", "push"],
                        help="pull or push static files")


def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


class cmd_static():
    app_root = ""

    def run(self):
        parser = ArgumentParser()
        populate_argument_parser(parser)

        argv = sys.argv[2:] or ['--help']
        args, _ = parser.parse_known_args(argv)

        getattr(self, args.cmd[0])()

    def remove(self, tdir):
        print "Delete temp dir if exists", "[root]" + tdir[len(self.app_root) + 1:]
        try:
            shutil.rmtree(tdir)
        except OSError:
            pass

    def set_approot(self):
        cwd = os.getcwd()
        print "cwd:", cwd

        while cwd != "/":
            if "app.yaml" in os.listdir(cwd):
                print "app root:", cwd

                self.app_root = cwd
                return
            cwd = os.path.dirname(cwd)
        else:
            raise sys.exit("cannot find app root, please make sure there is a app.yaml in the app root dir")

    def clean(self, s):
        return "[root]" + s[len(self.app_root) + 1:]

    def static_conf(self):
        try:
            conf = yaml.load(file(os.path.join(self.app_root, 'static.yaml'), 'r'))
            return conf
        except yaml.YAMLError, e:
            print "Error in configuration file:", e
            raise
        except IOError, e:
            raise sys.exit("no static.yaml in app root dir")

    def temp_dir(self, url):
        tdir = url.strip().split("/")[-1]

        # strip ".git"
        tdir = tdir[:-4]
        tdir = ".statictmp/" + tdir

        tdir = os.path.join(self.app_root, tdir)
        return tdir

    def resp_hdler(self, status, err_raise=True, repo_tmp=None, result_p=False):
        # if stderr not empty
        if status[1] != "":
            if err_raise:
                print "\033[31m", status[1].strip(), "\033[0m\n"
                raise sys.exit("Git error please handle it then Continue")
            else:
                print "Static tmp folder {repo_tmp} will remove for update, do you want to continue (y/n)? ".format(repo_tmp=self.clean(repo_tmp)),
                ans = getch()
                print
                while 1:
                    if ans == "\x03":
                        raise sys.exit("Terminated")

                    ans = ans.strip().lower()
                    if ans == "y":
                        print "Continue ..."
                        return True
                    elif ans == "n":
                        print status[1].strip()
                        raise sys.exit("Git error please goto {repo_tmp} to deal with this".format(repo_tmp=self.clean(repo_tmp)))

        if result_p:
            print status[0].strip()

    def tmp2ignores(self):
        ignore_file = os.path.join(self.app_root, '.gitignore')
        ignores = open(ignore_file, 'U').readlines()
        if not '.statictmp\n' in ignores:
            ignores.append('.statictmp\n')
            open(ignore_file, 'wb').write(''.join(ignores))

    def clone2tmp(self, url):
        tdir = self.temp_dir(url)

        args = ['git', 'clone', url, tdir]
        print subprocess.check_output(args)

    def reset(self, tdir, v_or_t):
        cwd = os.getcwd()
        os.chdir(tdir)
        Popen(['git', 'reset', '--hard', v_or_t],
              stdout=PIPE, stderr=PIPE).communicate()
        os.chdir(cwd)
        print "Switch to '{v_or_t}'".format(v_or_t=v_or_t)

    def pulldown(self, repo_tmp):
        cwd = os.getcwd()
        os.chdir(repo_tmp)
        status = Popen(['git', 'pull'], stdout=PIPE, stderr=PIPE).communicate()
        os.chdir(cwd)
        if self.resp_hdler(status, False, repo_tmp):
            raise Exception('')

    def cmd_run(self, repo_tmp, build_cmd):
        cwd = os.getcwd()
        os.chdir(repo_tmp)
        args = shlex.split(build_cmd)
        try:
            print subprocess.check_output(args)
        except subprocess.CalledProcessError:
            print "\033[31m may error when execute '{cmd}'\033[0m\n".format(cmd=build_cmd)

        os.chdir(cwd)

    def remote_origin(self, repo_tmp):
        cwd = os.getcwd()
        os.chdir(repo_tmp)
        status = Popen(['git', 'remote', '-v'], stdout=PIPE).communicate()[0]
        status = status.split('\n')[0]
        status = status.split('\t')[1]
        status = status.split()[0]
        os.chdir(cwd)

        return status

    def modified(self, sdir, tdir):
        tfile = os.path.join(tdir, os.path.split(sdir)[-1])
        if not os.path.exists(sdir) or not os.path.exists(tfile):
            return None

        fromlines = open(sdir, 'U').readlines()
        tolines = open(tfile, 'U').readlines()
        fromdate = time.ctime(os.stat(sdir).st_mtime)
        todate = time.ctime(os.stat(tfile).st_mtime)

        diff = difflib.context_diff(fromlines, tolines, sdir, tfile, fromdate, todate)
        for line in diff:
            return tfile
        return None

    def dir_modified(self, sdir, limitstatic=False, *dirs):
        if len(dirs) == 3:
            js_dir, css_dir, pic_dir = dirs
        else:
            tdir = dirs[0]

        mdfied_files = set()
        for root, dirs, files in os.walk(sdir):
            for f in files:
                source_dir = os.path.join(root, f)

                modified = None
                if limitstatic:
                    if f.endswith(".js"):
                        if js_dir is None:
                            raise sys.exit("static.yaml error: no js_dir in any level")
                        modified = self.modified(source_dir, js_dir)

                    if f.endswith(".css"):
                        if css_dir is None:
                            raise sys.exit("static.yaml error: no css_dir in any level")

                        modified = self.modified(source_dir, css_dir)

                    pic_suffixs = [".jpg", ".jpeg", ".bmp", ".png", "ico"]
                    for suffix in pic_suffixs:
                        if f.endswith(suffix):
                            if pic_dir is None:
                                raise sys.exit("static.yaml error: no pic_dir in any level")
                            modified = self.modified(source_dir, pic_dir)
                            break
                else:
                    # recurse
                    tdir_rcs = tdir + root[len(sdir):]
                    modified = self.modified(source_dir, tdir_rcs)

                if modified:
                    mdfied_files.add(modified)

        return mdfied_files

    def cover_file(self, sdir, tdir, mdfied):
        tfile = os.path.join(tdir, os.path.split(sdir)[-1])
        if os.path.exists(tfile):
            if self.modified(sdir, tdir):
                if tfile in mdfied:
                    print "{tfile} have been modified in local, do you want to cover(y/n/i[gnore])? ".format(tfile=self.clean(tfile)),
                    ans = getch()
                    print
                    while 1:
                        if ans == "\x03":
                            raise sys.exit("Terminated")

                        ans = ans.strip().lower()
                        if ans == "y":
                            print "Update to new one"
                            return True
                        elif ans == "n":
                            raise sys.exit("You can continue when you finish editing this file")
                        elif ans == "i":
                            print "Keep old one"
                            return False
                        else:
                            print "cannot figure out your input, shoule be (y/n/i[gnore]): ",
                            ans = getch()
                            print
                else:
                    print "{tfile} in local not modified, auto Update it to new version".format(tfile=self.clean(tfile))
                    return True
        return True

    def cp2dir(self, sdir, tdir, mdfied):
        #prepare dir
        try:
            os.makedirs(tdir)
        except OSError:
            pass

        if self.cover_file(sdir, tdir, mdfied):
            shutil.copy(sdir, tdir)
            print "Copy", self.clean(sdir), "\n ->", self.clean(tdir)

    def cpdir2dir(self, sdir, mdfied, limitstatic=False, *dirs):
        if len(dirs) == 3:
            js_dir, css_dir, pic_dir = dirs
        else:
            tdir = dirs[0]

        for root, dirs, files in os.walk(sdir):
            for f in files:
                source_dir = os.path.join(root, f)

                if limitstatic:
                    if f.endswith(".js"):
                        if js_dir is None:
                            raise sys.exit("static.yaml error: no js_dir in any level")
                        self.cp2dir(source_dir, js_dir, mdfied)

                    if f.endswith(".css"):
                        if css_dir is None:
                            raise sys.exit("static.yaml error: no css_dir in any level")
                        self.cp2dir(source_dir, css_dir, mdfied)

                    pic_suffixs = [".jpg", ".jpeg", ".bmp", ".png", "ico"]
                    for suffix in pic_suffixs:
                        if f.endswith(suffix):
                            if pic_dir is None:
                                raise sys.exit("static.yaml error: no pic_dir in any level")
                            self.cp2dir(source_dir, pic_dir, mdfied)
                else:
                    # recurse
                    tdir_rcs = tdir + root[len(sdir):]
                    self.cp2dir(source_dir, tdir_rcs, mdfied)

    def pull(self):
        self.set_approot()
        conf = self.static_conf()
        js_dir, css_dir, pic_dir = [None] * 3
        if "js_dir" in conf:
            js_dir = conf["js_dir"]
        if "css_dir" in conf:
            css_dir = conf["css_dir"]
        if "pic_dir" in conf:
            pic_dir = conf["pic_dir"]

        for k, v in conf["repos"].items():
            print "\n", "\033[34m", "** " * 10, "\033[0m\n"

            tjs_dir, tcss_dir, tpic_dir = js_dir, css_dir, pic_dir
            if "url" in v:
                url = v["url"]
            else:
                url = "http://code.dapps.douban.com/{name}.git".format(name=k)
            print "found repo", url

            v_or_t = None
            if type(v) == str:
                v_or_t = v
            else:
                if "version" in v:
                    v_or_t = v["version"]
                if "tag" in v:
                    v_or_t = v["tag"]
                if "js_dir" in v:
                    tjs_dir = v["js_dir"]
                if "css_dir" in v:
                    tcss_dir = v["css_dir"]
                if "pic_dir" in v:
                    tpic_dir = v["pic_dir"]

            build_cmds = []
            if "build_cmd" in v:
                build_cmds = v["build_cmd"]

            if tjs_dir:
                tjs_dir = self.app_root + tjs_dir
            if tcss_dir:
                tcss_dir = self.app_root + tcss_dir
            if tpic_dir:
                tpic_dir = self.app_root + tpic_dir
            repo_tmp = self.temp_dir(url)

            print "Update repo", url
            local_mdfied = set()
            if os.path.exists(repo_tmp):
                # check modify
                if "file" in v:
                    for k1, v1 in v["file"].items():
                        sdir = repo_tmp + k1
                        tdir = self.app_root + v1
                        if os.path.isfile(sdir):
                            modified = self.modified(sdir, tdir)
                            if modified:
                                local_mdfied.add(modified)
                        elif os.path.isdir(sdir):
                            modifieds = self.dir_modified(sdir, False, tdir)

                            local_mdfied = local_mdfied | modifieds
                else:
                    modifieds = self.dir_modified(repo_tmp, True, tjs_dir, tcss_dir, tpic_dir)
                    local_mdfied = local_mdfied | modifieds

                if self.remote_origin(repo_tmp) != url:
                    self.remove(repo_tmp)
                    self.clone2tmp(url)
                else:
                    try:
                        self.pulldown(repo_tmp)
                    except Exception:
                        self.remove(repo_tmp)
                        self.clone2tmp(url)
            else:
                self.clone2tmp(url)
                self.tmp2ignores()

            print "Update success"

            if v_or_t is not None:
                self.reset(repo_tmp, v_or_t)

            if build_cmds is not None:
                for cmd in build_cmds:
                    print "\nExecute:", cmd
                    self.cmd_run(repo_tmp, cmd)

            # ready to cp files
            if "file" in v:
                for k1, v1 in v["file"].items():
                    sdir = repo_tmp + k1
                    tdir = self.app_root + v1
                    if os.path.isfile(sdir):
                        self.cp2dir(sdir, tdir, local_mdfied)
                    elif os.path.isdir(sdir):
                        self.cpdir2dir(sdir, local_mdfied, False, tdir)

            else:
                self.cpdir2dir(repo_tmp, local_mdfied, True, tjs_dir, tcss_dir, tpic_dir)

    def push(self):
        print "haha, wo shi @clj"


def main():
    print 'hehe'

if __name__ == '__main__':
    main()
