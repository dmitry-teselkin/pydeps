
import os
import re
import urllib2

from sh import rm
from sh import git
from sh import tail
from sh import pip
from sh import python

from getpass import getuser

from urlparse import urlparse

from utils import pushd

import settings as conf


class GithubRepoDirectory():
    def __init__(self, project=None, name=None, branch='master', url=None, base_path=None):
        if url:
            parts = urlparse(url=url).split('/')
            self.name = parts[-1]
            self.project = parts[-2]
        elif '/' in name:
            parts = name.split('/')
            self.name = parts[-1]
            self.project = parts[-2]
        elif name and project:
            self.name = name
            self.project = project
        elif name:
            project_list = []
            for key, value in conf.GITHUB_REPOS.items():
                if name in list(value):
                    project_list.append(key)

            if len(project_list) == 1:
                self.name = name
                self.project = project_list[0]
            else:
                raise Exception("Found '{0}' projects that hold repo '{1}': {2}".format(
                    len(project_list), name, project_list
                ))
        else:
            raise Exception('Not enough data to create GithubRepo class')

        if base_path:
            self.base_path = base_path
        else:
            self.base_path = conf.CONF['cache_dir']

        self.full_name = '/'.join((self.project, self.name))
        if url:
            self.url = url
        else:
            self.url = "https://github.com/{0}".format(self.full_name)
        self.path = os.path.join(self.base_path, 'github.com', self.full_name)

        self.branch = branch

        try:
            if self.status(show=True):
                self.reset()
            self.update()
        except:
            self.clone()

    def reset(self):
        with pushd(self.path):
            print('')
            print("Resetting Git repository in '{0}' ...".format(self.path))
            git('reset', '--hard')
            git('clean', '-f', '-d', '-x')
            print('... done')

    def update(self):
        with pushd(self.path):
            print('')
            print("Updating Git repository in '{0}' ...".format(self.path))
            git('remote', 'update')
            git('pull', '--rebase')
            print('... done')

    def clone(self):
        print('')
        print('Cloning new repository ...')
        git('clone', self.url, self.path)
        print('... done')

    def status(self, long=False, show=False):
        opts = '--long' if long else '--short'
        with pushd(self.path):
            git_status = git('status', opts)

        if show:
            print('')
            print("'git status' in '{0}':".format(self.path))
            for line in git_status:
                print("| {0}".format(line.rstrip()))

        return git_status


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
        print('')
        print("Loading Global Requirements from '{0}' ...".format(url))
        resp = urllib2.urlopen(url)
        for line in resp.readlines():
            dependency = PythonPackageDependency(line)
            if dependency.looks_good:
                self.entries.append(dependency)
        resp.close()
        print("... done. {0} records loaded.".format(len(self.entries)))

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


class PythonPackage():
    def __init__(self, path):
        if os.path.exists(path):
            self.path = path
        else:
            raise Exception("Path '{0}' does not exist.".format(path))

        self.dependencies = []

        with pushd(self.path):
            self.package_name = tail(python('setup.py', '--name'), '-1').rstrip()

    def _add_dependency(self, full_name, dependents=None):
        package = PythonPackageDependency(full_name, dependency_chain=dependents)
        if package.looks_good:
            self.dependencies.append(package)

    def resolve_deps(self, force=False):
        if force:
            self.dependencies = []

        if len(self.dependencies) > 0:
            return self.dependencies

        pip_install_opts = ['--no-install', '--verbose', '-e']

        rm('-r', '-f', "/tmp/pip_build_{0}".format(getuser()))

        with pushd(self.path):
            print('')
            print('Gathering package requirements ...')
            for line in pip('install', pip_install_opts, '.'):
                string = line.rstrip()
                match = re.search('Downloading/unpacking (.*?) \(from (.*?)\)', string)
                if match:
                    self._add_dependency(match.group(1), dependents=match.group(2))
                    continue

                match = re.search('Requirement already satisfied.*?: (.*?) in .*?\(from (.*?)\)', string)
                if match:
                    self._add_dependency(match.group(1), dependents=match.group(2))
                    continue

        print("... done. {0} records found.".format(len(self.dependencies)))

        return self.dependencies

    def validate_requirements(self, global_requirements):
        for dependency in self.dependencies:
            dependency.validate(global_requirements)
            dependency.is_direct = dependency.dependencies[0].name == self.package_name


class PythonPackageDependency():
    def __init__(self, full_name, dependency_chain=None):
        """
        :param full_name: A string containing dependency name and version
        :param dependency_chain: A string that lists packages which require current package
        :return:
        """
        self._full_name = full_name.split('#')[0].rstrip()
        self._dependency_chain = dependency_chain
        self.name = ""
        self.global_requirement = None
        self.is_compatible = False
        self.is_direct = False
        self.constraints = None
        self.dependencies = []

        if self._full_name:
            self.looks_good = True
        else:
            self.looks_good = False
            return

        self._evaluate()

    def __repr__(self):
        return "(Name: '{0}', Constraints: [{1}], Parents: [{2}])".format(
            self.name,
            ' , '.join([':'.join(c) for c in self.constraints]),
            ' -> '.join([repr(p) for p in self.dependencies])
        )

    def __str__(self):
        return "{0}{1}".format(self.name, self.constraints)

    def _evaluate(self):
        match = re.search('^(.*?)([<>!=].*)$', self._full_name)
        if match:
            self.name = match.group(1)
            self.constraints = VersionConstraints(match.group(2))
        else:
            self.name = self._full_name
            self.constraints = VersionConstraints()

        if self._dependency_chain:
            for string in self._dependency_chain.split('->'):
                dependency = PythonPackageDependency(string)
                if dependency.looks_good:
                    self.dependencies.append(dependency)

    def equals(self, dependency, strict=False):
        if self.name != dependency.name:
            return False

        return self.constraints.equals(dependency.constraints)

    def validate(self, global_requirements):
        self.is_compatible, self.global_requirement = global_requirements.validate(self)


class VersionConstraints():
    def __init__(self, string=''):
        self._constraints = []

        for c in string.split(','):
            match = re.search('^([<>!=]=?)(.*?)$', c)
            if match:
                self._constraints.append(
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

    def __str__(self):
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
                for c in self._constraints
            ]
        )

    def __contains__(self, item):
        return item in self._constraints

    def __len__(self):
        return len(self._constraints)

    def __iter__(self):
        for c in self._constraints:
            yield c

    def equals(self, constraints):
        if len(self) != len(constraints):
            return False

        for c in constraints:
            if not c in self:
                return False

        return True
