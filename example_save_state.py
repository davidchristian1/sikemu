#!/usr/bin/env python3
import pickle
import os
import firebase_admin
import RPi.GPIO as GPIO  # import GPIO

from firebase_admin import credentials
from firebase_admin import db
from hx711 import HX711  # import the class HX711
from gpiozero import LightSensor
from time import sleep
# setup LDR
ldr = LightSensor(4)
ldr2 = LightSensor(17)
# setup firebase
cred = credentials.Certificate('your firebase certificate')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'your firebase URL'
})

#modify according to your firebase structure
ref = db.reference('barang')
barang_ref = ref.child('barang_001')

try:
    GPIO.setmode(GPIO.BCM)  # set GPIO pin mode to BCM numbering
    # Create an object hx which represents your real hx711 chip
    # Required input parameters are only 'dout_pin' and 'pd_sck_pin'
    hx = HX711(dout_pin=5, pd_sck_pin=6)
    # Check if have swap file. If yes that suggest that the program was not
    # terminated proprly (power failure). Load the latest state.
    swap_file_name = 'swap_file.swp'
    if os.path.isfile(swap_file_name):
        with open(swap_file_name, 'rb') as swap_file:
            hx = pickle.load(swap_file)
            # Load the state before the Pi restarted.
    else:
        # measure tare and save the value as offset for current channel
        # and gain selected. That means channel A and gain 128
        err = hx.zero()
        # check if successful
        if err:
            raise ValueError('Tare is unsuccessful.')

        reading = hx.get_raw_data_mean()
        if reading:  # always check if you get correct value or only False
            # now the value is close to 0
            print('Data subtracted by offset but still not converted to units:',
                  reading)
        else:
            print('invalid data', reading)

        # In order to calculate the conversion ratio to some units, in my case I want grams,
        # you must have known weight.
        input('Put known weight on the scale and then press Enter')
        reading = hx.get_data_mean()
        if reading:
            print('Mean value from HX711 subtracted by offset:', reading)
            known_weight_grams = input(
                'Write how many grams it was and press Enter: ')
            try:
                value = float(known_weight_grams)
                print(value, 'grams')
            except ValueError:
                print('Expected integer or float and I have got:',
                      known_weight_grams)

            # set scale ratio for particular channel and gain which is
            # used to calculate the conversion to units. Required argument is only
            # scale ratio. Without arguments 'channel' and 'gain_A' it sets
            # the ratio for current channel and gain.
            ratio = reading / value  # calculate the ratio for channel A and gain 128
            hx.set_scale_ratio(ratio)  # set ratio for current channel
            print('Ratio is set.')
        else:
            raise ValueError(
                'Cannot calculate mean value. Try debug mode. Variable reading:',
                reading)

        # If Raspberry Pi unexpectedly powers down, load the settings.
        print('Saving the HX711 state to swap file on persistant memory')
        with open(swap_file_name, 'wb') as swap_file:
            pickle.dump(hx, swap_file)
            swap_file.flush()
            os.fsync(swap_file.fileno())
            # flush, fsynch and close the file all the time.
            # This will write the file to the drive. It is slow but safe.
   
    while True:
        sleep(0)
        if ldr.value > 0.3 or ldr2.value > 0.3:
            if hx.get_weight_mean(10) < 150:
                barang_ref.update({
                    'status_keamanan': '2'
                })
                #print(ldr.value)
                #print(ldr2.value)
                print('Alert 2')
            else:
                barang_ref.update({
                    'status_keamanan': '1'
                })
                #print(ldr.value)
                #print(ldr2.value)
                print('Alert 1')
        else:
            barang_ref.update({
                'status_keamanan': '0'
            })
            #print(ldr.value)
            #print(ldr2.value)
            print('No Alert')
        #print(hx.get_weight_mean(20), 'g')


except (KeyboardInterrupt, SystemExit):
    print('Exiting..')

finally:
    GPIO.cleanup()
