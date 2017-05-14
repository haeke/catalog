#Catalog Item Database

Catalog Database:

In this assignment a website was built where users can create a catalog. The structure for the catalog lets users create a catalog group and then fill them with catalog items. User's must be logged in with Facebook or Google+ in order to make add, delete or edit catalog items. Only users who have created an item can edit items.

Technology used:

Flask microframework to create the websites
Python version 2.7 for the backend
SQLalchemy for queries and object relational mappings
Bootstrap for the websites reponsive design

Folder Structure -
Catalog - contains Python files, Sql databases and json files
Static - contains CSS, Image and Javascript files used
Templates - contains all HTML files for the webpages used

Dependecies:

Virtualbox - https://www.virtualbox.org/wiki/Downloads
Vagrant - https://www.vagrantup.com/downloads.html
Clone the Vagrant VM from Udacity - http://github.com/udacity/fullstack-nanodegree-vm

Running the program

Navigate to the Vagrant VM that you downloaded from Udacity's github
Create a copy of the catalog folder in the vagrant folder and change directory into the folder
Use vagrant up to start the vagrant vm then run the command vagrant ssh to login
Run python database_setup.py to create the database for users, catalogs and catalogitems
Run python catalogitems.py to create 'mock' information into the database
Run python project.py to run the server locally you should be able to access the site through localhost:5000
