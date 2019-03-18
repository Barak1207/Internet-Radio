###BARAK KARAKUKLI###
#LAST CHANGE WAS 19.11.2018


###___GPIO WIRING___###
###RASPBERRY PI 3###

# The wiring for the LCD is as follows:
# 0 : GND
# 2 : 5V
# 3 : Contrast (0-5V)
# 4 : RS (Register Select)
# 5 : R/W (Read Write)	   - GROUND THIS PIN
# 6 : Enable or Strobe
# 7 : Data Bit 0			 - NOT USED
# 8 : Data Bit 1			 - NOT USED
# 9 : Data Bit 2			 - NOT USED
# 10: Data Bit 3			 - NOT USED
# 11: Data Bit 4
# 12: Data Bit 5
# 13: Data Bit 6
# 14: Data Bit 7
# 15: LCD Backlight +5V**
# 15: LCD Backlight GND
 

#RS -> GPIO7
#E -> GPIO8
#Data Bit 4 -> GPIO25
#Data Bit 5 -> GPIO24
#Data Bit 6 -> GPIO23
#Data Bit 7 -> GPIO18

#STOP_START_SWITCH -> GPIO10

#OMX_PAUSE_RESUME_BUTTON -> GPIO17
#OMX_SEEK_FORWARD_BUTTON  -> GPIO27
#OMX_SEEK_BACKWARD_BUTTON -> GPIO22

#SOCKET_WAITING_LED -> GPIO12





				#LCD 			#OMX
#USED GPIO [7,8,18,23,24,25,  17,22,27]


from random import randint
import time
import socket

from functools import partial
from os import getcwd, chdir, system, listdir, devnull, remove, popen
from os.path import isfile, join
import threading

#from bs4 import BeautifulSoup

import subprocess
import signal
import psutil


import urllib2 as url

import RPi.GPIO as GPIO

import youtube_dl as yt
from mutagen.mp3 import MP3


###GLOBAL VARIABLES###
###
###
# Define GPIO to LCD mapping
LCD_RS = 7
LCD_E  = 8
LCD_D4 = 25
LCD_D5 = 24
LCD_D6 = 23
LCD_D7 = 18
# Define some device constants
LCD_WIDTH = 16	# Maximum characters per line
LCD_CHR = True
LCD_CMD = False
LCD_LINE_1 = 0x80 # LCD RAM address for the 1st line
LCD_LINE_2 = 0xC0 # LCD RAM address for the 2nd line
# Timing constants
E_PULSE = 0.0005
E_DELAY = 0.0005
###
###
SOCKET_WAITING_LED = 12
###
#STOP_START_SWITCH = 10
###
OMX_PAUSE_RESUME_BUTTON = 17
OMX_SEEK_FORWARD_BUTTON = 27
OMX_SEEK_BACKWARD_BUTTON = 22
###

OMX_QUIT = 'q'
OMX_PAUSE_RESUME = 'p'
OMX_SEEK_FORWARD = '\x1b[C' #Right arrow key
OMX_SEEK_BACKWARD = '\x1b[D'#Left arrow key
OMX_INCREASE_VOLUME = '+'
OMX_DECREASE_VOLUME = '-'

AUDIO_OUTPUT = 'local' #hdmi #both

MAX_SONG_SIZE = '20m' #MB


CUR_DIR = getcwd()

HTML_PAGE = open(join(CUR_DIR, '!page.html')).read()
STATIC_RADIO_FILE = join(CUR_DIR, '!staticSound')
STATIC_RADIO_FILE_LENGTH = int(MP3(STATIC_RADIO_FILE).info.length)

DEVNULL = open(devnull)



class LCD_thread():
	#Creates a thread in which to run an infinite scrolling text loop if text length > LCD_WIDTH
	#Just fucking prints the text (w/o a new thread) to LCD if length is shorter than LCD_WIDTH

	__instance = None

	def __init__(self, text, line):

		if not LCD_thread.__instance:

			LCD_thread.__instance = self

			self.delay = 0.15
			
			self.__line = line
			self.__len = len(text)

			
			self.__cont = True
			self.__running = True


			if self.__len > LCD_WIDTH:
				#Need to infinite scroll, new thread.
				threading.Thread( target=self.__LCD_scroll_text, args=(text, self.__line) ).start()

			else:
				#Just fucking print that shit up nigga
				LCD_text(text, self.__line, delay=self.delay)
		else:
			raise ValueError('Can\'t have two instances of LCD_thread')


	def stop(self):
			#Break infinite loop if there is one, makes baddy thready go away.
			#Pretty much kills this shit class anyways		
			self.__cont = False

			#while self.__running:#To make sure scroll text loop doesn't do another iteration
			#	time.sleep(E_DELAY)
			time.sleep(.1)
			LCD_text('', self.__line)

			LCD_thread.__instance = None


	def wrapper(func):
		def inner(self, *args, **kwargs): # inner function needs parameters

			return func(self,  *args, **kwargs) # call the wrapped function
			print 'here'
			self.__running = False
		return inner # return the inner function (don't call it)

	@wrapper
	def __LCD_scroll_text(self, text, line, scroll_delay=0.4):

		pause = 2 * scroll_delay

		LCD_text(text[0 : LCD_WIDTH], self.__line, delay=self.delay)

		while self.__cont:
			#Scroll left, <-text
			for i in range(0, (self.__len - LCD_WIDTH) + 1 ):

				if not self.__cont:
					#If need to stop, don't wait for next iteration of outer while loop
					return

				LCD_text(text[ i : i + LCD_WIDTH ], self.__line)
				time.sleep(scroll_delay)

			time.sleep(pause)

			#Scroll right, text->
			for i in range(0, (self.__len - LCD_WIDTH) + 1):

				if not self.__cont:
					##
					return

				LCD_text(text[ self.__len - LCD_WIDTH - i :  self.__len - i ], self.__line)
				time.sleep(scroll_delay)

			time.sleep(pause)

		return 






def init_GPIO():

	GPIO.setwarnings(False)

	GPIO.setmode(GPIO.BCM)	   # Use BCM GPIO numbers
	GPIO.setup(LCD_E,  GPIO.OUT)  # E
	GPIO.setup(LCD_RS, GPIO.OUT) # RS
	GPIO.setup(LCD_D4, GPIO.OUT) # DB4
	GPIO.setup(LCD_D5, GPIO.OUT) # DB5
	GPIO.setup(LCD_D6, GPIO.OUT) # DB6
	GPIO.setup(LCD_D7, GPIO.OUT) # DB7

	#GPIO.setup(STOP_START_SWITCH, GPIO.IN, pull_up_down = GPIO.PUD_UP)

	GPIO.setup(OMX_PAUSE_RESUME_BUTTON, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
	GPIO.setup(OMX_SEEK_FORWARD_BUTTON, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
	#GPIO.setup(OMX_SEEK_BACKWARD_BUTTON, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)

	GPIO.setup(SOCKET_WAITING_LED, GPIO.OUT)

def init_LCD():
	# Initialise display
	LCD_byte(0x33,LCD_CMD) # 110011 Initialise
	LCD_byte(0x32,LCD_CMD) # 110010 Initialise
	LCD_byte(0x06,LCD_CMD) # 000110 Cursor move direction
	LCD_byte(0x0C,LCD_CMD) # 001100 Display On,Cursor Off, Blink Off
	LCD_byte(0x28,LCD_CMD) # 101000 Data length, number of lines, font size
	LCD_byte(0x01,LCD_CMD) # 000001 Clear display
	time.sleep(E_DELAY)

def LCD_toggle_enable():
	# Toggle enable
	time.sleep(E_DELAY)
	GPIO.output(LCD_E, True)
	time.sleep(E_PULSE)
	GPIO.output(LCD_E, False)
	time.sleep(E_DELAY)

def LCD_byte(bits, mode):
	# Send byte to data pins
	# bits = data
	# mode = True  for character, False for command
	GPIO.output(LCD_RS, mode) # RS
	# High bits
	GPIO.output(LCD_D4, False)
	GPIO.output(LCD_D5, False)
	GPIO.output(LCD_D6, False)
	GPIO.output(LCD_D7, False)
	if bits&0x10==0x10:
		GPIO.output(LCD_D4, True)
	if bits&0x20==0x20:
		GPIO.output(LCD_D5, True)
	if bits&0x40==0x40:
		GPIO.output(LCD_D6, True)
	if bits&0x80==0x80:
		GPIO.output(LCD_D7, True)
 
	# Toggle 'Enable' pin
	LCD_toggle_enable()
	# Low bits
	GPIO.output(LCD_D4, False)
	GPIO.output(LCD_D5, False)
	GPIO.output(LCD_D6, False)
	GPIO.output(LCD_D7, False)
	if bits&0x01==0x01:
		GPIO.output(LCD_D4, True)
	if bits&0x02==0x02:
		GPIO.output(LCD_D5, True)
	if bits&0x04==0x04:
		GPIO.output(LCD_D6, True)
	if bits&0x08==0x08:
		GPIO.output(LCD_D7, True)
 
	# Toggle 'Enable' pin
	LCD_toggle_enable()


def LCD_clear():
	LCD_byte(0x01, LCD_CMD) # 000001 Clear display
	time.sleep(E_DELAY)


def LCD_text(text, line, delay=0):
	# Send text to display

	text = text.ljust(LCD_WIDTH,' ')
	LCD_byte(line, LCD_CMD)
	for i in range(LCD_WIDTH):
		LCD_byte(ord(text[i]), LCD_CHR)
		time.sleep(delay)

def LCD_scroll_text(text, line, delay=0.3, infinite=False):
	pause = 0.5
	txt_len = len(text)

	while True:
		#Scroll left, <-text
		for i in range(0, (txt_len - LCD_WIDTH) + 1 ):
			LCD_byte(line, LCD_CMD)
			LCD_text(text[ i : i + LCD_WIDTH ], line)
			time.sleep(delay)

		time.sleep(pause)

		#Scroll right, text->
		for i in range(0, (txt_len - LCD_WIDTH) + 1):
			LCD_byte(line, LCD_CMD)
			LCD_text(text[ txt_len - LCD_WIDTH - i :  txt_len - i ], line)
			time.sleep(delay)

		time.sleep(pause)

		if not infinite:
			break






















def kill_child_processes(parent_pid, sig=signal.SIGTERM):
	#signal.SIGKILL, hard kill signal
	#signal.SIGTERM, soft kill signal
	#signal.SIGINT,  CTRL + C signal

	try:
		parent = psutil.Process(parent_pid)
	except psutil.NoSuchProcess:
		return
	children = parent.children(recursive=True)
	for process in children:
		process.send_signal(sig)
		#time.sleep(.10)



def delete_partial_downloads():
	files = [ f for f in listdir(".") if f.endswith('.part') ]
	for f in files:
		remove(f)



def song_exsists(song_name):
	#List all songs already downloaded
	#Return full path to song, if exsists
	files = [f for f in listdir(CUR_DIR) if isfile(join(CUR_DIR, f)) and (not f.endswith('.part')) ]
	song_nameL = song_name.lower()
	#if any file contains song_name, then it already exsists, return it
	for f in files:		
		if song_nameL in f.lower():
			return join(CUR_DIR, f)
	return False



def get_URL(song_name):
	#Returns tuple of ( full URL of song, video title ) by searching song_name in Youtube
	##################################HEY IDIOT################################
	#USE THIS NEXT TIME: youtube-dl "Taylor Swift 22" --skip-download --get-url
	#return  popen(' '.join([ 'youtube-dl', '"', 'ytsearch1: ', song_name, '"', '--get-url', '--skip-download', '--extract-audio', '--audio-quality', str(2) ])).read().strip()
	#And then you can skip the stream_song function since it's the same function
	#Note that this is os.popen! and not subporcess.Popen
	###########################################################################19.11.2018
	#BIG CHANGE, 19.11.2018
	#return  popen(' '.join([ 'youtube-dl', '"', 'ytsearch1: ', song_name, '"', '--get-url', '--skip-download', '--extract-audio', '--audio-quality', str(2) ])).read().strip()
	#I REVERTED THIS CHANGE SINCE IF YOU USE THIS URL THAT THE LINE ABOVE RETURNS, YOU DO NOT HAVE ACCESS TO THE VIDEO TITLE AND SO...
	watch = 'watch?v='
	title = 'title="'
	yt_search = 'http://www.youtube.com/results?search_query='
	yt_url = 'http://www.youtube.com/'
	yt_id_len = 11
	#Get HTML_reponse of the page recieved when searching song_name in youtube
	#Replacing any spaces in song_name...
	try:
		HTML_response = url.urlopen(yt_search + url.quote(song_name)).read()

	except Exception, e:
		#####
		import traceback
		traceback.print_exc()
		print 'Probs no internet! @get_URL'
		LCD_text('No internet?', LCD_LINE_1)

		return None

	watch_index = HTML_response.find(watch)
	return yt_url + HTML_response[ watch_index : ( len(watch) + watch_index  + yt_id_len ) ]



	#SMART BUT SUPER SLOW WAY
	#	x = 1
	#	#Three tries to find
	#	while x < 4:
	#		#Increase range to search in HTML_reponse
	#		soup = BeautifulSoup(HTML_response[40000 / x : 70000 * x], 'html.parser')
	#
	#		for link in soup.find_all('a'):
	#
	#			href = link.get('href')
	#			title = link.get('title')
	#
	#			if ( href and title ) and watch in href:
	#
	#				title = title.encode('ascii', 'ignore')
	#
	#				#Check is title contains searched song, if not, then probably it's the wrong song
	#				if song_name.lower() in title.lower():
	#					return  ( yt_url + href,  title )
	#					
	#		x += 1
	#	return false

#def download_songOLD(URL):
#	#Gets full URL, returns FULL path to the song file downloaded
#	#Save under title of youtube video, select best audio, if not available select worst in general, max file size constant.
#	download_output = subprocess.check_output( [ 'youtube-dl', '-o', '%(title)s', '-f', 'bestaudio/worst/best', '--max-filesize', MAX_SONG_SIZE, URL ] )
#	#Seriosuly shit way to find title of song.
#	dest = 'Destination: '
#	dest_index = download_output.find(dest)
#	return join( getcwd(), download_output[  dest_index + len(dest) : download_output.find('\n', dest_index) ] )



def download_song(URL):
	#Dump stderr/in,need stdout to know if finished
	try:
		#proc = subprocess.Popen( [ 'youtube-dl', '-o', '%(title)s', '-f', 'bestaudio/worst/best', '--max-filesize', MAX_SONG_SIZE, URL ] , stdin=subprocess.PIPE , stdout=subprocess.PIPE, stderr=DEVNULL )
		proc = subprocess.Popen( [ 'youtube-dl', '-o', '%(title)s.%(ext)s', '--extract-audio', '--max-filesize', MAX_SONG_SIZE, URL ] , stdin=subprocess.PIPE , stdout=subprocess.PIPE, stderr=DEVNULL )#19.11.2018
	except Exception, e:
		print 'Probs no internet! @download_song'
		LCD_text('No internet?', LCD_LINE_1)
	return proc



def stream_song(URL, pos=0):
	#Stream song with omxplayer directly from Youtube in a different subprocess, returns process	
	try:
		#streaming_URL = subprocess.check_output( [ 'youtube-dl', '-f', 'bestaudio/worst/best', '-g', URL ] )
		streaming_URL = subprocess.check_output( [ 'youtube-dl', '--extract-audio', '-g', URL ] ) #19.11.2018
	except Exception, e:
		print 'Probs no internet! @stream_song'
		LCD_text('No internet?', LCD_LINE_1)
	return play_song(streaming_URL.strip(), pos)	



def play_song(song_path, pos=0):
	#Get full path bruh
	#Plays song in omxplayer in a different subprocess, returns process
	#omxplayer creates a subprocess of it's own to play, need to kill kids.

	chdir('/usr/bin')
	proc = subprocess.Popen( [ '/bin/bash', 'omxplayer', '-b', '-l', str(pos), '-o', AUDIO_OUTPUT, song_path ]
			, stdin=subprocess.PIPE , stdout=DEVNULL, stderr=subprocess.STDOUT )
	chdir(CUR_DIR)
	return proc



def omxplayer_control(play_proc, channel):
	try:
		if channel is OMX_PAUSE_RESUME_BUTTON:
			play_proc.stdin.write(OMX_PAUSE_RESUME)
		elif channel is OMX_SEEK_FORWARD_BUTTON:
			play_proc.stdin.write(OMX_SEEK_FORWARD)
		elif channel is OMX_SEEK_BACKWARD_BUTTON:
			play_proc.stdin.write(OMX_SEEK_BACKWARD)
	except Exception, e:
		'print play_proc probably dead @omxplayer_control'


def fade_out(play_proc, iters):
	try:
		for i in range(0, iters):
			play_proc.stdin.write(OMX_DECREASE_VOLUME)
			time.sleep(1)
	except Exception, e:
		'print play_proc probably dead @fade_out'



def refresh_control_GPIO_events(play_proc):

	GPIO.remove_event_detect(OMX_PAUSE_RESUME_BUTTON)
	GPIO.remove_event_detect(OMX_SEEK_FORWARD_BUTTON)
	#GPIO.remove_event_detect(OMX_SEEK_BACKWARD_BUTTON)

	GPIO.add_event_detect(OMX_PAUSE_RESUME_BUTTON, GPIO.RISING, callback=partial(omxplayer_control,
		play_proc), bouncetime=500)
	GPIO.add_event_detect(OMX_SEEK_FORWARD_BUTTON, GPIO.RISING, callback=partial(omxplayer_control,
		play_proc), bouncetime=300)
	#GPIO.add_event_detect(OMX_SEEK_BACKWARD_BUTTON, GPIO.RISING, callback=partial(omxplayer_control,
	#	play_proc), bouncetime=300)



def get_song_name_socket(sock, play_proc):
	#This function deals with too many things now, proceed with caution
	#Keeps listetning until a new song name is entered that is not None
	print 'Waiting...'
	GPIO.output(SOCKET_WAITING_LED, True)

	while True:
		conn, addr = sock.accept()
		data = conn.recv(128)
		
		name = url.unquote( data[ len('GET /') : data.find(' HTTP/') ] ).strip()

		conn.send( HTML_PAGE )
		time.sleep(.5)
		conn.close()

		if name and ('favicon'  not in name.lower()):
			if name == '!!!':
				system('sudo init 0')
			elif name.startswith('!'):
				omxplayer_control(play_proc, OMX_PAUSE_RESUME_BUTTON)
				continue

			GPIO.output(SOCKET_WAITING_LED, False)
			return name


def get_internal_IP():
	#DISGUSTING!
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.connect(('www.google.com', 80))
	ip =  s.getsockname()[0]
	s.close()
	return ip



def teardown(play_proc, download_proc, LCD_t):

	loc_variables = locals()
	if play_proc and 'play_proc' in loc_variables:
		kill_child_processes(play_proc.pid)
		play_proc.kill()
		#play_proc.stdin.write(OMX_QUIT)

	if download_proc and 'download_proc' in loc_variables:
		try:
			kill_child_processes(download_proc.pid)
			download_proc.kill()
		except Exception, e:
			pass
	#if 'radio_static_proc' in loc_variables:
	#	kill_child_processes(radio_static_proc.pid)
	if LCD_t and 'LCD_t' in loc_variables:
		LCD_t.stop()

	#if 'download_proc' in locals():
	#	print 'Waiting for download to finish, CTRL + C to cancel...'
	#	download_proc.wait()
	#	print 'Done'



def flow(song_name):
	#Returns full path if exsists, false if doesn't
	song_path = song_exsists(song_name)

	if not song_path:
		#Need to download
		#Need to stream	

		print 'Getting URL...'
		song_URL = get_URL(song_name)
		
		print 'Playing', song_name
		play_proc = stream_song(song_URL)

		LCD_t = LCD_thread(song_name.title(), LCD_LINE_1)

		download_proc = download_song(song_URL)
		#download_proc.wait()
		#print 'finished Downloading...'

	else:
		print 'Exsists'
		#Just need to play file
		download_proc = None

		LCD_t = LCD_thread(song_name.title(), LCD_LINE_1)
		play_proc = play_song(song_path)

		print  'Playing', song_name

	return (play_proc, download_proc, LCD_t)



#def Switch_Blocking(play_proc, download_proc, LCD_t):
#	print 'blocking'
#	GPIO.remove_event_detect(STOP_START_SWITCH)
#	teardown(play_proc, download_proc, LCD_t)
#	while not GPIO.input(STOP_START_SWITCH):
#		print 'blocking'
#		time.sleep(.5)



#Main

#play_proc
#download_proc

#song_name ,Entered by user
#song_path ,Full path to file
#song_URL ,Full URL to the song on Youtube

try:

	init_GPIO()
	init_LCD()


	LCD_text('IP %s' % (get_internal_IP()), LCD_LINE_2)


	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.bind(('', 80))
	sock.listen(1)


	song_name = get_song_name_socket(sock,'')
	radio_static_proc = play_song(STATIC_RADIO_FILE, pos=randint(0, STATIC_RADIO_FILE_LENGTH - 20))

	while True:

		play_proc, download_proc, LCD_t = flow(song_name)

		#Fade out and quit static noise
		fade_out(radio_static_proc, 4)
		radio_static_proc.stdin.write(OMX_QUIT)

		refresh_control_GPIO_events(play_proc)
		#GPIO.add_event_detect(STOP_START_SWITCH, GPIO.FALLING, callback=partial(Switch_Blocking,
		#	play_proc, download_proc, LCD_t,), bouncetime=1000)

		song_name = get_song_name_socket(sock, play_proc)

		radio_static_proc = play_song(STATIC_RADIO_FILE, pos=randint(0, STATIC_RADIO_FILE_LENGTH - 20))

		fade_out(play_proc, 3)

		teardown(play_proc, download_proc, LCD_t)

		


except Exception, e:
	print e
	system('echo ' + str(e)+  '>> /../home/pi/Barak/log')
finally:
	#Prevent Zambros
	if sock and 'sock' in locals():
		sock.close()

	try:
		teardown(play_proc, download_proc, LCD_t)
	except Exception, e:
		pass
	
	LCD_clear()
	GPIO.output(SOCKET_WAITING_LED, False)
	GPIO.cleanup()
	DEVNULL.close()
	delete_partial_downloads()
	print 'Exiting...'
	
#sudo rm '!youtubeRadio.py' ; sudo wget 'http://10.0.0.7/Ethan Raspberry/youtubeRadio/!youtubeRadio.py' && sudo python '!youtubeRadio.py'
#sudo rm '!youtubeRadio.py' ; sudo rm '!staticSound' ; sudo rm '!page.html' ; sudo wget 'http://10.0.0.7/Ethan Raspberry/youtubeRadio/!youtubeRadio.py' && sudo wget 'http://10.0.0.7/Ethan Raspberry/youtubeRadio/!page.html' && sudo wget 'http://10.0.0.7/Ethan Raspberry/youtubeRadio/!staticSound' && sudo python '!youtubeRadio.py'
