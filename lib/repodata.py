
import os
import time

from sh import awk
from sh import grep_dctrl
from sh import zcat
from sh import rm
from sh import wget
from sh import repoquery
from sh import mkdir

from uuid import uuid4

from tempfile import mkdtemp

from lxml import etree

from urlparse import urlparse

from utils import pushd

import settings as conf


class Repodata():
    def __init__(self, name):
        self.name = name
        self.base_url = ''
        self.repo_url = ''
        self.index_file = ''
        self.cache_dir = mkdtemp(dir=conf.CONF['cache_dir'])
        self.cache_uuid = uuid4()
        self.cache_threshold_sec = 60 * 60
        self.broken = False
        print("")
        print("Caching data for repository '{0}'".format(name))

    def grep_package(self, name, pattern=None):
        pass

    def test_cache(self):
        index_file_path = os.path.join(self.cache_dir, self.index_file)
        if os.path.exists(index_file_path):
            file_age = time.time() - os.path.getctime(index_file_path)
            if file_age > self.cache_threshold_sec:
                print("File '{0}' too old.".format(index_file_path))
                return False
        else:
            print("No such file '{0}'".format(index_file_path))
            return False

        print("Cache is up-to-date (index file updated {0} sec ago).".format(file_age))
        return True

    def update_cache(self):
        pass

    def __str__(self):
        index_file_url = '/'.join([self.repo_url, self.index_file])
        index_file_path = os.path.join(self.cache_dir, self.index_file)

        return "Remote URL: {0}, Cached file: {1}".format(
            index_file_url,
            index_file_path
        )


class DebMetadata(Repodata):
    def __init__(self, name):
        Repodata.__init__(self, name=name)
        self.index_file = 'Packages.gz'

    def grep_package(self, name, pattern=None):
        pattern = pattern if pattern else "(^|-){0}$"
        try:
            return [
                line.rstrip().split(' ', 1)
                for line in awk(
                    grep_dctrl(
                        zcat(os.path.join(self.cache_dir, self.index_file)),
                        '-F', 'Package',
                        '-e', pattern.format(name),
                        '-s', 'Package,Version'
                    ),
                    '/Package/{p=$2;next} /Version/{print p " " $2}'
                )
            ]
        except:
            return []

    def update_cache(self):
        if not self.test_cache():
            rm(self.cache_dir, '-rf')
            self.cache_dir = mkdtemp(dir=conf.CONF['cache_dir'])

            index_file_url = '/'.join([self.repo_url, self.index_file])
            index_file_path = os.path.join(self.cache_dir, self.index_file)

            try:
                print("Downloading index file '{0}' --> '{1}' ...".format(
                    index_file_url, index_file_path
                ))
                wget(index_file_url, '-O', index_file_path)
            except:
                self.broken = True


class RpmRepodata(Repodata):
    def __init__(self, name):
        Repodata.__init__(self, name=name)
        self.index_file = 'repodata/repomd.xml'

    def grep_package(self, name, pattern=None):
        try:
            package_list = []
            found_items = [
                line.rstrip()
                for line in repoquery(
                    "--repofrompath={0},{1}".format(self.cache_uuid, self.cache_dir),
                    '--search', name)
            ]

            for item in found_items:
                item_info = [
                    line.rstrip()
                    for line in repoquery(
                        "--repofrompath={0},{1}".format(self.cache_uuid, self.cache_dir),
                        '--info', item)
                ]

                pkg_info = {}
                for record in item_info:
                    try:
                        key, value = record.rstrip().split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        if key == 'Description':
                            break
                        pkg_info[key] = value
                    except:
                        continue
                package_list.append([pkg_info['Name'], pkg_info['Version']])

            return package_list
        except:
            return []

    def update_cache(self):
        if not self.test_cache():
            rm(self.cache_dir, '-rf')
            self.cache_dir = mkdtemp(dir=conf.CONF['cache_dir'])
            self.cache_uuid = uuid4()
            mkdir(os.path.join(self.cache_dir, 'repodata'))

            index_file_url = '/'.join([self.repo_url, self.index_file])
            index_file_path = os.path.join(self.cache_dir, self.index_file)

            try:
                print("Downloading index file '{0}' --> '{1}' ...".format(
                    index_file_url, index_file_path
                ))
                wget(index_file_url, '-O', index_file_path)
            except:
                self.broken = True
                return

            try:
                xmlroot = etree.parse(index_file_path).getroot()
                xmlns = xmlroot.nsmap[None]
                for item in xmlroot.findall("{{{0}}}data".format(xmlns)):
                    for subitem in item.findall("{{{0}}}location".format(xmlns)):
                        location = subitem.get('href')
                        url = '/'.join([self.repo_url, location])
                        path = '/'.join([self.cache_dir, location])
                        print("Downloading file '{0}' --> '{1}' ...".format(
                            url, path
                        ))
                        wget(url, '-O', path)
            except:
                self.broken = True


class GithubRepo():
    def __init__(self, name, branch='master', url=None):
        if url:
            self.path = urlparse(url=url).path
        else:
            self.path = conf.GITHUB_REPOS.get(name, name)
            self.url = "https://github.com/{0}".format(self.path)

        self.cache_dir = os.path.join(conf.CONF['cache_dir'], self.path)
        self.branch = branch

    def update(self):
        with pushd(self.cache_dir):
            git('reset', '--hard')
            git('clean', '-f', '-d', '-x')
            git('remote', 'update')
            git('pull', '--rebase')

    def clone(self):
        git('clone', url, self.cache_dir)
