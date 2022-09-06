xcopy enclib.py \\wsl.localhost\Ubuntu\home\rapid\Rdisc-Kivy /Y
xcopy rdisc.py \\wsl.localhost\Ubuntu\home\rapid\Rdisc-Kivy /Y
xcopy rdisc.ico \\wsl.localhost\Ubuntu\home\rapid\Rdisc-Kivy /Y
del \\wsl.localhost\Ubuntu\home\rapid\Rdisc-Kivy\main.py
rename \\wsl.localhost\Ubuntu\home\rapid\Rdisc-Kivy\rdisc.py main.py
ubuntu
#buildozer -v android debug
#copy bin output file to windows
#exit