#/usr/bin/python

import argparse

from lib.resolver import GlobalRequirements
from lib.resolver import GitRepository
from lib.resolver import PythonPackage

from lib.reports import ReportGenerator

from lib.repodata import DebMetadata

from lib.repodata import RepodataUrl


parser = argparse.ArgumentParser()
parser.add_argument('--name', default='murano')
#parser.add_argument('--path')
parser.add_argument('--branch', default='master')
parser.add_argument('--greq-branch')
args = parser.parse_args()

if args.greq_branch:
    greq_branch = args.greq_branch
else:
    greq_branch = args.branch

package_path = ''
greq = GlobalRequirements(branch=greq_branch)
greq.add_alias('glance_store', 'glance-store')
greq.add_alias('posix_ipc', 'posix-ipc')


#if args.path:
#    package_path = args.path

if args.name:
    #repo = GithubRepoDirectory(name=args.name)
    repo = GitRepository(name=args.name, branch=args.branch)
    repo.status(long=True, show=True)
    package_path = repo.path

if package_path:
    python_package = PythonPackage(path=package_path)
    python_package.resolve_deps()
    python_package.validate_requirements(greq)

    report = ReportGenerator(python_package=python_package)
    report.user_friendly_report()

'''
repo_url = RepodataUrl(product_name='fuel', product_release='master', product_version='5.1')
print(repo_url.url)

deb_repo = DebMetadata(repo_url=repo_url)
deb_repo.update_cache()

murano_packages = deb_repo.grep_package(name='python-requests')
for p in murano_packages:
    print p
'''
