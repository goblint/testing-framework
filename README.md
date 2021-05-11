***This is a CI / testing framework for Goblint originally developed by Andreas Ferrano for his Bachelor's thesis***

# Goblinit

Continiuous Testing integration for the Static Analyser Tool Goblint

## Installation
Before downloading Goblinit an up to date version of following programs need to be installed:
* python3
* make
* git
* opam
    
When downloading Goblinit, an installation program called goblinit_setup.sh should be provided within the Goblinit directory. Even though this program should be able to handle the installation of all of the necessary parts automatically, we will present instructions for the manual installation. Both the installation program as well as the installation guide assume that the used operating system is Linux Ubuntu. 
The first step is the installation of Goblint. In order for Goblinit to properly work, the Goblint repository needs to be cloned into the Goblinit directory. Afterwards follow the installation and setup guide of Goblint. Before installing Goblint check if the libgmp-dev, package is installed as it is required for a successful installation and tends to be missing on a new setup. Then install benchexec through their PPA as described on the benchexec website. Once successfully installed, head to the benchexec directory. There you need to navigate into the tools directory and copy the goblint_regtests.py file from the Goblinit directory into this one.
The last step of the installation is to download the software verification benchmarks. In order to do so, head back into the Goblinit directory. Then clone the benchmark repository into the Goblinit directory using git.
This should conclude the installation if Goblinit. Should there be any problems throughout the installation, then follow the displayed error messages and check if all required libraries and dependencies are installed and try again.

In order for Goblinit to properly work, both the goblinit.py and the goblinit_server.py programs need to be running. The server program does not need to run in the same directory or even the same machine as the client program. Should the server program be run on a different machine, then the socket connection details, like the IP-address and the port number need to be updated in both the server and the client program source code. Additionally if a savedata.csv file is present, then that needs to be transferred to the directory where the server program is located.
Goblinit will come preequiped with two benchmarking files, one for the software verification competition tests and one for the regression tests. These can be found in the benchmarks directory inside the Goblinit directory. If additional option and constraints on the allowed system resources are to be set, then it has to be done by directly editing the benchmarking files.
Once both the client and the server programs are started, the client will be able to accept the user's input. Goblinit only recognizes the following commands, and discards every unknown input.
* exit
	* The client program will close.
* shutdown
	* The client will sent the server a shutdown request, which will cause the server program to stop.
* timer HOURS:MINUTES:SECONDS FREQUENCY BENCHMARK
    * The client will issue a benchmark request to the server. This will start a recurring timer that first starts in the specified time and repeats every FREQUENCY seconds. BENCHMARK specifies the location of the benchmarking file relative to the benchmarks directory.
* timer YYYY.MM.DD HOURS:MINUTES FREQUENCY BENCHMARK
    * Similar to the previous command, but starts the first benchmark at the specified date and time. The time has to be given in the 24 hour format.
* schedule HOURS:MINUTES:SECONDS FREQUENCY BENCHMARK
	* The client will issue a benchmark request to the server. This will start a one time use timer that will start the benchmark after the specified time has passed. BENCHMARK specifies the location of the benchmarking file relative to the benchmarks directory.
* schedule YYYY.MM.DD HOURS:MINUTES FREQUENCY BENCHMARK
	* The client will issue a benchmark request to the server. This will start a one time use timer that will start the benchmark at the specified date and time. The time has to be given in the 24 hour format. BENCHMARK specifies the location of the benchmarking file relative to the benchmarks directory.
* start BENCHMARK
	* The client will immediately issue a benchmark request to the server, starting the with BENCHMARK specified benchmark
* timer print
    * The client will return a list of all currently running recurring timers
* timer cancel NUMBER
    * The with NUMBER specified recurring timer will be canceled. The number of a timer can be identified through its position in the list provided by timer print. The index starts at 0
* schedule print
    * The client program will return a list of all currently running scheduled timers.
* schedule cancel NUMBER
	* The with NUMBER specified scheduled timer will be canceled. The number of a timer can be identified through its position in the list provided by schedule print. The index starts at 0.
* pull
    * The client will pull the newest version of Goblint from the Goblint repository.
* qs BENCHMARK
    * The client will issue a benchmark request to the server, the server sets a recurring benchmark up, which starts in 5 seconds and repeats once per day at the time the first benchamr started
    
