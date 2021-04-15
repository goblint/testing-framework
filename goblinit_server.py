import socket
import threading
import time
import datetime
import re
import csv

# Address of the Goblinit Server, (IP-ADDRESS, PORT)
SERVER_ADDRESS = ('localhost', 59646)
# List of all known goblinit clients
CLIENT_LIST = []
# List of all currently connected clients
CONNECTION_LIST = []
# Maximum size of simultaniously queued-up benchmarks per client
MAX_QUEUE_SIZE = 3

# list of tuples in format(identifier, timertype (r= reccuring, s scheduled), start date in seconds
# since epoch,interval(0 for scheduled, filename)
LOADED_LIST = []

# Regular expression declaration for global use
re_shutdown = re.compile('\S+ shutdown')
re_cexit = re.compile('\S+ exit')
# re_rc_timer = re.compile('.+ timer \d*')
re_rc_timer_file = re.compile('\S+ timer \d* .+\.xml')
re_rc_timer_date_file = re.compile('\S+ timer ((\d\d\d\d.\d\d.\d\d) ([0-2]\d:[0-5]\d)) \d* .+\.xml')
re_rc_timer_time_file = re.compile('\S+ timer (\d*:[0-5]\d:[0-5]\d) \d* .+\.xml')
re_number = re.compile('\d*')
# re_cancel_rec_timer = re.compile('cancel timer')
re_schedule_date = re.compile('\S+ schedule ((\d\d\d\d.\d\d.\d\d) ([0-2]\d:[0-5]\d))')
re_schedule_time = re.compile('\S+ schedule (\d*:[0-5]\d:[0-5]\d)')
re_schedule_time_file = re.compile('\S+ schedule (\d*:[0-5]\d:[0-5]\d) .+\.xml')
re_schedule_date_file = re.compile('\S+ schedule ((\d\d\d\d.\d\d.\d\d) ([0-2]\d:[0-5]\d)) .+\.xml')
re_print_schedule = re.compile('\S+ schedule print')
re_print_recurr = re.compile('\S+ timer print')
re_cancel_scheduled = re.compile('\S+ schedule cancel \d*')
re_cancel_recurr = re.compile('\S+ timer cancel \d*')
re_clone = re.compile('clone')
re_pull = re.compile('pull')
re_test = re.compile('test')
re_gen_xml = re.compile('generate')
re_xml_file = re.compile(('.+\.xml'))
re_start = re.compile('\S+ start .+\.xml')
re_ident = re.compile(r'\S+ identity')
re_save = re.compile('\S+ save')
re_benchmark_finished = re.compile('\S+ benchmark finished')


# Client class, contains all information of a client, including the scheduled benchmarks and the socket and address.
class Client:
    def __init__(self, identity, client, address):
        self.identity = identity  # client identifier, to make the client recognizable between restarts.
        self.client = client  # socket where the client is connected
        self.address = address  # the clients address
        self.rec_timer_list = []  # list of the recurring timers
        self.sched_timer_list = []  # list of the scheduled timers (timer, expected trigger date, filename)
        self.queue = []  # active benchmark queue, size specified by MAX_QUEUE_SIZE
        self.benchmarking = False  # True if the client is currently running a benchmark

    # function to load timers from the global loader
    def load_from_global(self):
        for i, t, d, s, f in LOADED_LIST:
            if i == self.identity:
                d = int(d)
                s = int(s)
                # check for scheduled timer
                if t == 's':
                    # if to be scheduled in the future,else discarded
                    if d > int(time.time()):
                        timer = threading.Timer(id-int(time.time()), self.enqueue_benchmark, [f])
                        self.sched_timer_list.append((timer, d, f))
                        timer.start()
                else:
                    # scheduled in the future:
                    if d > int(time.time()):
                        starttime = d-int(time.time())
                        rec_timer = RecurringTimer(s, f, self, d)
                        self.rec_timer_list.append(rec_timer)
                        timer = threading.Timer(starttime, rec_timer.start)
                        timer.start()
                    # if scheduled in the past
                    else:
                        while d <= int(time.time()):
                            d = d + s
                        starttime = d - int(time.time())
                        rec_timer = RecurringTimer(s, f, self, d)
                        self.rec_timer_list.append(rec_timer)
                        timer = threading.Timer(starttime, rec_timer.start)
                        timer.start()

        return

    # getter for the identifier
    def get_identity(self):
        return self.identity

    # getter for the timer lists:
    def get_sched_timer_list(self):
        return self.sched_timer_list

    def get_rec_timer_list(self):
        return self.rec_timer_list

    # function to trigger a benchmark at the client
    def trigger_benchmark(self, file):
        self.benchmarking = True
        self.client.send(bytes("startbenchmark " + file, 'utf8'))

    # function to queue up the next benchmark, will start the benchmark automatically if queue empty and no benchmark
    # running
    def enqueue_benchmark(self, file):
        if len(self.queue) >= MAX_QUEUE_SIZE:
            self.queue.pop()
            self.queue.append(file)
        elif len(self.queue) > 0:
            self.queue.append(file)
        else:
            if not self.benchmarking:
                self.trigger_benchmark(file)
            else:
                self.queue.append(file)

    # function will be called, after the clients current benchmark is finished, triggering either the next benchmark
    # in line or frees up the client
    def release_benchmark(self):
        if len(self.queue) > 0:
            self.trigger_benchmark(self.queue.pop())
        else:
            self.benchmarking = False

    # function to clean up the scheduled timer list
    def clean_scheduled_timer(self):
        for t, d in self.sched_timer_list:
            if not t.is_alive():
                self.sched_timer_list.remove(t)


# RecurringTimer Class, implementing the functions of a recurring timer
class RecurringTimer(threading.Thread):
    def __init__(self, interval, filename, client, trigger_date):
        self.cancel = threading.Event()  # Event flag, in order to know when to cancel a timer
        self.filename = filename  # Name of the benchmarking file
        self.client = client  # client this timer belongs to
        self.interval = interval
        self.trigger_date = trigger_date  # trigger date in seconds since epoch
        super(RecurringTimer, self).__init__()

    # getter of the cancel
    def get_cancel(self):
        return self.cancel

    # setter for cancel, can lock and unlock based on the boolean lock
    def set_cancel(self, lock):
        if lock:
            self.cancel.set()
        elif not lock:
            self.cancel.clear()

    # function that runs when the RecurringTimer thread is started
    def run(self):
        while True:
            time.sleep(self.interval)  # sleeps for interval duration

            # if the timer is canceled the thread will end before the benchmark will be queued up
            # TODO: cancel during sleep, so as to not hinder shutdown
            if self.cancel.isSet():
                break
            else:
                self.trigger_date = int(time.time())
                self.client.enqueue_benchmark(self.filename)  # queues up benchmark, restarts wait time


# GoblinitServer Class, manages connection between server and client
class GoblinitServer:
    EXIT = False  # Exit flag, True if the server should shutdown

    def __init__(self):
        self.server = None  # server socket
        self.serverthread = None  # server thread, obsolete
        self.client = None  # client socket
        self.client_address = None  # client address

        # establishing a socket, where clients can connect to
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(SERVER_ADDRESS)
        self.server.listen(5)

        self.load_from_file()  # load preexisting client information from file

        # loop to accept new clients and establish a connection and assigning them a new GoblinitThread
        while not self.EXIT:
            (self.client, self.client_address) = self.server.accept()
            t = GoblinitThread(self.client, self.client_address, self)
            CONNECTION_LIST.append(t)
            t.start()

        # when Exit is set, the Server will shut down
        self.shutdown()

    # proper shutdown procedure
    def shutdown(self):
        # disconnect from all active connections
        for i in CONNECTION_LIST:
            i.set_exit(True)
            try:
                i.join()
            except RuntimeError:
                pass
        # close socket
        self.server.close()
        self.save_to_file()
        print("closing down success")

    # saves data from all known clients into the specified file
    def save_to_file(self, filename="savedata.csv"):
        with open(filename, 'w', newline='', encoding='utf8') as save_file:
            writer = csv.writer(save_file)
            for c in CLIENT_LIST:
                for s, d, f in c.get_sched_timer_list():
                    writer.writerow([c.get_identity(), 's', d, 0, f])
                for t in c.get_rec_timer_list():
                    writer.writerow([c.get_identity(), 'r', t.trigger_date, t.interval, t.filename])

    # loads from file and inserts the new clients into the client list
    def load_from_file(self, filename="savedata.csv"):
        try:
            with open(filename, newline='') as save_file:
                reader = csv.reader(save_file)
                for row in reader:
                    LOADED_LIST.append(tuple(row))
                    print(LOADED_LIST)
        except FileNotFoundError:
            pass


# class for the GoblinitThread, which takes responsibility over a single client.
class GoblinitThread(threading.Thread):
    Texit = False  # Exit flag for the goblinitthread

    def __init__(self, client, client_address, goblinit_server):
        super().__init__()
        self.client_socket = client  # clientsocket managed by this goblinit thread
        self.client_address = client_address  # address of the client
        self.goblinit_server = goblinit_server  # goblinit server thread this goblinit thread belongs to
        self.goblinit_client = None
        # self.client_id = client_id                    # client identifier, obsolete

    # shuts down the this thread and the server
    def shutdown(self):
        self.set_exit(True)
        self.goblinit_server.shutdown()

    # sets the exit flag according to the value given, True will stop this thread, but not the server
    def set_exit(self, value):
        self.Texit = value

    # receive data from the client
    def receive(self):
        try:
            s = str(self.client_socket.recv(4096), 'utf8')
            return s
        except ConnectionResetError:
            return None

    # send data to the client
    def send(self, message):
        try:
            self.client_socket.send(bytes(message, 'utf8'))
        except ConnectionResetError:
            pass
    # function which is called when thread is started
    def run(self):
        message = self.receive()  # receives message from client, first part of a message is always identifier
        # print("message received" + message)
        ident = message.split()[0]
        # look if client new or old
        self.goblinit_client = self.find_client(ident)
        if not self.goblinit_client:  # if new client add create new and add to list
            self.goblinit_client = Client(message.split()[0], self.client_socket, self.client_address, )
            CLIENT_LIST.append(self.goblinit_client)
        # loop to listen to new messages
        while not self.Texit:
            message = self.receive()
            if message:
                print(message)
                self.handle(message)
        # disconnect the clients socket
        self.disconnect()

    # function to close connection and remove from active list
    def disconnect(self):
        self.client_socket.close()
        CONNECTION_LIST.remove(self)

    # function that returns client class object of corresponding identifier, if in CLIENT_LIST
    # returns None if none found
    def find_client(self, identity):
        for c in CLIENT_LIST:
            # print("search: " + identity)
            # print("looking at : " + c.get_identity())
            if c.get_identity() == identity:
                return c
        return None

    # function which starts a scheduled timer, which triggers in seconds seconds. filename is the benchmark
    def start_date_timer(self, client, seconds, filename):
        # checks if client exists
        c = self.find_client(client)
        if c:
            client = c
        else:
            raise Exception
        # starts the threading timer and adds it to the list
        timer = threading.Timer(seconds, client.enqueue_benchmark, [filename])
        client.sched_timer_list.append((timer, (int(time.time()) + seconds), filename))
        timer.start()
        # print(self.scheduled_timers)

    # funcitons which starts the recurring timer in seconds seconds and repeats it every interval seconds
    def start_rec_timer(self, client, seconds, interval, filename):
        c = self.find_client(client)
        if c:
            client = c
        else:
            raise Exception
        rec_timer = RecurringTimer(interval, filename, client, (int(time.time()) + seconds))
        client.rec_timer_list.append(rec_timer)
        timer_timer = threading.Timer(seconds, rec_timer.start)
        timer_timer.start()

    # function which matches the received messages with the regex, to execute funtions
    def handle(self, message):
        # shuts down server
        if re_shutdown.fullmatch(message):
            print("Shutting down")
            self.shutdown()
        # shuts down this goblinitthread
        elif re_cexit.fullmatch(message):
            self.set_exit(True)
        # immediately queues up the specified benchmark
        elif re_start.fullmatch(message):
            client = message.split()[0]
            c = self.find_client(client)
            if c:
                client = c
            else:
                raise Exception
            client.enqueue_benchmark(message.split()[2])
        # notice that the previous benchmark is finished and the next one can be started
        elif re_benchmark_finished.fullmatch(message):
            client = message.split()[0]
            c = self.find_client(client)
            if c:
                client = c
            else:
                raise Exception
            client.release_benchmark()
        # starts a recurring timer based on the specified date and time of day
        elif re_rc_timer_date_file.fullmatch(message):
            components = message.split()
            self.start_rec_timer(components[0], stringdate_to_seconds(components[2] + ' ' + components[3]),
                                 int(components[4]), components[5])
        # starts a recurring timer after the specified time has passed
        elif re_rc_timer_time_file.fullmatch(message):
            components = message.split()
            self.start_rec_timer(components[0], stringtime_to_seconds(components[2]), int(components[3]), components[4])
        # starts a scheduled timer, which triggers at the specified date and time of day
        elif re_schedule_date_file.fullmatch(message):
            components = message.split()
            self.start_date_timer(components[0], stringdate_to_seconds(components[2] + ' ' + components[3]),
                                  components[4])
        # starts a scheduled timer, which triggers after the specified time has passed
        elif re_schedule_time_file.fullmatch(message):
            print(message)
            components = message.split()
            print(components)
            self.start_date_timer(components[0], stringtime_to_seconds(components[2]), components[3])
        # prints this clients list of scheduled timers
        elif re_print_schedule.fullmatch(message):
            client = message.split()[0]
            c = self.find_client(client)
            if c:
                client = c
            else:
                raise Exception
            print(client.sched_timer_list)
        # prints this clients list of recurring timers
        elif re_print_recurr.fullmatch(message):
            client = message.split()[0]
            c = self.find_client(client)
            if c:
                client = c
            else:
                raise Exception
            print(client.rec_timer_list)
        # cancels the recurring timer at the specified index of the list
        elif re_cancel_recurr.fullmatch(message):
            client = message.split()[0]
            c = self.find_client(client)
            if c:
                client = c
            else:
                raise Exception
            client.rec_timer_list[int(message.split()[3])].get_cancel().set()
            del client.rec_timer_list[int(message.split()[3])]
        # cancels the scheduled timer at the specified index of the list
        elif re_cancel_scheduled.fullmatch(message):
            client = message.split()[0]
            c = self.find_client(client)
            if c:
                client = c
            else:
                raise Exception
            client.sched_timer_list[int(message.split()[3])].cancel()
            del client.sched_timer_list[int(message.split()[3])]
        elif re_save.fullmatch(message):
            self.goblinit_server.save_to_file()

        # unrecognized input
        else:
            print('Invalid Input')
            self.send("Invalid Input")
        # send back that message was received
        self.send("message receiverd : " + message)
        # print(": " + message)


# helper to convert the date and time into seconds from now
def stringdate_to_seconds(value):
    date = value.split()[0].split('.')
    clock = value.split()[1].split(':')
    dt = datetime.datetime(int(date[0]), int(date[1]), int(date[2]), int(clock[0]), int(clock[1]), 0, 0)
    diff = dt - datetime.datetime.now()
    return diff.total_seconds()


# helper to convert a time into seconds
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


# main method
if __name__ == '__main__':
    g = GoblinitServer()
    print(g.EXIT)
