
from prettytable import PrettyTable


class ReportGenerator():
    def __init__(self, python_package):
        self.package_name = python_package.package_name
        self.header = ''

        """
        Create a dict of dicts:
            <package name>: {
                'orig_package': <package found in component's requirements>,
                'greq_package': <package found in global requirements>,
                'status': <if package complies with global requirements>,
                'is_direct_dependency': <if package is a direct dependency for the component>
            }
        """
        self.data = {}
        for dependency in python_package.dependencies:
            self.data[dependency.name] = {
                'orig_package': dependency,
                'greq_package': dependency.global_requirement,
                'status': dependency.is_compatible,
                'is_direct_dependency': dependency.is_direct
            }

    def _top_block_delimiter(self, header):
        self.header = header
        print("")
        print(self.header)
        print("=" * len(self.header))

    def _bottom_block_delimiter(self):
        print("=" * len(self.header))

    def print_report_block(self, compatible=False, direct=False):
        str_direct = 'direct' if direct else 'indirect'
        str_compatible = 'compatible' if compatible else 'incompatible'

        self._top_block_delimiter("{0} dependencies {1} with global requirements:".format(
            str_direct.capitalize(), str_compatible
        ))
        count = 0
        for key in sorted(self.data.keys()):
            item = self.data[key]
            if item['status'] == compatible and item['is_direct_dependency'] == direct:
                count += 1
                if item['greq_package']:
                    greq_status = "Global Requirements: {0}".format(item['greq_package'])
                else:
                    greq_status = "Not found in Global Requirements"

                if direct:
                    str_parents = "  "
                else:
                    str_parents = "(From: {0})".format(
                        " -> ".join([str(p) for p in item['orig_package'].parents])
                    )

                print("{0} {1} # {2}".format(item['orig_package'], str_parents, greq_status))
        self._bottom_block_delimiter()

        print("Total: {0}".format(count))

    def print_machine_friendly_report_block(self, compatible=False, direct=False):
        str_direct = 'direct' if direct else 'indirect'
        str_compatible = 'compatible' if compatible else 'incompatible'
        delimiter = ";"

        print("# ---------- {0} {1} dependencies ----------".format(str_compatible, str_direct))
        for key in sorted(self.data.keys()):
            item = self.data[key]
            if item['status'] == compatible and item['is_direct_dependency'] == direct:
                str_parents = " -> ".join([str(p) for p in item['orig_package'].dependencies])

                print("{1:35}{0}{2:15}{0}{3:10}{0}{4:35}{0}{5}".format(
                    delimiter,
                    item['greq_package'],
                    str_compatible,
                    str_direct,
                    item['orig_package'],
                    str_parents
                ))

    def print_user_friendly_report_block(self, compatible=False, direct=False):
        table = PrettyTable([
            'N',
            'Component Requires',
            'Global Requirements',
            'Required By'
        ])
        table.align['Global Requirements'] = 'l'
        table.align['Component Requires'] = 'l'
        table.align['Required By'] = 'l'

        str_direct = 'direct' if direct else 'indirect'
        str_compatible = 'compatible' if compatible else 'incompatible'

        print('')
        print("{0} dependencies, {1} with global requirements".format(str_direct.upper(), str_compatible.upper()))

        line_num = 1
        for key in sorted(self.data.keys()):
            item = self.data[key]
            if item['status'] == compatible and item['is_direct_dependency'] == direct:
                str_parents = " -> ".join([str(p) for p in item['orig_package'].dependencies])
                table.add_row([
                    line_num,
                    item['orig_package'],
                    item['greq_package'],
                    str_parents
                ])
                line_num += 1

        print table

    def package_matching_report_block(self, repository_set=None, direct=True):
        str_direct = 'direct' if direct else 'indirect'

        for key in sorted(self.data.keys()):
            item = self.data[key]
            if item['is_direct_dependency'] == direct:
                str_orig_package = str(item['orig_package'].name)
                str_greq_package = str(item['greq_package'])
                print("# {0}".format(item['orig_package']))
                for r, p, v in repository_set.grep_package(item['orig_package'].name):
                    print("{1:25}{0}{2:10}{0}{3:35}{0}{4:40}{0}{5}".format(
                        ';',
                        str_orig_package,
                        str_direct,
                        str_greq_package,
                        ' '.join([p, v]),
                        r.name
                    ))

    def global_requirements_validation(self):
        print("")
        print("Report for package '{0}':".format(self.package_name))

        self.print_report_block(compatible=True, direct=True)
        self.print_report_block(compatible=False, direct=True)
        self.print_report_block(compatible=True, direct=False)
        self.print_report_block(compatible=False, direct=False)

    def machine_friendly_report(self):
        print("")
        print("#{1:35}{0}{2:15}{0}{3:10}{0}{4:35}{0}{5}".format(
            ';',
            'Global Requirements',
            'Is Compatible',
            'Is Direct Dependency',
            'Component Requirements',
            'Required By'
        ))
        self.print_machine_friendly_report_block(compatible=True, direct=True)
        self.print_machine_friendly_report_block(compatible=False, direct=True)
        self.print_machine_friendly_report_block(compatible=True, direct=False)
        self.print_machine_friendly_report_block(compatible=False, direct=False)
        print("")

    def user_friendly_report(self):
        self.print_user_friendly_report_block(compatible=True, direct=True)
        self.print_user_friendly_report_block(compatible=False, direct=True)
        self.print_user_friendly_report_block(compatible=True, direct=False)
        self.print_user_friendly_report_block(compatible=False, direct=False)

    def package_matching(self, repository_set=None):
        print("")
        print("Looking for packages matching:")
        self.package_matching_report_block(repository_set=repository_set, direct=True)
        self.package_matching_report_block(repository_set=repository_set, direct=False)
        print("")
