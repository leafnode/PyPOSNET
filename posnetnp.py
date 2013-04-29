#!/usr/bin/python

import time
import pyposnet
import xmmscontrol.client

conn = xmmscontrol.client.connect("dupa.8", "deith.dom.wafel.com")
kasa = pyposnet.posnet("/dev/usb/tts/0")

width = 20
ov = None
state = 1
current = 0

while True:
    np = conn.nowPlaying()
    l = len(np)
    if l <= 20:
	kasa.display_client_string(np, upper = True)
	current = 0
    else:
	if current < 0:
	    current = 0
	    state = 2
	elif current+20 > l:
	    current = l-20
	    state = 2
	kasa.display_client_string(np[current:current+20], upper = True)
	if state == 1:
	    current += 1
	elif state == 2:
	    time.sleep(1)
	    if current != 0:
		state = 3
	    else:
		state = 1
	elif state == 3:
	    current -= 1
    
    v = conn.volume()
    if v != ov:
	ov = v
	v = int(v[1:v.find(',')])
	kasa.display_client_string("Vol %i%%" % v, lower = True)

    time.sleep(1)

