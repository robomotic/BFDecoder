import os
import sys
import time
import string
import numpy as np
from numpy.lib import stride_tricks
import pyaudio
import math
import cmath
from scipy.io import wavfile
from scipy.signal import butter, filtfilt, periodogram
import matplotlib.pyplot as plt
from optparse import OptionParser
from array import *

from Morse import *
from KalmanFilter1D import KalmanFilter1D
	
Codebook = {
  '.-'	:'A', '-...':'B', '-.-.':'C', '-..'	:'D', '.'	:'E',
  '..-.':'F', '--.'	:'G', '....':'H', '..'	:'I', '.---':'J',
  '-.-':'K', '.-..' : 'L', '--' :'M', '-.' :'N', '---':'O',
  '.--.' : 'P', '--.-' : 'Q', '.-.':'R', '...':'S', '-'  :'T',
  '..-':'U', '...-' : 'V', '.--':'W', '-..-' : 'X', '-.--' : 'Y',
  '--..' : 'Z', '.----' : '1', '..---' : '2', '...--' : '3', 
  '....-' : '4', '.....' : '5', '-....' : '6', '--...' : '7', 
  '---..' : '8','----.' : '9','-----' : '0',
  '-...-' : '=', '.-.-':'~', '.-...' :'<AS>', '.-.-.' : '<AR>', '...-.-' : '<SK>',
  '-.--.' : '<KN>', '..-.-' : '<INT>', '....--' : '<HM>', '...-.' : '<VE>',
  '.-..-.' : '\\', '.----.' : '\'', '...-..-' : '$', '-.--.' : '(', '-.--.-' : ')', 
  '--..--' : ',', '-....-' : '-', '.-.-.-' : '.', '-..-.' : '/', '---...' : ':', 
  '-.-.-.' : ';', '..--..' : '?', '..--.-' : '_', '.--.-.' : '@', '-.-.--' : '!'
}

""" short time fourier transform of audio signal """
def stft(sig, frameSize, overlapFac=0.5, window=np.hanning):
    win = window(frameSize)
    hopSize = int(frameSize - np.floor(overlapFac * frameSize))
    
    # zeros at beginning (thus center of 1st window should be for sample nr. 0)
    samples = np.append(np.zeros(np.floor(frameSize/2.0)), sig)    
    # cols for windowing
    cols = np.ceil( (len(samples) - frameSize) / float(hopSize)) + 1
    # zeros at end (thus samples can be fully covered by frames)
    samples = np.append(samples, np.zeros(frameSize))
    
    frames = stride_tricks.as_strided(samples, shape=(cols, frameSize), strides=(samples.strides[0]*hopSize, samples.strides[0])).copy()
    frames *= win
    
    return np.fft.rfft(frames)  

 
# returns AGC decay values 
def decayavg(average,input, weight):

	if (weight <= 1.0): 
		return input
	else:
		return input * (1.0 / weight) + average * (1.0 - (1.0 / weight))

# clamps output between mn and mx values 
def clamp(x, mn, mx): 
	if x > mx:
		return mx
	if x < mn:
		return mn
	else:
		return x
	

# decode signal envelope into Morse symbols and then characters
def decode_stream(signal,samplerate):

	# create morse object
	m = Morse(signal,samplerate)

	# assume 10ms signal rise time 
	bfv = (samplerate * .010)   
	# moving average filter to smooth signal envelope - reduce noise spikes
	env = np.resize(np.convolve(signal, np.ones(bfv)/bfv),len(signal))
	mx = np.nanmax(env)
	mn = np.nanmin(env)
	mean = np.mean(env)
		
	# prepare arrays to collect plotting data	
	agcv = np.arange(len(env))
	twodits = np.arange(len(env))
	t = np.linspace(0,1,len(env))

	agcpeak = mx
	i = 0
	while i < len(env): 

		# AGC is useful if signal has rapid amplitude variations due to fading, QSB etc.
		# In computer generated audio the amplitude is not varied 
		# Parameters control attack/decay time: fast attack (5) - slow decay (700) 
		if agc:
			z = env[i] - mean	
			if (z > agcpeak):
				agcpeak = decayavg(agcpeak,z,5)
			else:
				agcpeak = decayavg(agcpeak,z,700)
			agcv[i] = agcpeak
			if agcpeak > 0:
				z /= agcpeak
				z = clamp(z,0.,1.)
			up  = UPPER_THRESHOLD
			down = LOWER_THRESHOLD
		else:
			# calculate signal threshold if no AGC is used
			z = env[i] 
			up   = UPPER_THRESHOLD * (mx - mn)
			down = LOWER_THRESHOLD * (mx - mn)
		
		# capture estimated speed over time for plotting 
		twodits[i] = m.edge_recorder(z,up,down)
		
		i += 1
	
	# plot key variables 
	if plotter:
		ax1=plt.subplot(3,1,1)
		plt.plot(signal,'g-') #,t,up*signal,'r--')
		ax1.set_title("Signal")

		ax2=plt.subplot(3,1,2)	
		plt.plot(1.2*samplerate*2/twodits)  # plot speed estimate in WPM
		ax2.set_title("WPM")	
		
		if agc:
			ax3=plt.subplot(3,1,3)
			plt.plot( agcv,'g-')
			ax3.set_title("AGC")
		plt.show()

def demodulate(x,Fs,freq):

	# demodulate audio signal with known CW frequency 

	t = np.arange(len(x))/ float(Fs)
	y =  x*((1 + np.sin(2*np.pi*freq*t))/2 )	
	
	#calculate envelope and low pass filter this demodulated signal
	#filter bandwidth impacts decoding accuracy significantly 
	#for high SNR signals 50 Hz is better, for low SNR 20Hz is better
	# 25Hz is a compromise - could this be made an adaptive value? 
	Wn = 40./ (Fs/2.)  	# 25 Hz cut-off for lowpass  

	b, a = butter(2, Wn)  	# 2nd order butter filter
	z = filtfilt(b, a, abs(y))
	
	#pass envelope magnitude to decoder 
	decode_stream(z,Fs)

# process audio file by demodulator and envelope detector 
def process(fname):
	Fs, x = wavfile.read(fname)
	a = str.split(fname,".wav")
	b = str.split(a[0],"cw")
	sys.stdout.write(b[0])
	sys.stdout.write(",")
	# find frequency peaks of high volume CW signals 
	if fft_scan:
		f,s = periodogram(x,Fs,'blackman',4096,'linear',False,scaling='spectrum')
		# download peakdetect from # https://gist.github.com/endolith/250860
		from peakdetect import peakdet
		threshold = max(s)*0.4  # only 0.4 ... 1.0 of max value freq peaks included
		maxtab, mintab = peakdet(abs(s[0:len(s)/2-1]), threshold,f[0:len(f)/2-1] )

		if plotter:
			plt.plot(f[0:len(f)/2-1],abs(s[0:len(s)/2-1]),'g-')
			print(maxtab)

			from matplotlib.pyplot import plot, scatter, show
			scatter(maxtab[:,0], maxtab[:,1], color='blue')
			plt.show()
	
	# process all CW stations with higher than threshold volume
	if fft_scan:
		for freq in maxtab[:,0]:
			print("\nfreq:%5.2f" % freq)
			demodulate(x,Fs,freq)
	else:
		demodulate(x,Fs,MORSE_FREQUENCY)	

def main(*args, **kwargs):
  
	global verbosity
	global plotter
	global agc
	global fft_scan
	
	parser = OptionParser(usage="%prog [OPTIONS] <audio files>\nDecodes morse code from .WAV audio files")

	parser.add_option("-v", "--verbose",
	  action="store_true",
	  dest="verbose",
	  default=False,
	  help="Prints details about errors and calls.")
	parser.add_option("-p", "--plot",
	  action="store_true",
	  dest="plotter",
	  default=False,
	  help="Plot signal, speed estimate and AGC if used")
	parser.add_option("-a", "--agc",
	  action="store_true",
	  dest="agc",
	  default=False,
	  help="Use automatic gain control")
	parser.add_option("-f", "--fft",
	  action="store_true",
	  dest="fft",
	  default=False,
	  help="Use automatic FFT frequency scan")

	(options, args) = parser.parse_args()
	if options.verbose:
		verbosity = True
	if options.plotter:
		plotter = True
	if options.agc:
		agc = True
	if options.fft:
		fft_scan = True
	if len(args) < 1:
		print('usage: [OPTIONS] <audio files>')
		exit(1)

	#process all audio files given as arguments
	print("ID,Prediction")
	for i in range(0,len(args)):
		process(args[i])
		print("")
		
if __name__ == "__main__":
	main()