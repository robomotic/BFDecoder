import matplotlib.pyplot as plt
from scipy.fftpack import fft,fftfreq
from scipy.io import wavfile # get the api
import numpy as np
from scipy.signal import butter, lfilter
import sys
import os

def load_audio(fname):
	fs, data = wavfile.read(fname) # load the data
	mono = data.T[0] # this is a two channel soundtrack, I get the first track
	return (fs,data)

def butter_bandpass(lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a


def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data)
    return y

def produce_fft(infputfile,outputfile,plot = False):
	print("Processing " + infputfile)
	(frate,mono) = load_audio(infputfile)
	mononorm = [(sample/2**16.)*2 for sample in mono] # this is 8-bit track, normalized on [-1,1)

	w = fft(mononorm) # calculate fourier transform (complex numbers list)
	wlen = len(w)/2  # you only need half of the fft list (real signal symmetry)
	freqs = fftfreq(len(mononorm)) * frate

	if plot == True:
		fig = plt.figure()

		ax1 = fig.add_subplot(211)
		ax2 = fig.add_subplot(212)
		ax1.plot(mononorm,'b')
		ax1.set_title("Audio signal 16 bit normalized")

		ax2.plot(freqs, np.abs(w),'r')
		ax2.set_xlabel('Frequency in Hertz [Hz]')
		ax2.set_ylabel('Magnitude')
		ax2.set_xlim(-frate / 2, frate / 2)
		#ax2.set_ylim(-5, 110)
		ax2.set_title("FFT of signal")
		fig.tight_layout()
		plt.show()
		plt.draw()
		fig.savefig(outputfile,dpi = 300)
		print("FFT saved")
		plt.close()
		return (frate,mononorm)
	else:
		return (frate,mononorm)

def filter_morse(inputfile,outdir=r'..\..\..\Samples',lowcut = 750,highcut = 800,order = 3 ):
	(frate,mono) = load_audio(inputfile)

	filtered = butter_bandpass_filter(mono, lowcut, highcut, frate, order = order)
	filepath = '{0}\{1}_{2}_{3}_{4}_.wav'.format(outdir, 'bandpass_filter',order, lowcut,highcut)
	wavfile.write(filepath,frate,np.round(filtered).astype('int16') )

	fig = plt.figure()


	ax1 = fig.add_subplot(211)
	ax2 = fig.add_subplot(212)

	ax1.plot(mono)
	ax2.plot(filtered)
	plt.show()
	
    
if __name__ == '__main__':
	
	if len(sys.argv)==2:
		(frate,mono) = produce_fft(r'..\..\..\Samples\recording.wav',r'..\..\..\Samples\recording.png')
	else:
		filter_morse(r'..\..\..\Samples\recording.wav')