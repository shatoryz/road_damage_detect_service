import serial

flag = False
# Function to parse GPGGA sentence and return coordinates
def parse_gpgga(sentence):
    parts = sentence.split(',')
    if parts[0] == "$GPGGA":
        lat = parts[2]
        lat_dir = parts[3]
        lon = parts[4]
        lon_dir = parts[5]
        return lat, lat_dir, lon, lon_dir
    return None

# Open the serial port
ser = serial.Serial('/dev/serial0', baudrate=9600, timeout=1)

while flag:
    nmea_sentence = ser.readline().decode('ascii', errors='replace')
    gps_data = parse_gpgga(nmea_sentence)
    if gps_data:
        lat, lat_dir, lon, lon_dir = gps_data
        print(f"Latitude: {lat} {lat_dir}, Longitude: {lon} {lon_dir}")