import wave
import struct
import numpy as np
import matplotlib.pyplot as plt

def load_audio(fname):
	wav_file = wave.open(fname, 'r')
	info = wav_file.getparams()
	print(info)
	data = wav_file.readframes(info.nframes)
	wav_file.close()
	data = struct.unpack('{n}h'.format(n=info.nframes), data)
	data = np.array(data)
	return (info.framerate,data)

def produce_fft(infputfile,outputfile):
	(frate,data) = load_audio(infputfile)
	w = np.fft.fft(data)
	freqs = np.fft.fftfreq(len(w))
	# just a check this should be between -0.5 and 0.5
	print(freqs.min(), freqs.max())

	# Find the peak in the coefficients
	idx = np.argmax(np.abs(w))
	freq = freqs[idx]
	freq_in_hertz = abs(freq * frate)

	print(freq_in_hertz)

	#Plot the spectrum
	d = len(w)/2  # you only need half of the fft list (real signal symmetry)
	fig = plt.plot(abs(w[:(d-1)]),'r') 
	#plt.show()
	plt.savefig(outputfile)   # save the figure to file
	plt.close()    # close the figure

if __name__ == '__main__':
	produce_fft(r'..\..\..\Samples\recording.wav',r'..\..\..\Samples\recording.png')
	produce_fft(r'..\..\..\Samples\battlefield_1.wav',r'..\..\..\Samples\battlefield_1.png')

