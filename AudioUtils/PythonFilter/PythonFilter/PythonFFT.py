import matplotlib.pyplot as plt
from scipy.fftpack import fft,fftfreq
from scipy.io import wavfile # get the api
import numpy as np

def load_audio(fname):
	fs, data = wavfile.read(fname) # load the data
	mono = data.T[0] # this is a two channel soundtrack, I get the first track
	return (fs,data)

def produce_fft(infputfile,outputfile):
	print("Processing " + infputfile)
	(frate,mono) = load_audio(infputfile)
	mononorm = [(sample/2**16.)*2 for sample in mono] # this is 8-bit track, normalized on [-1,1)

	w = fft(mononorm) # calculate fourier transform (complex numbers list)
	wlen = len(w)/2  # you only need half of the fft list (real signal symmetry)
	freqs = fftfreq(len(mononorm)) * frate

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
	plt.savefig(outputfile)   # save the figure to file
	plt.close()    # close the figure
	print("FFT saved")

if __name__ == '__main__':
	produce_fft(r'..\..\..\Samples\recording.wav',r'..\..\..\Samples\recording.png')
	produce_fft(r'..\..\..\Samples\battlefield_1.wav',r'..\..\..\Samples\battlefield_1.png')

