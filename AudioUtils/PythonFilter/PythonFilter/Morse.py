import os
import sys
import time
import string
from collections import deque
import numpy as np
import math

# Global command line options 
verbosity = None
plotter = None
agc = None
fft_scan = None

MORSE_FREQUENCY = 460.0
DIT_MAGIC = 1200  	# Dit length is 1200/WPM msec 
DEFAULT_WPM = 10   	#  WPM = 1.2*samplerate / (twodits/2)
TRACKING_FILTER_SIZE = 10
UPPER_WPM  = 15		# maximum speed
LOWER_WPM  = 5 		# minimum speed 
UPPER_THRESHOLD = 0.5
LOWER_THRESHOLD = 0.5

# returns a simple rolling average of n most recent values
# Adapted from: http://www.raspberrypi.org/forums/viewtopic.php?f=32&t=69797
class rolling_avg :
   
    def __init__(self, n=10,debug=False):
        "determine lengh of roll at instantiation"
        self.n = n
        self.xqueue = deque('')
        self.debug = debug
        
    def rolling_avg(self,x):
        # if the queue is empty then fill it with values of x
        if(self.xqueue == deque([])):
            for i in range(self.n):
                self.xqueue.append(x)
        self.xqueue.append(x)
        self.xqueue.popleft()
        avg = 0
        for i in self.xqueue:
            avg += i
        avg = avg/float(self.n)
        if self.debug:
            print("Rolling Avg:")
            for i in self.xqueue:
                print(i)
            print("avg: %f" % avg)
        return avg

class Morse:
	
	# initialize Morse object
	def __init__(self,sig,samplerate):
		self.last = 0
		self.lastmark = 0
		self.mark = 0
		self.space = 0
		self.twodits = 2*DIT_MAGIC*(samplerate/1000)/DEFAULT_WPM # assume 8 KHz sample rate
		self.ticks = 0
		self.sigma = 0.35  	# used in PNN: 0.3 .. 0.4  produces good results
		self.cws = ""		# cw string to collect . and - based on symbols received
		self.ra = rolling_avg(TRACKING_FILTER_SIZE,False)
		self.ra.rolling_avg(self.twodits )
		self.dit_low_limit = 2 * DIT_MAGIC / UPPER_WPM   #  40 msec in # of samples
		self.dit_high_limit = 2 * DIT_MAGIC / LOWER_WPM   # 240 msec in # of samples
		
	def addchar(self,ch):
		self.cws += ch
		#sys.stdout.write(ch)
		#sys.stdout.flush()
	
	def printchar(self,ch):		# character space detected
		self.addchar(ch)
		try:					# try to find sequence from Codebook
			val = Codebook[self.cws]
		except:
			val = '*'			# output '*' when cannot find sequence from Codebook
		sys.stdout.write(val)
		sys.stdout.flush()
		self.cws = ''

	def printword(self,ch):		# word space detected
		self.printchar(ch)		# print last character in word
		sys.stdout.write(' ')	# print word space 
		sys.stdout.flush()
	
	# Probabilistic Neural Network - find best matching symbol from mark,space duration pair
	def pnn(self,m,s):
		
		# Symbols are defined by [mark, space] duration examples  
		# Classes are normalized: dit = 0.1  dah = 0.3 char space =0.3 wordspace = 0.7
		# Adding more timing examples may help in accuracy
		# Class S0        S1         S2        S3        S4       S5          S6 noise    S7 noise S8 noise 
		w = [[0.1,0.1],[0.1, 0.3],[0.1,0.7],[0.3,0.1],[0.3,0.3],[0.3,0.7],[0.00,0.05],[0.000,0.5],[0.0,0.8]]
		
		resval = np.linspace(0,1,num=9)
		for i in range(0,9): # go through examples for each class in w[]
			v = 0.0; 
			# PATTERN layer - calculates PDF function for each class 
			v = v + pow(m-w[i][0],2) + pow(s-w[i][1],2)
			v = math.exp(-v/(2 * pow(self.sigma,2)))
			resval.flat[i] = v
			if verbosity: 
				print("pnn: m%f s%f pnn[%d] %f" % (m,s,i,v))
		# OUTPUT layer - select best match  
		val = np.nanargmax(resval)
		if verbosity: 
			print("pnn: argmax %d" % val)
		return val

	# decode symbols S0...S5 into characters 
	def decode(self,m, s):  
		self.ticks += m + s
		ten_dits = 5.0*self.twodits # normalize  dit = 0.1 dash = 0.3
		sym = self.pnn(m/ten_dits,s/ten_dits)    
	
		if verbosity: 
			print("\nticks:%f m:%f \ts:%f \t 2dit:%d \t " % (self.ticks, m, s, self.twodits))
			print("\nSymbol S%d " % sym)

		if sym ==0:
			self.addchar(".")
		elif sym == 1:
			self.printchar(".")
		elif sym == 2: 
			self.printword(".")
		elif sym == 3: 
			self.addchar("-")
		elif sym == 4: 
			self.printchar("-")
		elif sym == 5: 
			self.printword("-")
		else:
			sys.stdout.write('')  # not known symbol - noise?

	# update speed tracking from (dit,dash) pair over rolling average
	def update_tracking(self, dit, dash):
		if (dit > self.dit_low_limit and dit < self.dit_high_limit): 
			#print "\ndit:%f dash:%f" %(dit,dash)
			self.twodits = self.ra.rolling_avg((dash + dit) / 2.)	
		if (dash > 3*self.dit_low_limit and dash < 3*self.dit_high_limit):
			#print "\ndit:%f dash:%f" %(dit,dash)
			self.twodits = self.ra.rolling_avg((dash + dit) / 2.)	
	
	# detect KEYDOWN/KEYUP edges, measure timing and decode symbols 		  	
	def edge_recorder(self, v, upper, lower):
		KEYUP = 1
		KEYDOWN = 2
		if (v > upper):
			if (self.last == KEYUP):
				# calculate speed when received dit-dah  or dah-dit sequence 
				if (self.lastmark > 2*self.mark): 
					if verbosity: 
						print("update1: %f %f" % (self.mark, self.lastmark))
					self.update_tracking(self.mark, self.lastmark)
				if (self.mark > 2*self.lastmark): 
					if verbosity:
						print("update2: %f %f" % (self.lastmark, self.mark))
					self.update_tracking(self.lastmark, self.mark)

				# decode received "mark-space" symbol 
				self.decode(self.mark, self.space)
				self.lastmark = self.mark
				self.mark = 0
				self.space = 0
				self.last = KEYDOWN
				return self.twodits
			self.mark +=1 
		elif (v < lower):  
			self.last = KEYUP
			self.space +=1
		return self.twodits
# end Morse class