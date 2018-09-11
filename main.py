from network import LoRa
import binascii
import socket
import time
import pycom
from pytrack import Pytrack
from L76GNSS import L76GNSS

# need to connect to TTN-mapper (see faq)
# can also add a nice casing and a small display (obtain the rssi?)

# GPS settings
GPS_TIMEOUT        = 30 #How long to wait for a GPS reading per attempt
POST_MESSAGE_SLEEP = 15 #How long to wait between messages - affects GPS sample rate when connected

# TTN credentials
APP_EUI = 'XXX'
APP_KEY = 'ZZZZZZ'


def convert_payload(lat, lon, alt, hdop):
    """
        Converts to the format used by ttnmapper.org
    """
    payload = []
    latb = int(((lat + 90) / 180) * 0xFFFFFF)
    lonb = int(((lon + 180) / 360) * 0xFFFFFF)
    altb = int(round(float(alt), 0))
    hdopb = int(float(hdop) * 10)

    payload.append(((latb >> 16) & 0xFF))
    payload.append(((latb >> 8) & 0xFF))
    payload.append((latb & 0xFF))
    payload.append(((lonb >> 16) & 0xFF))
    payload.append(((lonb >> 8) & 0xFF))
    payload.append((lonb & 0xFF))
    payload.append(((altb  >> 8) & 0xFF))
    payload.append((altb & 0xFF))
    payload.append(hdopb & 0xFF)
    return payload


# Initialize LoRa in LORAWAN mode.
lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.AS923, adr=False, tx_retries=0, device_class=LoRa.CLASS_A)

# create an OTA authentication params
app_eui = binascii.unhexlify(APP_EUI)
app_key = binascii.unhexlify(APP_KEY)

# join a network using OTAA if not previously done
pycom.rgbled(0x7f7f00)
lora.join(activation=LoRa.OTAA, auth=(app_eui, app_key), timeout=0)

# wait until the module has joined the network
pycom.rgbled(0x7f0000)
while not lora.has_joined():
    print('Joining...')
    time.sleep(2)
pycom.rgbled(0x7f7f00)

# open a socket
sock = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
sock.setsockopt(socket.SOL_LORA, socket.SO_DR, 5)
sock.setblocking(True)
print('Socket created')

# starting the gps
py = Pytrack()
gps = L76GNSS(py, timeout=GPS_TIMEOUT)
fix = False

# main loop
while True:
    print("Getting position...")
    (lat, lon, alt, hdop) = gps.position()
    if not lat is None and not lon is None and not alt is None and not hdop is None: #Have a GPS fix
        if not fix:
            print("GPS lock acquired")
            pycom.rgbled(0x000000)
            fix = True
        print("{} {} {} {}".format(lat, lon, alt, hdop))
        payload = convert_payload(lat, lon, alt, hdop)
        sock.send(bytes(payload))
        time.sleep(POST_MESSAGE_SLEEP)
    else:   #No GPS fix
        if fix:
            print("Lost GPS")
            pycom.rgbled(0x7f7f00)
            fix = False
