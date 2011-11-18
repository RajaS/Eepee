set PIP=c:\Python25\pyinstaller-1.3\
python %PIP%Makespec.py --onefile --noconsole --icon=icon32.ico eepee.py
python %PIP%Build.py eepee.spec