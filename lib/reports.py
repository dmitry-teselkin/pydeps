

class ReportGenerator():
    def __init__(self, package_name):
        self.package_name = package_name
        self.header = ''

    def _top_block_delimiter(self, header):
        self.header = header
        print("")
        print(self.header)
        print("=" * len(self.header))

    def _bottom_block_delimiter(self):
        print("=" * len(self.header))

    def print_report_block(self, validation_result, compatible=False, direct=False):
        str_direct = 'direct' if direct else 'indirect'
        str_compatible = 'compatible' if compatible else 'incompatible'

        self._top_block_delimiter("{0} dependencies {1} with global requirements:".format(
            str_direct.capitalize(), str_compatible
        ))
        count = 0
        for key in sorted(validation_result.keys()):
            item = validation_result[key]
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

    def print_machine_friendly_report_block(self, validation_result, compatible=False, direct=False):
        str_direct = 'direct' if direct else 'indirect'
        str_compatible = 'compatible' if compatible else 'incompatible'
        delimiter = ";"

        print("# ---------- {0} {1} dependencies ----------".format(str_compatible, str_direct))
        for key in sorted(validation_result.keys()):
            item = validation_result[key]
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

    def package_matching_report_block(self, validation_result=None, repository_set=None, direct=True):
        str_direct = 'direct' if direct else 'indirect'

        for key in sorted(validation_result.keys()):
            item = validation_result[key]
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

    def global_requirements_validation(self, validation_result):
        print("")
        print("Report for package '{0}':".format(self.package_name))

        self.print_report_block(validation_result=validation_result,
                                compatible=True, direct=True)
        self.print_report_block(validation_result=validation_result,
                                compatible=False, direct=True)
        self.print_report_block(validation_result=validation_result,
                                compatible=True, direct=False)
        self.print_report_block(validation_result=validation_result,
                                compatible=False, direct=False)

    def machine_friendly_report(self, validation_result):
        print("")
        print("#{1:35}{0}{2:15}{0}{3:10}{0}{4:35}{0}{5}".format(
            ';',
            'Global Requirements',
            'Is Compatible',
            'Is Direct Dependency',
            'Component Requirements',
            'Required By'
        ))
        self.print_machine_friendly_report_block(validation_result=validation_result,
                                                 compatible=True, direct=True)
        self.print_machine_friendly_report_block(validation_result=validation_result,
                                                 compatible=False, direct=True)
        self.print_machine_friendly_report_block(validation_result=validation_result,
                                                 compatible=True, direct=False)
        self.print_machine_friendly_report_block(validation_result=validation_result,
                                                 compatible=False, direct=False)
        print("")

    def package_matching(self, validation_result=None, repository_set=None):
        print("")
        print("Looking for packages matching:")
        self.package_matching_report_block(validation_result=validation_result,
                                             repository_set=repository_set, direct=True)
        self.package_matching_report_block(validation_result=validation_result,
                                             repository_set=repository_set, direct=False)
        print("")
