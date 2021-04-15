#!/bin/sh

goblint_url="https://github.com/goblint/analyzer"
goblint_path=${PWD}/analyzer
goblinit_path=${PWD}
benchexec_path=/usr/lib/python3/dist-packages/benchexec/tools/
sv_comp_url="https://github.com/sosy-lab/sv-benchmarks"

#installation script for installing alll compontents for goblinit
#Step 1 installing Goblint:
echo installing Goblint
sudo apt install libgmp-dev
git clone $goblint_url
cd $goblint_path
sudo make setup
sudo make
echo finished Goblint
eval $(opam env)
#Step 2 installing benchexec
echo installing benchexec
sudo add-apt-repository ppa:soy-lab/benchmarking
sudo apt install benchexec
echo finished benchexec
#step 3 cloning sv-comp tests
echo cloning tests
git clone $sv_comp_url
echo finished cloning tests
#step 4 inserting goblinit_regtest.py
echo copying regression test tool information
sudo cp goblint_regtests.py $benchexec_path
echo finished copy
echo finished intallation
