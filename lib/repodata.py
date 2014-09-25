
import os
import time

from sh import awk
from sh import grep_dctrl
from sh import gzip
from sh import rm
from sh import wget
from sh import repoquery
from sh import mkdir

from uuid import uuid4

from tempfile import mkdtemp

from lxml import etree

from utils import pushd

from urlparse import urlparse

import settings as conf


class RepodataUrl():
    def __init__(self, product_name, product_version='', product_release='',
                dist='', codename='', component='', arch=''):
        if product_name == 'fuel':
            product_release = product_release or 'master'
            dist = dist or 'ubuntu'
        elif product_name == 'ubuntu':
            dist = 'ubuntu'
        elif product_name == 'centos':
            dist = 'centos'

        if dist == 'ubuntu':
            codename = codename or 'precise'
            component = component or 'main'
            arch = arch or 'amd64'
        elif dist == 'centos':
            arch = arch or 'x86_64'

        self.fields = {
            'product_name': product_name,
            'product_version': product_version,
            'product_release': product_release,
            'dist': dist,
            'codename': codename,
            'component': component,
            'arch': arch
        }

        url_prefix = {
            'fuel': 'http://fuel-repository.mirantis.com',
            'osci': '',
            'ubuntu': 'http://archive.ubuntu.com',
            'centos': ''
        }.get(product_name, '')

        url_product_suffix = {
            'fuel-release': 'fwm/{product_version}/{dist}',
            'fuel-stable': 'osci/{dist}-fuel-{product_version}-stable/{dist}',
            'fuel-testing': 'osci/{dist}-fuel-{product_version}-testing/{dist}',
            'fuel-master': 'osci/{dist}-fuel-master',
        }.get('{product_name}-{product_release}'.format(**self.fields), '')

        url_dist_suffix = {
            'ubuntu': 'dists/{codename}/{component}/binary-{arch}',
            'centos': 'os/{arch}',
        }.get(dist, '')

        self.url = '/'.join([url_prefix, url_product_suffix, url_dist_suffix])


class Repodata():
    def __init__(self, url, base_path=None):
        # Base path where files related to the repository are located
        self.base_path = base_path if base_path else conf.CONF['cache_dir']
        self.path = ''
        # Main index file of the repository
        self.index_file = ''

        self.cache_uuid = uuid4()
        self.cache_threshold_sec = 60 * 60

        self.broken = False
        self.url = urlparse(url=url)

        self.repo_url = ''

    def grep_package(self, name, pattern=None):
        pass

    def test_cache(self):
        index_file_path = os.path.join(self.path, self.index_file)
        print("Testing index file '{0}'".format(self.path))
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
        index_file_path = os.path.join(self.path, self.index_file)

        return "Remote URL: {0}, Cached file: {1}".format(
            index_file_url,
            index_file_path
        )


class DebMetadata(Repodata):
    def __init__(self, url, codename='precise', arch='amd64', component='main', base_path=None):
        Repodata.__init__(self, url=url, base_path=base_path)

        self.index_file = 'Packages'

        self.path = os.path.normpath(os.path.join(self.base_path, self.url.netloc, '.' + self.url.path,
                                                  codename, component, 'binary-' + arch))

        self.repo_url = '/'.join([self.url.geturl(), 'dists', codename, component, 'binary-' + arch])

    def grep_package(self, name, pattern=None):
        pattern = pattern if pattern else "{0}"
        try:
            return [
                line.rstrip().split(' ', 1)
                for line in awk(
                    grep_dctrl(
                        '--field', 'Package,Provides',
                        '--show-field', 'Package,Version',
                        '--eregex', '--ignore-case',
                        '--pattern', pattern.format(name),
                        os.path.join(self.path, self.index_file)
                    ),
                    '/Package/{p=$2;next} /Version/{print p " " $2}'
                )
            ]
        except Exception as err:
            print(str(err))
            return []

    def update_cache(self):
        if not self.test_cache():
            rm(self.path, '-rf')
            mkdir('-p', self.path)

            index_file_url = '/'.join([self.repo_url, 'Packages.gz'])
            index_file_path = os.path.join(self.path, self.index_file)

            print("Downloading index file '{0}' --> '{1}' ...".format(
                index_file_url, index_file_path
            ))
            try:
                with pushd(self.path):
                    wget(index_file_url, '-O', self.index_file + '.gz')
                    gzip('-d', self.index_file + '.gz')
            except Exception as err:
                print(str(err))
                self.broken = True

"""
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
"""
