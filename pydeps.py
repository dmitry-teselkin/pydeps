#/usr/bin/python

import argparse

from lib.resolver import GlobalRequirements
from lib.resolver import PipResolver
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

reqs = PipResolver()
reqs.resolve_from_dir(args.git_dir)

validation_result = reqs.validate(greq)

report = ReportGenerator(package_name=reqs.package_name)
report.machine_friendly_report(validation_result=validation_result)


