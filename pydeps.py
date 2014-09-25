#/usr/bin/python

from lib.resolver import GlobalRequirements
from lib.resolver import GithubRepoDirectory
from lib.resolver import PythonPackage

from lib.reports import ReportGenerator

greq = GlobalRequirements(branch='master')

repo = GithubRepoDirectory(name='oslo.messaging')
repo.status(long=True, show=True)

python_package = PythonPackage(path=repo.path)
python_package.resolve_deps()
result = python_package.validate_requirements(greq)

report = ReportGenerator(package_name=python_package.package_name)
report.machine_friendly_report(validation_result=result)
