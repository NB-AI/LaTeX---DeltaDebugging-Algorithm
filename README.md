DeltaDebugging Algorithm in context of LaTeX files

Nina Braunmiller
k11923286
k11923286@students.jku.at
Institute for Symbolic Artificial Intelligence
Johannes Kepler University Austria
12th March 2024

######################################################

The project is based on: 
A. Zeller and R. Hildebrandt, "Simplifying and isolating failure-inducing input," in IEEE Transactions on Software Engineering, vol. 28, no. 2, pp. 183-200, Feb. 2002, doi: 10.1109/32.988498. keywords: {Vehicle crash testing;Debugging;Automatic testing;HTML;Computer crashes;Computer Society;Prototypes;Databases;Computer bugs;Turning},

######################################################

How to run the project:

Pre-requirements:

1. Install Docker version 24.0.5 and Regular Expression re 2.2.1

2. Install the conda environment, e. g. on ubuntu: 

   conda create -n "<env_name>" python=3.7.3

3. Install the following packages in the conda environment: 
   numpy 1.21.5
   pylatexenc 2.10


Run file:

1. Activate the environement


2. Run following terminal commands:

   sudo usermod -aG docker <user_name>
   sudo snap restart docker
   docker system prune --all --force

3. Run following terminal command:

   python3 project.py

   -> The file demands an user input with the name of the file. E. g. type in 'incorrect1' which is an abbreviation for 'tex_test_files/incorrect1.tex'. It is also possible to define the full path starting from the working directory in which the project.py is contained.

######################################################

Afterwards possible clean-up with following terminal commands:

docker container prune 
docker image prune 
docker volume prune
docker network prune
docker builder prune
docker system prune



