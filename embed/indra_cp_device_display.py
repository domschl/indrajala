# Description: CircuitPython client to send an event to the Indra server, Cicruit Python 9.2.1

import wifi
import socketpool
import adafruit_connection_manager
import adafruit_requests
import time

import board
import busio
import displayio
import terminalio
from fourwire import FourWire
from adafruit_st7789 import ST7789
from adafruit_display_text import label

from indra_cp_config import ssid, password, indraserver_url, device_hostname, cert_authority

displayio.release_displays()

#               Clock       MOSI        MISO
spi = busio.SPI(board.GP10, board.GP11, None)
while not spi.try_lock():
    pass
spi.configure(baudrate=24000000) # Configure SPI for 24MHz
spi.unlock()
tft_cs = board.GP9
tft_dc = board.GP8

display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=board.GP12)

display = ST7789(display_bus, width=240, height=240, rowstart=80, rotation=270, backlight_pin=board.GP13)

# Connect to Wi-Fi
print("Device", device_hostname, "connecting via WLAN", ssid, "to server", indraserver_url)

# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
ssl_context.load_verify_locations(cadata=cert_authority)

requests = adafruit_requests.Session(pool, ssl_context)

# rssi = wifi.radio.ap_info.rssi

print(f"\nConnecting to {ssid}...")

# print(f"Signal Strength: {rssi}")

server_connected = False

while server_connected is False:
    try:
        print("Trying to connect...")
        # Connect to the Wi-Fi network
        wifi.radio.connect(ssid, password)
        server_connected = True
    except OSError as e:
        print(f"OSError: {e}")
        time.sleep(2)

print("Wifi connected!")

# Initialize the requests library
# Define URL and data
url = indraserver_url + "/api/v1/indraevent"
data = {"event": {"domain": "$event/test", "from_id": "circuit_python.1", "data": 1}}

# Make HTTPS POST request
response = requests.post(url, json=data)

# Print response status code
print("Response:", response.status_code, response.text)

# Make the display context
splash = displayio.Group()
display.root_group = splash
color_bitmap = displayio.Bitmap(240, 240, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0x0000FF # Bright Blue
bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
splash.append(bg_sprite)

# Draw a smaller inner rectangle
inner_bitmap = displayio.Bitmap(200, 200, 1)
inner_palette = displayio.Palette(1)
inner_palette[0] = 0xFFFFFF # White
inner_sprite = displayio.TileGrid(inner_bitmap, pixel_shader=inner_palette, x=20, y=20)
splash.append(inner_sprite)

# Draw a label
text_group = displayio.Group(scale=2, x=50, y=120)
text = "Hello World!"
text_area = label.Label(terminalio.FONT, text=text, color=0x000000)
text_group.append(text_area)  # Subgroup for text scaling
splash.append(text_group)

n=10
while n > 0:
    time.sleep(1)
    n = n-1
    
