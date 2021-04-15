import os
import subprocess
import threading
import time
import re
import socket
import datetime

# Default benchmark file if nor specified
DEFAULT_XML_FILE = "goblinit.xml"
# Address of the Goblinit server, (IP-ADDRESS, PORT)
SERVER_ADDRESS = ('localhost', 59646)
# Client identifier, used to identifiy different clients from each other by the server
# Please set this for each different client manually
IDENTIFIER = "Benchmarko"

# regular expression declarations
re_exit = re.compile('exit')
re_rc_timer = re.compile('timer \d*')
re_rc_timer_file = re.compile('timer \d* .+\.xml')
re_number = re.compile('\d*')
re_cancel_rec_timer = re.compile('cancel timer')
re_schedule_date = re.compile('schedule ((\d\d\d\d.\d\d.\d\d) ([0-2]\d:[0-5]\d))')
re_schedule_time = re.compile('schedule (\d*:[0-5]\d:[0-5]\d)')
re_schedule_time_file = re.compile('schedule (\d*:[0-5]\d:[0-5]\d) .+\.xml')
re_schedule_date_file = re.compile('schedule ((\d\d\d\d.\d\d.\d\d) ([0-2]\d:[0-5]\d)) .+\.xml')
re_print_schedule = re.compile('schedule print')
re_print_timer = re.compile('timer print')
re_cancel_scheduled = re.compile('cancel \d*')
re_clone = re.compile('clone')
re_pull = re.compile('pull')
re_test = re.compile('test')
re_gen_xml = re.compile('generate')
re_xml_file = re.compile(('.+\.xml'))
re_start_bench = re.compile('startbenchmark .*\.xml')
re_invalid_input = re.compile('Invalid Input')


# Class to manage the download and update of the git repository
class RepoManager:

    def __init__(self, cloneurl):
        self.url = cloneurl

    # clones or pulls newest version of th repo via the gitgoblin.sh script
    def update_repository(self, clone=False):
        if clone:
            # clone the goblint repository
            subprocess.run("./gitgoblin.sh -n", shell=True)
        else:
            # pull the newest version of goblint
            subprocess.run("./gitgoblin.sh", shell=True)


# Class that converts the tests filestructure into a benchexec readable xml file in order to ease future expansion
# Use currently not recommended
class XMLGenerator:
    # path to the testdirectory starting from the goblinit.py file TODO: possibility to give list of testing directories
    test_directory = "analyzer/tests"
    # header of the benchexec xml file required for benchgexec to run TODO:Add possiblity to switch rundefinitons, and test quantity
    header = '<?xml version="1.0"?>\n' \
             '<!--required for benchexec-->\n' \
             '<!DOCTYPE benchmark PUBLIC "+//IDN sosy-lab.org//DTD BenchExec benchmark 2.3//EN" "https://www.sosy-lab.org/benchexec/benchmark-2.3.dtd">\n' \
             '<!-- benchexec tool declaration-->\n' \
             '<benchmark tool="goblint" displayName="Goblinit testruns">\n' \
             '\t<!-- <rundefinition> defines a tool configuration to benchmark TODO in order to correctly asses test results -->\n' \
             '\t<rundefinition/>\n'
    # end of the benchexec xml file
    endmark = '</benchmark>'

    # generates the xml string starting from the given directory
    def generate_xml(self, directory):
        out = ''
        out = self.header + self.get_xml_of_directory_information(directory) + self.endmark
        return out

    # travels through the specified directory and returns a list with all
    def get_xml_of_directory_information(self, directory):
        out = ''
        for path, dirname, filenames in os.walk(directory):
            out = out + self.test_converter(path, filenames)
        return out

    def test_converter(self, path, tests):
        path_name = path.split('\\')
        re_test = re.compile('\S*.c')
        output = ''
        c = 0
        for i in tests:
            if re_test.fullmatch(i):
                c = c + 1
        if (c > 0):
            output = '<tasks name="'
            for i in path_name:
                output = output + ' ' + i
            output = output + '">\n'
            for i in tests:
                if re_test.fullmatch(i):
                    output = output + '\t<include>' + path.replace('\\', '/') + '/' + i + '<\\include>\n'
            output = output + '<\\tasks>\n'
        return output


# class which is repsonible for the communication between the client and the server
class Correspondent(threading.Thread):
    def __init__(self, identity, goblinit):
        super().__init__()
        self.identity = identity  # client identifier
        self.goblinit = goblinit  # goblinit main thread
        self.exit = False  # exit flag

        # establishing connection to the server
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.connect(SERVER_ADDRESS)
        # identification message
        self.send("identity")
        # print("pre listen")

    # function which is executed when this thread is started
    def run(self):
        # loop to listen to the servers messages and handles them
        while not self.exit:
            try:
                response = str(self.server.recv(4096), 'utf8')
                if not response:
                    break
                else:
                    # print("response: " + response)
                    if re_exit.fullmatch(response):
                        self.exit = True
                    else:
                        # in order to avoid infinte loop True is set to indicate message from server
                        self.goblinit.handle(response, True)
            except ConnectionResetError:
                self.exit = True
                self.goblinit.cexit = True

    # sends the message to the server, always puts the identifier first in every message
    def send(self, message):
        try:
            m = self.identity + " " + message
            self.server.send((bytes(m, 'utf8')))
        except ConnectionResetError:
            self.exit = True
            self.goblinit.cexit = True


# Main Goblinit Class, that manages timer, bench execution and the repo manager
class Goblinit:
    repomanager = None
    xmlgenerator = None
    busy = False

    def __init__(self):
        self.repomanager = RepoManager("https://github.com/goblint/analyzer")  # responsible for pulling goblint
        # self.xmlgenerator = XMLGenerator()                           # used to generate xml file, use not recommended
        self.corresspondent = Correspondent(IDENTIFIER, self)  # used to communicate with the server
        self.cexit = False

        self.corresspondent.start()
        self.listen()


    # function to listen to the console input
    def listen(self):
        # loop to listen for input
        while not self.cexit:
            console_input = input()
            if re_exit.fullmatch(console_input):
                self.cexit = True
                self.corresspondent.send(console_input)
            else:
                # handle the console input
                self.handle(console_input)

    # function to match the input with its purpose via regex matching
    def handle(self, console_input, from_server=False):
        # print(console_input)

        # pulls newest version of goblint, no need to send to server
        if re_pull.fullmatch(console_input):
            self.repomanager.update_repository()

        # clones golbint repository again, should not be needed, as goblint is clones on installation
        elif re_clone.fullmatch(console_input):
            self.repomanager.update_repository(True)

        # generates the xml output of the generator and prints it, use not recommended
        elif re_gen_xml.fullmatch(console_input):
            print(self.xmlgenerator.generate_xml(self.xmlgenerator.test_directory))

        # starts the benchmark, should only come from server
        elif re_start_bench.fullmatch(console_input):
            if from_server:
                self.start_benchmark(console_input.split()[1])
            else:
                print("Invalid Input, start benchmark through server")

        elif re_invalid_input.fullmatch(console_input):
            print("Invalid Input, please try again!")

        else:
            # if not from serverm send message to server for further processing
            if not from_server:
                self.corresspondent.send(console_input)

    # function to start the benchamrking process and table generation
    def start_benchmark(self, filename=DEFAULT_XML_FILE):
        if not self.busy:
            self.busy = True
            print("Benchmark started")
            self.repomanager.update_repository()
            result_folder = filename + str(int(time.time())) + "/"
            subprocess.run("(cd analyzer/ ; sudo benchexec --no-container" + " ../benchmarks/" + filename + " -o ../Testresults/ " + result_folder + ")", shell=True)
            subprocess.run("sudo table-generator Testresults/" + result_folder + "*.results.*.xml.bz2", shell=True)
            time.sleep(2)
            print("Benchmark finished")
            self.corresspondent.send("benchmark finished")
            self.busy = False
        else:
            print("Cant run Test, Goblinit is Currently Busy")


# helper functions


# Main Method:
def main():
    G = Goblinit()


if __name__ == '__main__':
    main()
