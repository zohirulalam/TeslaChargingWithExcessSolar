"""
 TesSense w/ SenseLink  -Randy Spencer 8/2023 Full Version 1.1
 Python charge monitoring utility for those who own the Sense Energy Monitor
 Uses Sense stats for production and utilization of electricity to control
 your first Tesla's AC charging to charge only with excess production.
 Simply plug in your car, update your info below, and type> python3 tessense.py

Tesla 240v charging is reported to Sense via TP-LinkCloud for logging and display
Other KASA devices can be controlled via SenseLink using the ControlList below, as
more solar is available more devices are turned on and vice-versa
"""

import asyncio, logging, sys, time
from datetime import datetime
from zoneinfo import ZoneInfo
TZ = ZoneInfo('US/Pacific')                                 # TimeZone name
LAT,LON = 34.0, -117.0                                      # 3 decimal charing location (Home: 34.0013655,-117.8497632)
MINRATE = 5                                                 # Minimum amps you can set the charger to
SLEEP_UNTIL, SLEEP_AFTER = 8, 18                            # 8AM and 6PM local time
USERNAME_TESLA = 'md.alom@me.com'                           # Sense's and TPLink's and Tesla's login
USERNAME_SENSE = 'zohirulalam@gmail.com'                    # Sense's and TPLink's and Tesla's login
USERNAME_KASA = 'zohirulalam@gmail.com'                     # Sense's and TPLink's and Tesla's login
SENSEPASS = 'sutFow-momny4-zedcax'                          # Sense's password, Tesla will prompt for it's own
KASAPASS = 'qadTos-xyvxu9-dumnyr'                           # TPLink's password
CONTROLLIST = 0 #["Lamp", "TV", "Heater"]                   # Replace '0' with a list of your devices to control


REDTXT, BLUTXT, NORMTXT = '\033[31m', '\033[34m', '\033[m'
REDBG, GRNBG, NORMBG = '\033[101m', '\033[102m', '\033[0m'

#/c Set stdout as logging handler
root_log = logging.getLogger()
root_log.setLevel(logging.ERROR)                            # set to ERROR or WARNING or INFO or DEBUG
handler = logging.StreamHandler(sys.stdout)

# To install support module:
# pip3 install sense_energy (to receive Sense data)
from sense_energy import Senseable

# pip3 install teslapy (to talk to your Tesla)
import teslapy

# pip3 install senselink (to send Tesla usage to your Sense)
from senselink import SenseLink
from senselink.plug_instance import PlugInstance
from senselink.data_source import MutableSource

# pip3 install tplink-cloud-api (to talk to your Kasa plugs)
from tplinkcloud import TPLinkDeviceManager, TPLinkDeviceManagerPowerTools


def printerror(error,data):                                 # Error message with truncated data
    print(str(data).split("}")[0],"}\n", datetime.now(TZ).strftime("%a %I:%M %p"), error)

def printmsg(msg):                                          # Timestamped message
    print(" ", datetime.now(TZ).strftime("%a %I:%M %p"), msg)
    
def print_temp(car, cardata):                               # Car temp and fan status
    if cardata['climate_state']['inside_temp'] > 35:        # 35°C = 95°F
        print("+", end='')
        if not cardata['vehicle_state']['fd_window']:       # Not Open
            print(GRNBG, "Vent",NORMBG, end=' ')
            vent(car, 'vent')
    else:
        if cardata['vehicle_state']['fd_window']:           # Open
            print(REDBG, "Close", NORMBG,end=' ')
            vent(car, 'close')
    print(car.temp_units(cardata['climate_state']['inside_temp'])+', ', end='')
    print(cardata['climate_state']['fan_status'],'(fan), ', end='')
    print(cardata['climate_state']['cabin_overheat_protection_actively_cooling'],'(cop)', end='')

def print_update(chargedata, fast):                         # Display stats at every % change
    print("\nLevel:",
        chargedata['battery_level'], "%, Limit",
        chargedata['charge_limit_soc'], "%,",
        chargedata['charge_rate'], "MPH",
        chargedata['charger_voltage'], "Volts",
        chargedata['charge_energy_added'], "kWh added,")
    if fast: print("Rate:",
        chargedata['charger_power'], "KWs",
        chargedata['conn_charge_cable'],
        chargedata['fast_charger_type'],
        chargedata['minutes_to_full_charge'], "Minutes remaining\n")
    else: print(chargedata['charger_actual_current'], "of a possible",
        chargedata['charge_current_request_max'], "Amps,",
        chargedata['time_to_full_charge'], "Hours remaining\n")
        
def send_cmd(car, cmd, err):                                # Send cmd to Start or Stop charging
    try: car.command(cmd)
    except teslapy.VehicleError as e:
        print(err)
        printmsg(e)

def set_amps(car, newrate, err):                            # Increase or decrease charging rate
    try: car.command('CHARGING_AMPS', charging_amps=newrate)
    except teslapy.VehicleError as e: printerror("V: " + err, e)
    except teslapy.HTTPError as e: printerror("H: " + err, e)

def set_rate(car, newrate, msg):
    print(msg, "charging to", newrate, "amps")
    if newrate == 2: newrate = 1                            # For API a newrate of 3=3, 2=3, 1=2
    set_amps(car, newrate, "Failed to change")              #  so to set to 2 newrate must be 1
    if newrate < 5:                                         # if under 5 amps you also need to
        set_amps(car, newrate, "Failed to change 2")        #  send it twice:
        
def start_charging(car):
    try:                                                    # Collect new data from Tesla
        state = car.get_vehicle_data()['charge_state']['charging_state']
    except teslapy.HTTPError as e:
        printerror("Tesla failed to update, please wait a minute...", e)
    else:
        print(GRNBG + "Starting" + NORMBG + " charge at 2 Amps")
        if state != "Charging":
            send_cmd(car, 'START_CHARGE', "Won't start charging")
            set_amps(car, 1, "Won't start charging 2")
            set_amps(car, 1, "Won't start charging 3")

def stop_charging(car):
    try:                                                    # Collect new data from Tesla
        state = car.get_vehicle_data()['charge_state']['charging_state']
    except teslapy.HTTPError as e:
        printerror("Tesla failed to update, please wait a minute...", e)
    else:
        if state == "Charging":
            print(REDBG + "Stopping" + NORMBG + " charge")
            send_cmd(car, 'STOP_CHARGE', "Failed to stop")
    try:
        if car.get_vehicle_data()['vehicle_state']['fd_window']:    # Window's Open
            vent(car, 'close')
    except: pass

def vent(car, command):
    try: car.command('WINDOW_CONTROL', command=command, lat=LAT, lon=LON)
    except teslapy.VehicleError as e: printmsg("Window_Control Failed " + str(e))
    else: print(REDTXT + "Windows will now", command + NORMTXT)

def wake(car):
    printmsg("Waking...")
    try: car.sync_wake_up()
    except teslapy.VehicleError as e:
        printerror("Failed to wake", e)
        return(False)
    else : return(True)
    
    
async def sleepnow(min):
    for x in range(min): await asyncio.sleep(60)

async def sleepovernight():
    if not SLEEP_UNTIL <= datetime.now(TZ).hour < SLEEP_AFTER:  # Not Daytime 8am - 8pm
        printmsg(BLUTXT + 'Nighttime,' + NORMTXT + " sleeping until morning...")
        while not SLEEP_UNTIL <= datetime.now(TZ).hour < SLEEP_AFTER:
            await sleepnow(2)
        printmsg(REDTXT + "Good Morning!" + NORMTXT)
        
async def TesSense():
    await asyncio.sleep(.1)
    global minwatts, power_diff, timeout, volts, mutable_plug
    in_service = minwatts = power_diff = volts = 0
    fullORunplugged = lastemp = level = limit = newrate = rate = 0

    retry = teslapy.Retry(total = 3,status_forcelist = (500, 502, 503, 504))
    with teslapy.Tesla(USERNAME_TESLA, retry=retry, timeout = 30) as tesla:
        mycar = tesla.vehicle_list()[0]

        print("Starting connection to", mycar.get_vehicle_summary()['display_name'], end='')
        if not mycar.available():
            print("... []")
        else:
            try: cardata=mycar.get_vehicle_data()
            except: print("Error reading CarData")
            else:
                print("... [", round(cardata['drive_state']['latitude'], 3), ",", round(cardata['drive_state']['longitude'], 3), "]")
        try:
            print(" last seen " + mycar.last_seen(), "at", str(mycar['charge_state']['battery_level']) + "% SoC")
        except:
            print(" last seen in the future at some % SoC")

        while True:                                         # Main loop with night time carve out
            try:
                in_service = mycar.get_vehicle_summary()['in_service'] # if car is in service mode at Tesla
            except:
                print("Failed to check In-Service status on Tesla")
            else:
                if in_service:
                    printmsg(" Sorry. Currently this car is in Service Mode")
                    await sleepnow(20)
                    continue
                    
            if 5 < timeout < 100:                           # If Sense Times Out
                timeout += 100                              # Prevent looping on stop_charging()
                stop_charging(mycar)                        # Stop Tesla Charging when Sense offline
                await sleepnow(1)
                continue

            while volts == 0 : await asyncio.sleep(1)       # Syncing with UpdateSense()
            
            if not mycar.available():                       # Car is sleeping
                await sleepovernight()
                if power_diff > minwatts and not fullORunplugged:
                    if wake(mycar):                         # Initial daytime wake() to get status
                        rate = newrate = 0                  # Reset rate as things will have changed
                        continue
                    else:
                        print("Wake error. Sleeping 20 minutes and trying again")
                        await sleepnow(20)           # Give the API a chance to find the car
                        continue
                else:
                    if fullORunplugged==1: print("Full-", end='')
                    elif fullORunplugged==2: print("Unplugged-", end='')
                    print("Sleeping, free power is", power_diff, "watts")
                    if fullORunplugged:
                        printmsg(" Wait twenty minutes...")
                        for x in range(20):
                            await asyncio.sleep(60)
                            try:
                                if mycar.available(): break
                            except:
                                print("Failed availability check")
                        continue
            else:                                           # Car is awake
                try:
                    cardata = mycar.get_vehicle_data() # Collect new data from Tesla
                except teslapy.HTTPError as e:
                    printerror("Tesla failed to update, please wait a minute...", e)
                    await asyncio.sleep(60)                 # Error: Return to top of order
                    continue
                else: chargedata = cardata['charge_state']

                if chargedata['fast_charger_present']:
                    printmsg("DC Fast Charging...")
                    print_update(chargedata,1)
                    await sleepnow(2)                       # Loop while Supercharging back to top
                    continue

# Prevent remote charging issues
                # if 'latitude' in cardata['drive_state']:    
                    # printmsg(cardata['drive_state'])
                    # printmsg(round(cardata['drive_state']['latitude'], 0))
                    # printmsg(round(cardata['drive_state']['longitude'], 0))
                    # if round(cardata['drive_state']['latitude'], 0) == LAT and \
                       # round(cardata['drive_state']['longitude'], 0) == LON :
                        # await sleepovernight()
                    # else:                                   # Away from home
                        # print(round(cardata['drive_state']['latitude'], 3), \
                             # round(cardata['drive_state']['longitude'], 3), end='')
                        # printmsg("Away from home. Wait 5 minutes")
                        # fullORunplugged = 2                 # If it's not at home it's unplugged
                        # await sleepnow(5)
                        # continue
                # else:
                    # print(REDTXT + "Error: No Location" + NORMTXT)

                if not chargedata['charging_state'] == "Charging":    # Not charging, check if need to start
                    mutable_plug.data_source.power = 0                # Let Sense know we are not charging
                    if power_diff>minwatts and not fullORunplugged:   # Minimum free watts to start charge
                        if chargedata['battery_level'] >= chargedata['charge_limit_soc']:
                            print(REDBG + "Full Battery" + NORMBG)
                            print_update(chargedata,0)
                            fullORunplugged = 1                       # Set Status to Battery Full
                        elif chargedata['charging_state'] == "Disconnected":
                            print(REDTXT + "Charger is not plugged in." + NORMTXT + " Excess power is at", power_diff, "watts")
                            fullORunplugged = 2                       # Set Status to Unplugged
                        else:                                         # Plugged-in and battery is not full
                            start_charging(mycar)
                            mutable_plug.data_source.power = 2 * volts  # Let Sense know we ARE charging
                    else:
                        print("Not Charging, free power is at",power_diff,"watts")
                        if cardata['vehicle_state']['fd_window']:     # Don't leave windows open
                            vent(mycar,'close')
                else:                                                 # Charging, update status
                    if chargedata['battery_level'] < chargedata['charge_limit_soc']:
                        fullORunplugged = 0                           # Mark it as NOT full and AS plugged-in

                    if  level != chargedata['battery_level'] or limit != chargedata['charge_limit_soc']:
                        level, limit = chargedata['battery_level'], chargedata['charge_limit_soc']
                        print_update(chargedata, 0)                   # Display charging info every % change
                        
                    rate=chargedata['charger_actual_current']
                    if volts : newrate = min(rate + int(power_diff / volts), chargedata['charge_current_request_max'])
                                                           
                    print("Charging at", rate, "amps, with", power_diff, "watts surplus")

                    if newrate < MINRATE:                   # Stop charging as there's no free power
                        stop_charging(mycar)
                        newrate = 0
                    elif newrate > rate:                    # Charge faster with any surplus
                        set_rate(mycar, newrate, "Increasing")
                    elif newrate < rate:                    # Charge slower due to less availablity
                        set_rate(mycar, newrate, "Slowing")
                    mutable_plug.data_source.power = newrate * volts    # Update Sense with current info (Ha!)
                    if lastemp != cardata['climate_state']['timestamp']:
                        lastemp = cardata['climate_state']['timestamp']
                        print_temp(mycar, cardata)                      # Display cabin temp and fan use

            printmsg("  Next check in 1 minutes...")               # Message after every complete loop
            await sleepnow(1)                        # Fastest the Sense API will update is 30 sec.


async def CheckTPLink():                                    # Based on github.com/piekstra/tplinkcloud-service
    def printmsg(msg):                                      # Wrap a balloon around each output from CheckTPLink()
        if msg.isprintable():
            print("=" * (len(max(msg.split('\n'), key=len)) - 12) + datetime.now(TZ).strftime("%a %I:%M %p"))
            print(msg)
            print("-" * len(max(msg.split('\n'), key=len)))
        else: print("===" + datetime.now(TZ).strftime("%a %I:%M %p") + "\n" + msg + "\n---")
            
    await asyncio.sleep(.01)
    print("=" * 29 + "\nLooking for TPLink smartplugs\n" + "-" * 29)
    device_manager = TPLinkDeviceManager(USERNAME_KASA, KASAPASS)                # Sign in
    power_manager = TPLinkDeviceManagerPowerTools(device_manager)           # Get emeter base
    devices = await power_manager.get_emeter_devices()                      # Get devices list
    if not devices: printmsg("No TPLink (KASA) E-Meter devices found")      # Print Error and Exit
    else:                                                                   # Display devices found
        print("=" * 70)
        if CONTROLLIST:                                                     # Skip list if CL already built
            print("Found " + str(len(devices)) + " TP-Link E-Meter devices")
            print("Controlled devices:")
            for nameddevice in CONTROLLIST:                                 # Controlled Devices Listing
                device = await power_manager.get_devices_power_usage_realtime(nameddevice)
                unit = await device_manager.find_device(nameddevice)
                try: print(nameddevice + " watts = " + str(round(device[0].data.power_mw if device[0].data.power_mw < 1000 else device[0].data.power_mw / 1000)))
                except: print(nameddevice + " = offline")
        else:
            print("Found " + str(len(devices)) + " TP-Link E-Meter devices:")
            for i, device in enumerate(devices, 1):
                print('{:25}'.format(device.device_info.alias), end='' if i % 3 else '\n')
            if i % 3: print()                                               # Trailing CR if not one above
        print("-" * 70)
        
        thishour = datetime.now(TZ).hour
        while True:                                        # Main Loop
            while not SLEEP_UNTIL <= datetime.now(TZ).hour < SLEEP_AFTER:   # Sleep Overnight
                await asyncio.sleep(120)

            if thishour != datetime.now(TZ).hour:           # Display every hour
                thishour = datetime.now(TZ).hour            # Shows the code's still going
                print("=" * 10)                             # Won't correctly show midnight so only run after 8am
                print(str(thishour - 12 if thishour > 12 else thishour) + " o'clock")
                print("-" * 10)

            output=''         # Build output message to display if CONTROLLIST devices are using much power
            for nameddevice in CONTROLLIST:
                try:                                        # Get Unit info from Device Name
                    unit = await device_manager.find_device(nameddevice)
                except:
                    printmsg("Cannot find TPLink device " + nameddevice)
                    break                                   # Move to the next device

                if unit.device_info.status:                 # Check if unit is online
                    try:
                        device = await power_manager.get_devices_power_usage_realtime(nameddevice)
                    except:
                        printmsg("Cannot find TPLink device status for " + nameddevice)
                        continue                            # Move to the next device
                        
                    if not hasattr(device[0].data, 'voltage_mv'):           # Check expected data structure
                        printmsg("Unexpected structure in " + nameddevice)
                    else:
                        factor=1000 if device[0].data.voltage_mv > 1000 else 1
                        watts = device[0].data.power_mw / factor   # If old model plug convert milliwatts to watts

                        if await unit.is_off() and power_diff > 750 :
                            printmsg(GRNBG + "Powering on" + NORMBG + ": " + nameddevice)
                            await unit.power_on()
                                                    # Power off nameddevice if it is using more than 5 watts and solar power isn't covering at least half of it's usage
                        elif watts > 5 and power_diff < -(watts / 2):
                            printmsg(REDBG + "Powering off" + NORMBG + ": " + nameddevice + "\nBecause " + str(power_diff) + " watts is less than " + str(-(round(watts / 2))) + " watts threshold")
                            await unit.power_off()
                                                                
                        elif watts > 5:                     # Display the stats for each running device
                            if timeout > 20:
                                print("Sense timeout - " + REDBG + "Powering off " + NORMBG + nameddevice)
                                await unit.power_off()
                            if output: output += "\n"
                            output = output + nameddevice + " = " + str(round(device[0].data.voltage_mv / factor, 2)) + " volts, " + str(round(device[0].data.power_mw/factor,2)) +    " watts, " + str(round(device[0].data.current_ma / factor, 2)) + " amps, " + str(round(device[0].data.total_wh / factor, 2)) + " 7-day kWhs"
                                                            # total_wh resets weekly to that day's total
            if output:
                printmsg(output)
            await asyncio.sleep(180)


async def UpdateSense():                                    # Update Sense info via Sense API
    global minwatts, power_diff, timeout, volts
    timeout = 0
    print("Initating connection to Sense...")
    sense=Senseable(wss_timeout=30,api_timeout=30)
    sense.authenticate(USERNAME_SENSE, SENSEPASS)
    while True:
        try:
            #sense.update_trend_data()
            sense.update_realtime()
        except:
            timeout += 1
            power_diff = 0
            if timeout > 2:
                printmsg(REDTXT + ">>Sense Timeout #" + str(timeout) + NORMTXT)
        else:
            timeout = 0
            volts = int(sense.active_voltage[0] + sense.active_voltage[1])
            power_diff = int(sense.active_solar_power-sense.active_power)
            minwatts = MINRATE * volts                      # Calc minimum watts needed to start charging
        await asyncio.sleep(60)                             # Fastest the Sense API will update is 30 sec.


async def main():                                           # Much thanks to cbpowell for this SenseLink code:
    # Create controller, with NO config
    global mutable_plug
    controller = SenseLink(None)
    
    # Create a PlugInstance, setting at least the name for Sense and MAC
    mutable_plug = PlugInstance("mutable", alias="Tesla", mac="53:75:31:f8:3a:8c")
    # Create and assign a Mutable Data Source to that plug
    mutable_data_source = MutableSource("mutable", None)
    mutable_plug.data_source = mutable_data_source
    
    # Add that plug to the controller
    controller.add_instances({mutable_plug.identifier:mutable_plug})

    # Pass plug to TesSense, where TesSense can update it
    Sen_task = UpdateSense()
    Tes_task = TesSense()
    TP_task  = CheckTPLink()

    # Get SenseLink tasks to add these
    tasks = controller.tasks
    tasks.add(Sen_task)                                     # Spawn the UpdateSense() function as a coroutine
    tasks.add(Tes_task)                                     # Spawn the TesSense() function as another coroutine
    if CONTROLLIST: tasks.add(TP_task)                      # Spawn the CheckTPLink() function also, if needed
    tasks.add(controller.server_start())

    logging.info("Starting controller.tasks")
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n Interrupt received\n")
