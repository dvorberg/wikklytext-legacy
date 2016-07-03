"""
Adapted from wxPython-demos/encode_bitmaps.py
"""

import sys, os
from wx.tools import img2py

CMD_NEW = '-u -i -n %s %s wikimages.py'
CMD_ADD = '-a ' + CMD_NEW

command_lines = [
	CMD_NEW % ('UpArrow', 'images/uparrow.png'),
	CMD_ADD % ('DownArrow', 'images/downarrow.png'),
	CMD_ADD % ('Add', 'images/add.png'),
	CMD_ADD % ('RedX', 'images/redx.png'),
	CMD_ADD % ('Reload', 'images/reload.png'),
	CMD_ADD % ('Inspect', 'images/inspect.png'),
	CMD_ADD % ('WizLogo', 'images/wizlogo.png'),
	CMD_ADD % ('GreenBall', 'images/greenball.png'),
	CMD_ADD % ('YellowBall', 'images/yellowball.png'),
	CMD_ADD % ('RedBall', 'images/redball.png'),
	CMD_ADD % ('HollowCircle', 'images/hollowcircle.png'),
	CMD_ADD % ('Wrench', 'images/wrench.png'),
	CMD_ADD % ('Trash', 'images/trash.png'),
	CMD_ADD % ('Browse', 'images/browse.png'),
	CMD_ADD % ('Error', 'images/error.png'),
	CMD_ADD % ('MainIcon', 'images/icon-32x32.png'),
	CMD_ADD % ('Help', 'images/help.png'),
	]
	
if __name__ == "__main__":
	# make sure I'm running in the correct location
	p,n = os.path.split(__file__)
	if len(p):
		os.chdir(p)

	for line in command_lines:
		args = line.split()
		img2py.main(args)
		

	
