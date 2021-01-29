import os
import subprocess
import threading
import time
import re
import datetime

DEFAULT_XML_FILE = "goblinit.xml"

# Class to manage the download and update of the git repository
class RepoManager:

    def __init__(self, cloneurl):
        self.url = cloneurl

    # clones oor pulls newest version of th repo via the goblinit shell script
    def update_repository(clone=False):
        if clone:
            # clone the goblint repository
            subprocess.run("./goblinit.sh -n")
        else:
            # pull the newest version of goblint
            subprocess.run("./goblinit.sh")


# Class that converts the tests filestructure into a benchexec readable xml file in order to ease future expansion
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
                    output = output + '\t<include>' + path.replace('\\', '/') + '/' + i + '<\include>\n'
            output = output + '<\\tasks>\n'
        return output


# timer that restarts when it is done. ist it restarts based on when the last timer ended (-> when the benchmark
# started) if the benchmark took longer than the timer, the next benchmark will start directly after it

class Recurring_Timer(threading.Thread):
    def __init__(self, goblinit, interval, filename=DEFAULT_XML_FILE, oginterval=0):
        self.cancel = threading.Event()
        self.filename = filename
        self.goblinit = goblinit
        if oginterval == 0:
            self.oginterval = interval
            self.interval = interval
        else:
            self.interval = oginterval
        super(Recurring_Timer, self).__init__()

    def getCancel(self):
        return self.cancel

    def setCancel(self, lock):
        if lock == True:
            self.cancel.set()
        elif lock == False:
            self.cancel.clear()

    def run(self):
        runtime = 0
        while True:
            # print("runnin")
            if (runtime < self.interval):
                time.sleep(self.interval - runtime)
            if self.cancel.isSet():
                # print("stoppn")
                break
            else:
                # print("callin")
                startime = time.time()
                self.goblinit.start_benchmark(self.filename)
                endtime = time.time()
                runtime = round(endtime - startime)


# Main Goblinit Class, that manages timer, bench execution and the repo manager
class Goblinit:
    scheduled_timers = []
    recurring_Timer = None
    repomanager = None
    xmlgenerator = None
    busy = False

    def __init__(self):
        self.repomanager = RepoManager("https://github.com/goblint/analyzer")
        self.xmlgenerator = XMLGenerator()
        self.listen()

    # listens on the console indefinetly until exit is called:
    def listen(self):
        exit = False
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
        re_cancel_scheduled = re.compile('cancel \d*')
        re_clone = re.compile('clone')
        re_pull = re.compile('pull')
        re_test = re.compile('test')
        re_gen_xml = re.compile('generate')
        re_xml_file = re.compile(('.+\.xml'))

        while not exit:
            console_input = input()
            if re_exit.fullmatch(console_input):
                exit = True
            elif re_rc_timer.fullmatch(console_input):
                # cancel old timer: old timer thread will run the sleep through, and end then,
                # new timer starts running immediately
                if self.recurring_Timer:
                    self.recurring_Timer.getCancel().set()
                # self.recurring_Timer.join()
                intertime = int(re_number.match(console_input.split()[1]).group())
                print(intertime)
                self.recurring_Timer = Recurring_Timer(self, intertime)
                self.recurring_Timer.start()

            elif re_rc_timer_file.fullmatch(console_input):
                file = re_xml_file.match(console_input.split()[2]).group()
                #print("yo wanna open " + file)
                intertime = int(re_number.match(console_input.split()[1]).group())
                print(intertime)
                self.recurring_Timer = Recurring_Timer(self, intertime, file)
                self.recurring_Timer.start()

            elif re_schedule_date.fullmatch(console_input):
                components = console_input.split()
                self.start_date_timer(stringdate_to_seconds(components[1] + ' ' + components[2]))

            elif re_schedule_date_file.fullmatch(console_input):
                components = console_input.split()
                self.start_date_timer(stringdate_to_seconds(components[1] + ' ' + components[2]), components[3])

            elif re_schedule_time.fullmatch(console_input):
                components = console_input.split()
                self.start_date_timer(stringtime_to_seconds(components[1]))

            elif re_schedule_time_file.fullmatch(console_input):
                components = console_input.split()
                self.start_date_timer(stringtime_to_seconds(components[1]), components[3])

            elif re_print_schedule.fullmatch(console_input):
                print(self.scheduled_timers)

            elif re_cancel_scheduled.fullmatch(console_input):
                components = console_input.split()
                pos = int(components[1])
                if len(self.scheduled_timers) > pos:
                    self.scheduled_timers[pos].cancel()
                    self.scheduled_timers.pop(pos)
                else:
                    print("Invalid List Position")
            elif re_pull.fullmatch(console_input):
                self.repomanager.update_repository()

            elif re_clone.fullmatch(console_input):
                self.repomanager.update_repository(True)

            elif re_test.fullmatch(console_input):
                self.start_benchmark()

            elif re_gen_xml.fullmatch(console_input):
                print(self.xmlgenerator.generate_xml(self.xmlgenerator.test_directory))

            elif re_cancel_rec_timer.fullmatch(console_input):
                self.recurring_Timer.getCancel().set()
                self.recurring_Timer = None
            else:
                print("Invalid Input, please try again!")
        # exit protocol: stop all the timers
        if self.recurring_Timer:
            self.recurring_Timer.getCancel().set()

        for x in self.scheduled_timers:
            x.cancel()

    def start_date_timer(self, seconds, filename=DEFAULT_XML_FILE):
        tim = threading.Timer(seconds, self.start_benchmark, [filename])
        self.scheduled_timers.append(tim)
        tim.start()
        # print(self.scheduled_timers)
        return

    def start_benchmark(self, filename=DEFAULT_XML_FILE):
        if not self.busy:
            self.busy = True
            print("Benchmark started")
            # self.repomanager.update_repository()
            result_folder = filename + str(int(time.time()))
            #subprocess.run("(cd analyzer/ ; sudo benchexec " + "../benchmarks/" + filename + "-o ../Testresults/ " + result_folder)
            #subprocess.run("sudo table-generator Testresults/resultfolder/*.results.xml.bz2
            time.sleep(2)
            print("Benchmark finished")
            self.busy = False
        else:
            print("Cant run Test, Goblinit is Currently Busy")


# helper functions

def stringdate_to_seconds(value):
    date = value.split()[0].split('.')
    clock = value.split()[1].split(':')
    dt = datetime.datetime(int(date[0]), int(date[1]), int(date[2]), int(clock[0]), int(clock[1]), 0, 0)
    diff = dt - datetime.datetime.now()
    return diff.total_seconds()


def stringtime_to_seconds(value):
    # print(value)
    components = value.split(':')
    # print(components)
    hours = int(components[0])
    if hours < 0:
        raise ValueError
    minutes = int(components[1])
    if not (0 <= minutes < 60):
        raise ValueError
    seconds = int(components[2])
    if not (0 <= seconds < 60):
        raise ValueError
    # print(360 * hours + 60 * minutes * seconds)
    return 360 * hours + 60 * minutes + seconds


# Main Method:
def main():
    G = Goblinit()


if __name__ == '__main__':
    main()
