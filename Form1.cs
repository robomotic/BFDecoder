using BattlefieldMorseCode;
using NAudio.Wave;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows.Forms;

namespace Tutorial6
{
    public partial class Form1 : Form
    {
		LoopbackRecorder Recorder;
		WaveFormat WaveFormat = new WaveFormat(44100, 1);
		WaveFormatConversionStream Wave;
		
		public Form1()
        {
            InitializeComponent();
        }

		/// <summary>
		/// Load a pre-recorded WAV
		/// </summary>
		private void openToolStripMenuItem_Click(object sender, EventArgs e)
		{
			OpenFileDialog open = new OpenFileDialog();
			open.InitialDirectory = @"c:\users\chris\appdata\local\temp";
			open.Filter = "Wave File (*.wav)|*.wav;";

			if (open.ShowDialog() != DialogResult.OK)
				return;

			// This will almost certainly go south! ;)
			WaveFileReader waveFileReader = new WaveFileReader(open.FileName);
			Wave = new WaveFormatConversionStream(WaveFormat, WaveFormatConversionStream.CreatePcmStream(waveFileReader));

			processToolStripMenuItem.Enabled = true;
			clearToolStripMenuItem.Enabled = true;
			startToolStripMenuItem.Enabled = false;
			stopToolStripMenuItem.Enabled = false;
		}

		private void startToolStripMenuItem_Click(object sender, EventArgs e)
		{
			Recorder = new LoopbackRecorder();
			Recorder.StartRecording();
			stopToolStripMenuItem.Enabled = true;
			processToolStripMenuItem.Enabled = true;
			startToolStripMenuItem.Enabled = false;
			openToolStripMenuItem.Enabled = false;
		}

		private void stopToolStripMenuItem_Click(object sender, EventArgs e)
		{
			Recorder.StopRecording();
			stopToolStripMenuItem.Enabled = false;
			clearToolStripMenuItem.Enabled = true;
			saveToolStripMenuItem.Enabled = true;
		}

		private void processToolStripMenuItem_Click(object sender, EventArgs e)
		{
			if (Wave == null)
			{
				Stream audioStream = Recorder.GetRecordingStream();
				audioStream.Position = 0;
				Wave = new WaveFormatConversionStream(WaveFormat, new Wave32To16Stream(new WaveFileReader(audioStream)));
			}
			ProcessAudio();
		}

		private void ProcessAudio()
		{
			SetupChart();

			byte[] audioData = new byte[16 * 1024];
			Int16[] convertedData = new Int16[audioData.Count() / sizeof(Int16)];

			int read = 0;
			Int16 lastSample = 0;
			int maxUpper = 500;

			while (Wave.Position < Wave.Length)
			{
				read = Wave.Read(audioData, 0, (16 * 1024));

				// Might need this to check we haven't run out of stuff to read
				if (read == 0)
					break;

				for (int i = 0; i < read / 2; i++)
				{
					convertedData[i] = BitConverter.ToInt16(audioData, i * 2);
					//chart1.Series["Wave"].Points.Add(BitConverter.ToInt16(audioData, i * 2));
				}

				//foreach (var sample in convertedData)
				//	chart1.Series["Wave"].Points.Add(sample);

				int freqThreshold = 400;

				foreach (var sample in convertedData)
				{
					if (sample > 0 && sample <= freqThreshold)
						chart1.Series["Wave"].Points.Add(freqThreshold);

					else if (sample > freqThreshold)
						chart1.Series["Wave"].Points.Add(0);

					else if (sample < 0 && sample <= -freqThreshold)
						chart1.Series["Wave"].Points.Add(freqThreshold);

					else if (sample < -freqThreshold)
						chart1.Series["Wave"].Points.Add(0);
				}

				int mode = (from sample in convertedData where sample > 0 group sample by sample into g orderby g.Count() descending select g.Key).FirstOrDefault();
				Console.WriteLine("Mode: {0}", mode);
			}
		}

		private void SetupChart()
		{
			while (chart1.Series.Count > 0) { chart1.Series.RemoveAt(0); }
			chart1.Series.Add("Wave");
			chart1.Series["Wave"].ChartType = System.Windows.Forms.DataVisualization.Charting.SeriesChartType.FastLine;
			chart1.Series["Wave"].ChartArea = "ChartArea1";
		}

		private void clearToolStripMenuItem_Click(object sender, EventArgs e)
		{
			if (Wave != null)
			{
				Wave.Close();
				Wave.Dispose();
				Wave = null;
				
			}

			if (Recorder != null)
			{
				Recorder.StopRecording();
				Recorder = null;
			}

			SetupChart();

			processToolStripMenuItem.Enabled = false;
			startToolStripMenuItem.Enabled = true;
			stopToolStripMenuItem.Enabled = false;
			openToolStripMenuItem.Enabled = true;
			clearToolStripMenuItem.Enabled = false;
			saveToolStripMenuItem.Enabled = false;
		}

		private void saveToolStripMenuItem_Click(object sender, EventArgs e)
		{
			if (Wave == null)
			{
				Stream audioStream = Recorder.GetRecordingStream();
				audioStream.Position = 0;
				Wave = new WaveFormatConversionStream(WaveFormat, new Wave32To16Stream(new WaveFileReader(audioStream)));
			}

			using (WaveFileWriter waveWriter = new WaveFileWriter(@"c:\users\chris\appdata\local\temp\recording.wav", Wave.WaveFormat))
			{

				byte[] buffer = new byte[16 * 1024];
				Wave.Position = 0;

				while (Wave.Position < Wave.Length)
				{
					int read = Wave.Read(buffer, 0, 16 * 1024);
					if (read > 0)
						waveWriter.Write(buffer, 0, read);
				}
			}
		}
	}
}
