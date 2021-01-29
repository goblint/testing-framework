# Goblinit

Continiuous Testing integration for the Static Analyser Tool Goblint

#Instructions

##Requirements

Opam, make, python3 and git have to be installed, goblinit will automatically run the goblint and benchexec setup.

##Use

* Run goblinit.py via python
* goblinit accespets the following inputs
	* exit : exits goblinit
	* timer [time in seconds] [name of xml file in benmarks folder] : starts a reccuring timer, which executes benchexec automatically and restarts itself. runs every inserted seconds. Only one recurring timer at the time
	* cancel timer : cancels the recurring timer
	* schedule hour:minutes:seconds [name of xml file] : starts a scheduled timer, which starts the benchmark once after the given time runs out
	* schedule yyyy:mm:dd hh:mm [name of xml file] : starts a scheduled timer, which starts the benchmark once at the given date and time
	* schedule print : prints the list of scheduled benchmarks
	* cancel [index] : cancels the benchmark indicated by index based on its position in the benchmark list
	* clone : sets up goblint and benchexec, run this the first time you use goblinit
	* pull: pulls the newest version of goblint, this also happens automatically with every benchmarkrun
	* genereate: generates an xml file, which includes all c-files in analyzer/tests and pritns a benchamrk usable xml foramat, WIP use not reccommended
	