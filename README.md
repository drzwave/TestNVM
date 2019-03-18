# TestNVM
Test Script for testing a 500 series Z-Wave chip external serial flash chip.

This repository contains a simple Python script which exercise the external serial flash chip (NVM) of a 500 series Z-Wave system.

The NVM is accessed by downloading the SerialAPI into the Z-Wave chip and then utilizing the Memory API to access it. 
No hardware connections to the NVM are required and the entire NVM can be tested and read/written.
The advantage of this method is the NVM does not have to be desoldered from the board and soldered back on to test it and read out the contents.
The SerialAPI has to be programmed into the ZM5x0x and the UART has to be connected to a PC or Raspberry Pi or other CPU that can run Python.

This program can also serve as a demonstrator on how to use the SerialAPI.

# Usage
```
python TestNVM.py [COMxx]
 The optional COMxx parameter is the serial port connection from the PC or Raspberry Pi.
 The program was tested using a Raspberry Pi with the ZM5x0x connected to the UART 
  on the 40 pin header on /dev/ttyAMA0.
 Once the program begins, a menu of commands is listed.
 Press ? to get help.
```

# Setup
- Connect a 500s series chip via the UART to a PC or Linux computer (I used a Raspberry Pi during development)
- Use the ZDP03A or other programmer to program the SerialAPI into the 500 series chip
- Run the program
- You can now do things like:
    - Read out parts or all of the External NVM
    - fill the NVM with a value - filling it with FF efectively makes it like a brand new part that has never been powered up
    - Reboot the ZM5x0x - this may (but often does not) re-initialize the NVM
    - Return the Zm5x0x to factory fresh by issuing a ZW_SetDefault. This will also re-initialize the External NVM
    - Include/Exclude a node - this will alter the NVM data with Node and routing information

# Contacts
- Eric Ryherd - drzwave@silabs.com - Author

NOTE: This program is provided AS-IS and without support. Feel free to copy and improve.



