#/usr/bin/python

import argparse

from lib.resolver import GlobalRequirements
from lib.resolver import GithubRepoDirectory
from lib.resolver import PythonPackage

from lib.reports import ReportGenerator

parser = argparse.ArgumentParser()
parser.add_argument('name', default='murano', nargs='?')
args = parser.parse_args()

greq = GlobalRequirements(branch='master')

repo = GithubRepoDirectory(name=args.name)
repo.status(long=True, show=True)

python_package = PythonPackage(path=repo.path)
python_package.resolve_deps()
python_package.validate_requirements(greq)

report = ReportGenerator(python_package=python_package)
report.machine_friendly_report()
