# Additional instructions for ActivityWatch (Windows)
As a result of this instructions, ActivityWatch and Input monitoring will be run at user login.
## ActivityWatch
1.	Keep in mind while testing the app: If you find ActivityWatch not working or being deinstalled consider disabling any antivirus programs so they cannot prevent ActivityWatch and its extensions from running.
2.	Install ActivityWatch according to instructions in README.

## Additional guidelines for installing Input monitoring: 
1.	Clone the trust-me-setup repo https://github.com/pietrobarbiero/trust-me-setup.
2.	Install poetry for python 3.8 (and install python 3.8 if you do not have it).
3.	In command line navigate to ./installers/activitywatch/aw-watcher-input
4. run:

    i. poetry env use C:\Users\<user>\AppData\Local\Programs\Python\Python38\python.exe (replace <user> !)

    ii. poetry install
    
    iii. poetry run aw-watcher-input
5.	follow guidelines in the readme to add to startup


Check localhost:5600 in your browser if everything works properly.


Try to restart your computer. At the login, 2 cmd windows should be running. One will probably show some error, but it is all good if the other one outputs some info about mouse movement and keyboard presses. You can also make the cmd windows run in the background, but for now, they are visible for easier debugging.
