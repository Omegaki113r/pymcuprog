"""
Serial driver for UPDI stack
"""
import time
from logging import getLogger
import serial
from serial.serialutil import SerialException

from . import constants

DEFAULT_SERIALUPDI_BAUD = 115200

class UpdiPhysical:
    """
    PDI physical driver using a given serial port at a given baud
    """

    def __init__(self, port, baud=DEFAULT_SERIALUPDI_BAUD, timeout=None):
        """
        Serial port physical interface for UPDI

        :param port: Serial port name to connect to.
        :type port: str
        :param baud: baud rate in bps to use for communications
        :type baud: int
        :param timeout: timeout value for serial reading.
            When UPDI is not enabled, attempting to read will return after this timeout period.
        :type timeout: float
        """
        self.logger = getLogger(__name__)

        # Inter-byte delay
        self.ibdly = 0.0001
        self.port = port
        # Set default baud if not provided
        if baud:
            self.baud = baud
        else:
            self.baud = DEFAULT_SERIALUPDI_BAUD
        # Default timeout to 1.0s
        if timeout:
            self.timeout = timeout
        else:
            self.timeout = 1.0
        self.ser = None

        self.initialise_serial(self.port, self.baud, self.timeout)
        # send an initial break as handshake
        self.send([constants.UPDI_BREAK])

    def initialise_serial(self, port, baud, timeout):
        """
        Standard serial port initialisation

        :param port: Serial port name to connect to
        :type port: str
        :param baud: Baud rate in bps to use for communications
        :type baud: int
        :param timeout: Timeout value for serial reading.
            When UPDI is not enabled, attempting to read will return after this timeout period.
        :type timeout: float
        """
        self.logger.info("Opening port '%s' at %d baud (timeout %.01fs)", port, baud, timeout)
        try:
            self.ser = serial.Serial(port, baud, parity=serial.PARITY_EVEN, timeout=timeout, stopbits=serial.STOPBITS_TWO)
        except SerialException:
            self.logger.error("Unable to open serial port '%s'", port)
            raise

    def _loginfo(self, msg, data):
        if data and isinstance(data[0], str):
            i_data = [ord(x) for x in data]
        else:
            i_data = data
        data_str = "[" + ", ".join(["0x{:02X}".format(x) for x in i_data]) + "]"
        self.logger.debug("%s : %s", msg, data_str)

    def send_double_break(self):
        """
        Sends a double break to reset the UPDI port

        BREAK is actually just a slower zero frame
        A double break is guaranteed to push the UPDI state
        machine into a known state, albeit rather brutally
        """

        self.logger.info("Sending double break")

        # Re-init at a lower baud
        # At 300 bauds, the break character will pull the line low for 30ms
        # Which is slightly above the recommended 24.6ms
        self.ser.close()
        temporary_serial = serial.Serial(self.port, 300, parity=serial.PARITY_EVEN, timeout=self.timeout,
                                         stopbits=serial.STOPBITS_ONE)

        # Send two break characters, with 1 stop bit in between
        temporary_serial.write([constants.UPDI_BREAK])

        # Wait for the double break end
        temporary_serial.read(1)

        time.sleep(0.1)

        # Send two break characters, with 1 stop bit in between
        temporary_serial.write([constants.UPDI_BREAK])

        # Wait for the double break end
        temporary_serial.read(1)

        # Re-init at the real baud
        temporary_serial.close()
        self.initialise_serial(self.port, self.baud, self.timeout)

    def send(self, command):
        """
        Sends a char array to UPDI without inter-byte delay
        Note that the byte will echo back

        :param command: command to send
        """
        self._loginfo("send", command)

        self.ser.write(command)

        # it will echo back.
        self.ser.read(len(command))

    def receive(self, size):
        """
        Receives a frame of a known number of chars from UPDI

        :param size: bytes to receive
        """
        response = bytearray()
        timeout = 1

        # For each byte
        while size and timeout:

            # Read
            character = self.ser.read()

            # Anything in?
            if character:
                response.append(ord(character))
                size -= 1
            else:
                timeout -= 1

        self._loginfo("receive", response)
        return response

    def sib(self):
        """
        System information block is just a string coming back from a SIB command
        """
        self.send([
            constants.UPDI_PHY_SYNC,
            constants.UPDI_KEY | constants.UPDI_KEY_SIB | constants.UPDI_SIB_32BYTES])
        return self.ser.readline()

    def __del__(self):
        if self.ser:
            self.logger.info("Closing port '%s'", self.port)
            self.ser.close()
