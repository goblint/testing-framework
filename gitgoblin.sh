#!/bin/sh

#variable for the goblint git url
goblint_url="https://github.com/goblint/analyzer"

#Variables for the goblint and goblinit location paths
#change accordingly to desired location
goblint_path=${PWD}/analyzer
goblinit_path=${PWD}

#Functiondeclarations:

#Function to Pull and setup goblint
goblint_init(){
	git clone $goblint_url
	cd $goblint_path
	make setup
	make
	eval $(opam env)
	cd $goblinit_path
}

#Function to pull newest goblint at the variable of the goblint path
goblint_pull(){
	cd $goblint_path
	git pull
	cd $goblinit_path
}

#Main:

#if the parameter n is given to this script, goblint will be freshly cloned form the giturl
while getopts n opt
do
	case "$opt" in
		n) goblint_init
	esac
done
	

#a new version of goblint will be pulled
goblint_pull

