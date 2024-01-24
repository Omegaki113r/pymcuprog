"""
Example usage of pymcuprog as a library to read the device ID
"""


# pymcuprog uses the Python logging module
import logging
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)

# Configure the session
from pymcuprog.backend import SessionConfig
sessionconfig = SessionConfig("avr128da48")
# sessionconfig = SessionConfig("atmega328p")

# Instantiate USB transport (only 1 tool connected)
from pymcuprog.toolconnection import ToolSerialConnection
transport = ToolSerialConnection()

# Instantiate backend
from pymcuprog.backend import Backend
backend = Backend()

# Connect to tool using transport
backend.connect_to_tool(transport)

# Start the session
backend.start_session(sessionconfig)

# Read the target device_id
device_id = backend.read_device_id()
print ("Device ID is {0:06X}".format(int.from_bytes(device_id, byteorder="little")))
backend.write_hex_to_target("boost.hex")

backend.end_session()