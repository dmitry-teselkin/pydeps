#/usr/bin/python

import argparse

from lib.resolver import GlobalRequirements
from lib.resolver import GithubRepoDirectory
from lib.resolver import PythonPackage

from lib.reports import ReportGenerator

from lib.repodata import DebMetadata

parser = argparse.ArgumentParser()
parser.add_argument('--name', default='murano')
parser.add_argument('--path')
parser.add_argument('--greq-branch', default='master')
args = parser.parse_args()


package_path = ''
greq = GlobalRequirements(branch=args.greq_branch)

if args.name:
    repo = GithubRepoDirectory(name=args.name)
    repo.status(long=True, show=True)
    package_path = repo.path

if args.path:
    package_path = args.path

if package_path:
    python_package = PythonPackage(path=package_path)
    python_package.resolve_deps()
    python_package.validate_requirements(greq)

    report = ReportGenerator(python_package=python_package)
    report.user_friendly_report()

'''
# http://fuel-repository.mirantis.com/fwm/5.1/ubuntu/dists/precise/main/binary-amd64/

deb_repo = DebMetadata(url='http://fuel-repository.mirantis.com/fwm/5.1/ubuntu',
           codename='precise',
           arch='amd64',
           component='main')
deb_repo.update_cache()

murano_packages = deb_repo.grep_package(name='argparse')
for p in murano_packages:
    print p
'''
