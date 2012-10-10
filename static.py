import sys
import os
import time
import yaml
import shutil
from dae.commands.plugin import PluginCommand
from argparse import ArgumentParser
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


class cmd_static(PluginCommand):
    app_root = ""

    def run(self):
        parser = ArgumentParser()
        populate_argument_parser(parser)

        argv = sys.argv[2:] or ['--help']
        args, _ = parser.parse_known_args(argv)

        getattr(self, args.cmd[0])()

    def remove(self, tdir):
        print "Delete temp dir if exists", tdir
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

    def git_resp_hdler(self, status, raiseif, repo_tmp=None):
        if status[1] != "":
            if raiseif:
                print status[1].strip()
                raise sys.exit("Git error please handle it then Continue")
            else:
                print "Static tmp folder {repo_tmp} will remove for update, do you want to continue (y/n)? ".format(repo_tmp=repo_tmp),
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
                        raise sys.exit("Git error please goto {repo_tmp} to deal with this".format(repo_tmp=repo_tmp))

    def clone_into(self, url):
        tdir = self.temp_dir(url)

        status = Popen(['git', 'clone', url, tdir],
                       stdout=PIPE, stderr=PIPE).communicate()
        self.git_resp_hdler(status, True)

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
        if self.git_resp_hdler(status, False, repo_tmp):
            raise Exception('')

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

    def ck_modified(self, v, repo_tmp, *dirs):
        js_dir, css_dir, pic_dir = dirs

        mdfied_files = set()
        if "file" in v:
            for k1, v1 in v["file"].items():
                sdir = repo_tmp + k1
                tdir = self.app_root + v1
                mdfiedif = self.modified(sdir, tdir)
                if mdfiedif:
                    mdfied_files.add(mdfiedif)
        else:
            for root, dirs, files in os.walk(repo_tmp):
                for f in files:
                    sdir = os.path.join(root, f)

                    mdfiedif = None
                    if f.endswith(".js"):
                        mdfiedif = self.modified(sdir, js_dir)

                    if f.endswith(".css"):
                        mdfiedif = self.modified(sdir, css_dir)

                    pic_suffixs = [".jpg", ".jpeg", ".bmp", ".png"]
                    for suffix in pic_suffixs:
                        if f.endswith(suffix):
                            mdfiedif = self.modified(sdir, pic_dir)
                            break

                    if mdfiedif:
                        mdfied_files.add(mdfiedif)

        return mdfied_files

    def cover_file(self, sdir, tdir, mdfied):
        tfile = os.path.join(tdir, os.path.split(sdir)[-1])
        if os.path.exists(tfile):
            if self.modified(sdir, tdir):
                if tfile in mdfied:
                    print "{tfile} have been modified in local, do you want to cover(y/n/i[gnore])? ".format(tfile=tfile),
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
                    print "{tfile} in local not modified, auto Update it to new version".format(tfile=tfile)
                    return True
        return True

    def cp_to_dir(self, sdir, tdir, mdfied):
        #prepare dir
        try:
            os.makedirs(tdir)
        except OSError:
            pass

        if self.cover_file(sdir, tdir, mdfied):
            shutil.copy(sdir, tdir)
            print "Copy", sdir, "\n  to:", tdir

    def cpfiles(self, sdir, mdfied, *dirs):
        js_dir, css_dir, pic_dir = dirs

        for root, dirs, files in os.walk(sdir):
            for f in files:
                source_dir = os.path.join(root, f)

                if f.endswith(".js"):
                    self.cp_to_dir(source_dir, js_dir, mdfied)

                if f.endswith(".css"):
                    self.cp_to_dir(source_dir, css_dir, mdfied)

                pic_suffixs = [".jpg", ".jpeg", ".bmp", ".png"]
                for suffix in pic_suffixs:
                    if f.endswith(suffix):
                        self.cp_to_dir(source_dir, pic_dir, mdfied)

    def pull(self):
        self.set_approot()
        conf = self.static_conf()
        js_dir = conf["js_dir"]
        css_dir = conf["css_dir"]
        pic_dir = conf["pic_dir"]

        for k, v in conf["repos"].items():
            print "\n", "** " * 10

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

            tjs_dir = self.app_root + tjs_dir
            tcss_dir = self.app_root + tcss_dir
            tpic_dir = self.app_root + tpic_dir
            repo_tmp = self.temp_dir(url)

            print "Update repo", url
            local_mdfied = set()
            if os.path.exists(repo_tmp):
                local_mdfied = self.ck_modified(v, repo_tmp, tjs_dir, tcss_dir, tpic_dir)

                if self.remote_origin(repo_tmp) != url:
                    self.remove(repo_tmp)
                    self.clone_into(url)
                else:
                    try:
                        self.pulldown(repo_tmp)
                    except Exception:
                        self.remove(repo_tmp)
                        self.clone_into(url)
            else:
                self.clone_into(url)
                ignore_file = os.path.join(self.app_root, '.gitignore')
                ignores = open(ignore_file, 'U').readlines()
                if not '.statictmp\n' in ignores:
                    ignores.append('.statictmp\n')
                    open(ignore_file, 'wb').write(''.join(ignores))

            print "Update success"
            if v_or_t is not None:
                self.reset(repo_tmp, v_or_t)

            if "file" in v:
                for k1, v1 in v["file"].items():
                    sdir = repo_tmp + k1
                    tdir = self.app_root + v1
                    self.cp_to_dir(sdir, tdir, local_mdfied)
            else:
                self.cpfiles(repo_tmp, local_mdfied, tjs_dir, tcss_dir, tpic_dir)

    def push(self):
        print "haha, wo shi @clj"


if __name__ == '__main__':
    import setuptools
    setuptools.setup(
        name='cmdstatic',
        py_modules=['static'],
        entry_points="""
        [dae.plugins]
        static=static:cmd_static
        """
    )
