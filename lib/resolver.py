
import os
import re
import urllib2

from sh import rm
from sh import git
from sh import tail
from sh import pip
from sh import python

from getpass import getuser

from utils import pushd

from repodata import GithubRepo

import settings as conf


class PythonPackageMeta():
    def __init__(self, full_name, dependents=None):
        self._full_name = full_name.split('#')[0].rstrip()
        self._dependents = dependents
        self.name = ""
        self.constraints = []
        self.parents = []

        if self._full_name:
            self.looks_good = True
        else:
            self.looks_good = False
            return

        match = re.search('^(.*?)([<>!=].*)$', self._full_name)
        if match:
            self.name = match.group(1)
            constraint = match.group(2).split(',')
        else:
            self.name = self._full_name
            constraint = []

        for c in constraint:
            match = re.search('^([<>!=]=?)(.*?)$', c)
            self.constraints.append(
                [
                    {
                        '>': 'gt',
                        '<': 'lt',
                        '>=': 'ge',
                        '<=': 'le',
                        '==': 'eq',
                        '!=': 'ne'
                    }.get(match.group(1), ''),
                    match.group(2)
                ]
            )

        if self._dependents:
            for string in self._dependents.split('->'):
                meta = PythonPackageMeta(string)
                if meta.looks_good:
                    self.parents.append(meta)

    def __repr__(self):
        return "(Name: '{0}', Constraints: [{1}], Parents: [{2}])".format(
            self.name,
            ' , '.join([':'.join(c) for c in self.constraints]),
            ' -> '.join([repr(p) for p in self.parents])
        )

    def __str__(self):
        return "{0}{1}".format(self.name, self.str_constraint())

    def equals(self, package, strict=False):
        if self.name != package.name:
            return False

        if len(self.constraints) != len(package.constraints):
            return False

        for c in self.constraints:
            if not c in package.constraints:
                return False

        return True

    def str_constraint(self):
        return ','.join(
            [
                "{0}{1}".format(
                    {
                        'gt': '>',
                        'lt': '<',
                        'ge': '>=',
                        'le': '<=',
                        'eq': '==',
                        'ne': '!='
                    }.get(c[0]), c[1]
                )
                for c in self.constraints
            ]
        )


class GlobalRequirements():
    def __init__(self, branch=None, path=None):
        self.entries = []

        if branch:
            branch = {
                'icehouse': 'stable/icehouse'
            }.get(branch, branch)

            url = "https://raw.githubusercontent.com/openstack/" \
                  "requirements/{0}/global-requirements.txt".format(branch)

            self._load_from_url(url)
            return

        if path:
            raise Exception('Loading Global Requirements from file is not supported')

        raise Exception('Either branch or path to load Global Requirements must be provided')

    def _load_from_url(self, url):
        print("")
        print("Loading Global Requirements from '{0}' ...".format(url))
        print("BTW, cache dir is {0}".format(conf.CONF['cache_dir']))
        resp = urllib2.urlopen(url)
        for line in resp.readlines():
            meta = PythonPackageMeta(line)
            if meta.looks_good:
                self.entries.append(meta)
        resp.close()
        print("Done. {0} records loaded.".format(len(self.entries)))

    def get_package(self, name):
        for package in self.entries:
            if package.name == name:
                return package

    def validate(self, package):
        names = [n.name for n in self.entries]
        if package.name in names:
            greq_package = self.get_package(package.name)
            if greq_package.equals(package):
                return [True, greq_package]
            else:
                return [False, greq_package]
        else:
            return [False, None]


class PipResolver():
    def __init__(self):
        self._pip_install_opts = ['--no-install', '--verbose']
        self.package_name = ""
        self.entries = []
        pass

    def _add_pip_package(self, full_name, dependents=None):
        package = PythonPackageMeta(full_name, dependents=dependents)
        if package.looks_good:
            self.entries.append(package)

    def resolve_from_dir(self, path):
        self._pip_install_opts.append('-e')
        if not os.path.exists(path):
            raise Exception("Path not found '{0}'".format(path))

        rm('-r', '-f', "/tmp/pip_build_{0}".format(getuser()))

        with pushd(path):
            print("")
            print("'git status' in '{0}':".format(path))
            print("------------")
            print(git('status'))
            print("------------")

            self.package_name = tail(python("setup.py", "--name"), "-1").rstrip()

            print("")
            print("Gathering package requirements ...")
            for line in pip('install', self._pip_install_opts, '.'):
                string = line.rstrip()
                match = re.search(
                    'Downloading/unpacking (.*?) \(from (.*?)\)',
                    string
                )
                if match:
                    self._add_pip_package(match.group(1), dependents=match.group(2))
                    continue

                match = re.search(
                    'Requirement already satisfied.*?: (.*?) in .*?\(from (.*?)\)',
                    string
                )
                if match:
                    self._add_pip_package(match.group(1), dependents=match.group(2))
                    continue
            print("Done. {0} records found.".format(len(self.entries)))

    def resolve_from_stackforge(self, url):
        pass

#    def resolve_from_git(self, name, url=None):
#        repo = GithubRepo(name=name, url=url)
#        self.resolve_from_dir(repo.cache_dir)

    def validate(self, global_requirements):
        """
        Returns a dict of dicts:
            <package name>: {
                'orig_package': <package found in component's requirements>,
                'greq_package': <package found in global requirements>,
                'status': <if package complies with global requirements>,
                'is_direct_dependency': <if package is a direct dependency for the component>
            }
        """
        result = {}
        for package in self.entries:
            status, greq_package = global_requirements.validate(package)
            result[package.name] = {
                'orig_package': package,
                'greq_package': greq_package,
                'status': status,
                'is_direct_dependency': self.package_name == package.parents[0].name
            }
        return result
