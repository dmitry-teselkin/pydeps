#/usr/bin/python

import argparse

from lib.resolver import GlobalRequirements
from lib.resolver import GithubRepoDirectory
from lib.resolver import PythonPackage

from lib.reports import ReportGenerator

import lib.settings as conf


parser = argparse.ArgumentParser(description="Resolve package dependencies")

parser.add_argument('--git-dir', dest='git_dir', default='/home/dim/Temp/cache/oslo.messaging',
                    help='Local GIT repository path.')

parser.add_argument('--greq-branch', dest='greq_branch', default='master',
                    help='Global Requirements branch.')

args = parser.parse_args()


print("""
SUMMARY:
--------
Resolving dependencies for python component located in local GIT repository '{0}'
Global Requirements are from '{1}' branch
Cache dir '{2}'
--------""".format(
    args.git_dir,
    args.greq_branch,
    conf.CONF['cache_dir']
))

greq = GlobalRequirements(branch=args.greq_branch)

repo = GithubRepoDirectory(name='oslo.messaging')
repo.status(long=True, show=True)

python_package = PythonPackage(path=repo.path)
python_package.resolve_deps()
result = python_package.validate_requirements(greq)

report = ReportGenerator(package_name=python_package.package_name)
report.machine_friendly_report(validation_result=result)
