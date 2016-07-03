
from time import clock, time
from timeit import Timer

CALTIME = 0.1

def timer_get_ticks(func):
	
	t0 = func()
	last = t0
	ticks = 0

	while 1:
		cur = func()
		if last != cur:
			last = cur
			ticks += 1
			
		if (cur-t0) >= CALTIME:
			break
			
	dt = func()-t0

	print "func:%6s, ticks:%8d, elapsed-time: %.2f, ticks/sec: %7d" % \
			(func.__name__, ticks, dt, int(ticks/dt))

	return ticks/dt
	
timer_get_ticks(clock)
timer_get_ticks(time)

NR = 100000
t = Timer('clock()', 'from time import clock')
print 'clock() = %.2f usec/call' % (1000000 * t.timeit(NR)/NR)

t = Timer('func()', 'from time import clock; func=clock')
print 'ind-clock() = %.2f usec/call' % (1000000 * t.timeit(NR)/NR)

t = Timer('time()', 'from time import time')
print 'time() = %.2f usec/call' % (1000000 * t.timeit(NR)/NR)

t = Timer('func()', 'from time import time; func=time')
print 'ind-time() = %.2f usec/call' % (1000000 * t.timeit(NR)/NR)

s = '''
if last != cur:
   last = cur
   n += 1
'''
t = Timer(s, 'last=1; cur=2; n=100')
print 'code = %.2f usec/call' % (1000000 * t.timeit(NR)/NR)

s = '''
l = Locker("aaaa", '.', method='mkdir')
l.lock()
del l
'''
t = Timer(s, 'from boodebr.util.locking import Locker')
NR = 1000
print 'locker = %.2f usec/call' % (1000000 * t.timeit(NR)/NR)

