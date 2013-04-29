#!/usr/bin/python
# -*- encoding: iso-8859-2 -*-
import serial
import time

"""
TODO:
    Kaucje
    Podawanie opcjonalnych numerów kasy i kasjera
    cancel_transaction
"""

BACKLIGHT_NEVER = 2
BACKLIGHT_ALWAYS = 1
BACKLIGHT_AC = 0

ERROR_MESSAGE      = 0
ERROR_SILENT       = 1
ERROR_MESSAGE_CODE = 2
ERROR_CODE         = 3

RABAT_NONE           = 0
RABAT_PRICE          = 1
RABAT_PERCENT        = 2
RABAT_NARZUT         = 3
RABAT_NARZUT_PERCENT = 4

def checksum(command):
    ck = 255
    for i in range(2, len(command)):
        ck = ck ^ ord(command[i])
    return "%02X" % (ck,)
        
class posnet:

    _serial = None

    def __init__(self, port="/dev/ttyS0"):
        self._serial = serial.Serial(port, 9600)

    def write(self, data):
        self._serial.write(data)

    def read(self):
        return self._serial.read()

    def dle(self):
        self.write("\x10")
        byte = self.read()
        byte = ord(byte)
        while byte < 112 or byte > 119:
            self.write("\x10")
            byte = self.read()
            byte = ord(byte)
        err = (byte & 1) != 0
        pe = (byte & 2) != 0
        onl = (byte & 4) != 0
        return {'err' : err, 'pe' : pe, 'onl' : onl}

    def enq(self):
        self.write("\x05")
        byte = self.read()
        byte = ord(byte)
        while byte < 96 or byte > 111:
            self.write("\x05")
            byte = self.read()
            byte = ord(byte)
        trf = (byte & 1) != 0
        par = (byte & 2) != 0
        cmd = (byte & 4) != 0
        fsk = (byte & 8) != 0
        return {'trf' : trf, 'par' : par, 'cmd' : cmd, 'fsk' : fsk}

    def bel(self):
        self.write('\x07')

    def can(self):
        self.write('\x18')

    def command(self, command, args = [], txtargs = '', **dict):
        string = "\x1b\x50"
        args = map(lambda x: str(x), args)
        string += ';'.join(args)
        string += str(command)
        string += txtargs
        if dict.get('nocs', False) != True:
            string += checksum(string)
        string += "\x1b\x5c"
        self.write(string)

    def get_response(self):
        out = ""
        byte = self._serial.read(size=1)
        while byte != '\x5c':
            out += byte
            byte = self._serial.read(size=1)
        return out

    def set_clock(self, year, month, day, hour, minute, second, nr_kasy = None, kasjer = None):
        command = "$c"
        args = [year, month, day, hour, minute, second ]
        if nr_kasy and kasjer:
            txtargs = "%s\r%s\r" % (nr_kasy, kasjer)
        else:
            txtargs = ''
        self.command(command, args, txtargs)

    def set_current_time(self):
        struct = time.localtime()
        self.set_clock("%02d" % (struct[0] % 2000), struct[1], struct[2], struct[3], struct[4], struct[5])
        
    def display_string(self, data):
        command = "$d"
        args = ["2",]
        data = str(data)
        self.command(command, args, data, nocs = True)

    def display_time(self, arg = 0):
        command = "$d"
        args = [3,]
        if arg == 0:
            args.append(0)
        else:
            args.append(1)
        self.command(command, args)

    def display_register(self):
        command = "$d"
        args = ["4",]
        self.command(command, args, nocs = True)

    def display_client_string(self, data, upper = False, lower = False):
        command = "$d"
        if not lower:
            args = ["101",]
        else:
            args = ["102",]
        
        data = str(data)
        self.command(command, args, data)

    def set_ptu(self, params):
        struct = time.localtime()
        cnt = len(params)
        args = [cnt, "%02d" % (struct[0] % 2000), struct[1], struct[2]]
        command = "$p"
        txtargs = '/'.join(params)
        self.command(command, args, txtargs)

    def set_header(self, txt):
        command = "$f"
        args = ["0",]
        txt += "\xff"
        self.command(command, args, txt)

    def get_header(self):
        self.command("#u")
        response = self.get_response()
        return response[response.find("#U")+2:-4]
        
    def set_rabat(self, nr):
        command = "$r"
        if nr == 1:
            args = [1,]
        elif nr == 2:
            args = [0,]
        else:
            raise RuntimeException
        
        self.command(command, args)

    def set_service_interval(self, days, warning):
        command = "$o"
        args = [0,]
        txtargs = "%i/%s\r" % (days, warning)
        self.command(command, args, txtargs)

    def set_auth_code(self, code):
        command = "$o"
        args = [1,]
        self.command(command, args, code+"\r")

    def paper_feed(self, lines):
        command = "#l"
        args = [lines,]
        self.command(command, args)

    def paper_econo(self, enable = True):
        command = "$r"
        args = [3,]
        if enable:
            args.append(1)
        else:
            args.append(0)
        self.command(command, args)

    def operator_display(self, enable = True):
        command = "$r"
        args = [4,]
        if enable:
            args.append(1)
        else:
            args.append(0)
        self.command(command, args)

    def backlight_options(self, mode = BACKLIGHT_ALWAYS):
        command = "$r"
        args = [5, 0, mode]
        self.command(command, args)

    def backlight_intensity(self, val):
        command = "$r"
        if val < 0 or val > 15:
            raise ValueError
        args = [5, 1, val]
        self.command(command, args)
        
    def backlight_contrast(self, val):
        command = "$r"
        if val < 0 or val > 31:
            raise ValueError
        args = [5, 2, val]
        self.command(command, args)
    
    def error_handling(self, error = ERROR_MESSAGE):
        command = "#e"
        args = [error,]
        self.command(command, args)
    
    def begin_transaction(self, count = 0):
        command = "$h"
        args = [count,]
        self.command(command, args)
        self._position = 0

    def position(self, name, quantity, ptu, price, brutto, rabat = RABAT_NONE, rabat_value = 0.0, rabat_desc = 0, rabat_user_desc = ''):
        command = "$l"
        args = [self._position, rabat]
        if rabat_desc != 0:
            args.append(rabat_desc)
        txtargs = "%s\r%i\r%s/%.2f/%.2f/" % (name, quantity, ptu, price, brutto)
        if rabat != RABAT_NONE:
            txtargs += "%.2f/" % (rabat_value,)
            
        if rabat_desc == 16 and rabat_user_desc != '':
            txtargs += "/%s\r" % (rabat_user_desc,)
        
        self.command(command, args, txtargs)
        self._position += 1

    def cancel_transaction(self, new_paragon = False):
        command = "$e"
        args = [0,]
        if new_paragon:
            args.append(2)
        else:
            args.append(0)
        self.command(command, args)

    def commit_transaction(self,  rabat ):
        pass
