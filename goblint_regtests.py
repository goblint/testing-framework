# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result

import re

SUCCESS = 0
FAIL = 1
WARN = 2
RACE = 3
DEADLOCK = 4
UNKNOWN = 5
UNKNOWN_EX = 6
NO_WARN = 7
NO_TERM = 8
TOTAL = 9


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Goblint.
    URL: https://goblint.in.tum.de/
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("goblint")

    def version(self, executable):
        return self._version_from_tool(executable, line_prefix="Goblint version: ")

    def name(self):
        return "Goblint"

    _DATA_MODELS = {"ILP32": "32bit", "LP64": "64bit"}

    def cmdline(self, executable, options, task, rlimits):
        additional_options = []

        if task.property_file:
            additional_options += ["--sets", "ana.specification", task.property_file]

        if task.options:
            data_model = task.options.get("data_model")
            if data_model:
                data_model_option = self._DATA_MODELS.get(data_model)
                if data_model_option:
                    additional_options += [
                        "--sets",
                        "exp.architecture",
                        data_model_option,
                    ]
                else:
                    raise benchexec.tools.template.UnsupportedFeatureException(
                        "Unsupported data_model '{}'".format(data_model)
                    )

        return [
            executable,
            *options,
            *additional_options,
            *task.input_files,
        ]

    def get_file_from_cmdline(self, cmdline):
        c = cmdline
        for i in c:
            # matches string ending in ".c" which should onyl mean the desired file
            if re.match(r".*\.c$", i):
                return i
        return None

    def synchronize_results(self, expected, results, term):
        # first iterate through results and match with expected values
        returns = {
            NO_TERM: 0,
            RACE: 0,
            DEADLOCK: 0,
            FAIL: 0,
            SUCCESS: 0,
            UNKNOWN: 0,
            UNKNOWN_EX: 0,
            WARN: 0,
            NO_WARN: 0,
            TOTAL: 0
        }
        if not term:
            returns[NO_TERM] += 1
            returns[TOTAL] += 1
        for l, v in results:
            for k, b in expected:
                if l == k and v == SUCCESS:
                    returns[SUCCESS] += 1
                    returns[TOTAL] += 1
                elif not l == k and b == WARN:
                    returns[WARN] += 1
                elif l == k and not v == b:
                    # check for unknown_ex and unknown
                    if b == UNKNOWN:
                        if not v == UNKNOWN and not v == UNKNOWN_EX:
                            returns[b] += 1
                            returns[TOTAL] += 1

                    elif b == UNKNOWN_EX:
                        if not v == UNKNOWN and not v == UNKNOWN_EX:
                            returns[b] += 1
                            returns[TOTAL] += 1
                    # if lines in both dbg and expected and values defer then increase expected value
                    else:
                        returns[b] += 1
                        returns[TOTAL] += 1

        #print(returns)
        # stringify:
        returnstring = {"NO_TERM": returns[NO_TERM], "RACE": returns[RACE], "DEADLOCK": returns[DEADLOCK],
                        "FAIL": returns[FAIL], "SUCCESS": returns[SUCCESS], "UNKNWON": 0, "UNKNWON!": 0,
                        "WARN": returns[WARN], "NO_WARN": returns[NO_WARN], "TOTAL": returns[TOTAL],
                        "UNKNOWN": returns[UNKNOWN], "UNKNOWN!": returns[UNKNOWN_EX]}

        return returnstring

    def determine_result(self, run):

        # print(run.output)
        should_term = True                  # termination expected?
        does_term = True                    # does it terminate?
        expectations = []                   # expected values
        results = []                        # actual values
        re_line_num = re.compile(r".*:(\d+)\)")
        test_file_addr = self.get_file_from_cmdline(run.cmdline)       # get the address of the tested file
        # test_file = open(test_file_addr,"r")
        # check for correct opening
        for line_num, line in enumerate(open(test_file_addr, "r"), 1):
            if "// TERM" in line:
                should_term = True
            elif "// NOTERM" in line:
                should_term = False

            elif "// RACE" in line:
                expectations.append((line_num, RACE))

            elif "// UNKNOWN!" in line:
                expectations.append((line_num, UNKNOWN_EX))

            elif "// UNKNOWN" in line:
                expectations.append((line_num, UNKNOWN))

            elif "// SUCCESS" in line:
                expectations.append((line_num, SUCCESS))

            elif "// FAIL" in line:
                expectations.append((line_num, FAIL))

            elif "// DEADLOCK" in line:
                expectations.append((line_num, DEADLOCK))

            elif "// WARN" in line:
                expectations.append((line_num, WARN))

            elif "// NOWARN" in line:
                expectations.append((line_num, NO_WARN))

        for line in run.output:
            if "Fatal error" in line:

                if "Assertion failed" in line:
                    return "ASSERTION"
                else:
                    m = re.search(
                        r"Fatal error: exception (Stack overflow|Out of memory|[A-Za-z._]+)",
                        line,
                    )
                    if m:
                        return "EXCEPTION ({})".format(m.group(1))
                    else:
                        return "EXCEPTION"

            elif re.search(r"does not reach the end", line):
                does_term = False

            elif re.search(r"lockset:", line):
                l = re_line_num.match(line)
                j = l.group(1)
                results.append((int(j), RACE))

            elif re.search(r"Deadlock", line):
                l = re_line_num.match(line)
                j = l.group(1)
                results.append((int(j), DEADLOCK))

            elif re.search(r"Assertion .* will fail", line):
                l = re_line_num.match(line)
                j = l.group(1)
                results.append((int(j), FAIL))

            elif re.search(r"Assertion .* will succeed", line):
                l = re_line_num.match(line)
                j = l.group(1)
                results.append((int(j), SUCCESS))

            elif re.search(r"Assertion .* is unknown", line):
                l = re_line_num.match(line)
                j = l.group(1)
                results.append((int(j), UNKNOWN))

            elif re.search(r"Uninitialized", line):
                l = re_line_num.match(line)
                j = l.group(1)
                results.append((int(j), WARN))

            elif re.search(r"dereferencing of null", line):
                l = re_line_num.match(line)
                j = l.group(1)
                results.append((int(j), WARN))

            elif re.search(r"CW:", line):
                l = re_line_num.match(line)
                j = l.group(1)
                results.append((int(j), WARN))

            elif re.search(r"Fixpoint not reached", line):
                l = re_line_num.match(line)
                j = l.group(1)
                results.append((int(j), WARN))

            elif re.search(r".*filehandle.*", line):
                l = re_line_num.match(line)
                j = l.group(1)
                results.append((int(j), WARN))

            elif re.search(r".* file is never closed", line):
                l = re_line_num.match(line)
                j = l.group(1)
                results.append((int(j), WARN))

            elif re.search(r".*unclosed files", line):
                l = re_line_num.match(line)
                j = l.group(1)
                results.append((int(j), WARN))

            elif re.search(r"changed pointer .*", line):
                l = re_line_num.match(line)
                j = l.group(1)
                results.append((int(j), WARN))

        # if an error occured return error
        if run.exit_code.value != 0:
            return result.RESULT_ERROR
        else:
            # calculate the results
            r = self.synchronize_results(expectations, results, (does_term and should_term))
            # print(expectations)
            # print(results)
            # returns the discrepancy string
            return str(r)
