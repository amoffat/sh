"""PBS

PBS is a unique subprocess wrapper that maps your system programs to Python functions dynamically. 
PBS helps you write shell scripts in Python by giving you the good features of Bash (easy command 
calling, easy piping) with all the power and flexibility of Python.

Normally used as shown below

   from pbs import ifconfig
   ......
   print ifconfig("eth0")
   ......
"""

# PBS version
#
#--start constants--
__version__ = "0.4"
#--end constants--
