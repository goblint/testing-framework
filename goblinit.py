import os
import subprocess
import threading
import time
import re
import datetime

global cancel_event
cancel_event = threading.Event()


# Class to manage the download and update of the git repository
class RepoManager:

    def __init__(self, cloneurl):
        self.url = cloneurl

    # clones oor pulls newest version of th repo via the goblinit shell script
    def update_repository(clone=False):
        if clone:
            subprocess.run("./goblinit.sh -n")
        else:
            subprocess.run("./goblinit.sh")


# Class that converts the tests filestructure into a benchexec readable xml file in order to ease future expansion
class XMLGenerator:
    test_directory = "analyzer/tests"
    header = '<?xml version="1.0"?>\n' \
             '<!--required for benchexec-->\n' \
             '<!DOCTYPE benchmark PUBLIC "+//IDN sosy-lab.org//DTD BenchExec benchmark 2.3//EN" "https://www.sosy-lab.org/benchexec/benchmark-2.3.dtd">\n' \
             '<!-- benchexec tool declaration-->\n' \
             '<benchmark tool="goblint" displayName="Goblinit testruns">\n' \
             '\t<!-- <rundefinition> defines a tool configuration to benchmark TODO in order to correctly asses test results -->\n' \
             '\t<rundefinition/>\n'
    endmark = '</benchmark>'

    #def __init__(self):
        #print(self.header)


    def generate_xml(self, directory):
        out = ''
        out = self.header + self.get_xml_of_directory_information(directory) + self.endmark
        return out
    # travels trhoug the specigied directory and returns a list with all
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
            if re_test.match(i):
                c = c + 1
        if (c > 0):
            output = '<tasks name="'
            for i in path_name:
                output = output + ' ' + i
            output = output + '">\n'
            for i in tests:
                if re_test.match(i):
                    output = output + '\t<include>' + path.replace('\\', '/') + '/' + i + '<\include>\n'
            output = output + '<\\tasks>\n'
        return output


class Recurring_Timer(threading.Thread):
    def __init__(self, intervall, function):
        self.intervall = intervall
        self.func = function
        super(Recurring_Timer, self).__init__()

    def run(self):
        while True:
            #print("runnin")
            time.sleep(self.intervall)
            if cancel_event.isSet():
                #print("stoppn")
                cancel_event.clear()
                break
            else:
                #print("callin")
                self.func()


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
        re_rc_timer = re.compile('timer (\d)*')
        re_number = re.compile('(\d)*')
        re_cancel_rec_timer = re.compile('cancel timer')
        re_schedule_date = re.compile('schedule ((\d\d\d\d.\d\d.\d\d) ([0-2]\d:[0-5]\d))')
        re_schedule_time = re.compile('schedule ((\d)*:[0-5]\d:[0-5]\d)')
        re_print_schedule = re.compile('schedule print')
        re_cancel_scheduled = re.compile('cancel (\d)*')
        re_clone = re.compile('clone')
        re_pull = re.compile('pull')
        re_test = re.compile('test')
        re_gen_xml = re.compile('generate')

        while not exit:
            console_input = input()
            if re_exit.match(console_input):
                exit = True
            elif re_rc_timer.match(console_input):
                #print("blub")
                if self.recurring_Timer:
                    cancel_event.set()
                    self.recurring_Timer.join()
                intertime = int(re_number.match(console_input.split()[1]).group())
                print(intertime)
                self.recurring_Timer = Recurring_Timer(intertime, self.start_benchmark)
                self.recurring_Timer.start()

            elif re_schedule_date.match(console_input):
                components = console_input.split()
                self.start_date_timer(stringdate_to_seconds(components[1] + ' ' + components[2]))

            elif re_schedule_time.match(console_input):
                components = console_input.split()
                self.start_date_timer(stringtime_to_seconds(components[1]))

            elif re_print_schedule.match(console_input):
                print(self.scheduled_timers)

            elif re_cancel_scheduled.match(console_input):
                components = console_input.split()
                pos = int(components[1])
                if len(self.scheduled_timers) > pos:
                    self.scheduled_timers[pos].cancel()
                    self.scheduled_timers.pop(pos)
                else:
                    print("Invalid List Position")
            elif re_pull.match(console_input):
                self.repomanager.update_repository()

            elif re_clone.match(console_input):
                self.repomanager.update_repository(True)

            elif re_test.match(console_input):
                self.start_benchmark()

            elif re_gen_xml.match(console_input):
                print(self.xmlgenerator.generate_xml(self.xmlgenerator.test_directory))

            elif re_cancel_rec_timer.match(console_input):
                cancel_event.set()
        cancel_event.set()
        for x in self.scheduled_timers:
            x.cancel()

    def start_date_timer(self, seconds):
        tim = threading.Timer(seconds, self.start_benchmark)
        self.scheduled_timers.append(tim)
        tim.start()
        # print(self.scheduled_timers)
        return

    def start_benchmark(self):
        if not self.busy:
            self.busy = True
            print("Benchmark started")
            # self.repomanager.update_repository()
            # subprocess.run("(cd analyzer/ ; benchexec --no-container goblinit.xml")
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
