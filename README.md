# TeslaChargingWithExcessSolar
Charge Tesla vehicles with Excess solar production compatible for Enphase Inverters

Description of the code:
- The script connects to
    - Sense Device
        - sense_energy module: receive excess solar energy production
        - senseLink module: communicate back to Sense to display charging status.
    - TeslaPy
        - Communicate with Tesla Vehicle
        - Get vehicle status, sends commands to start\stop charging, etc.
    - tplink-cloud-api
        - TP-Link has smart plugs that sense can detect and display usage of that plug
        - the scripts creates a dummy smart-plug called "Tesla", sends it back to sense to display the energy usage in Sense.

Intial Goal
- There is a bug with location info, even though the location coordinates are set, the scripts thinks vehicle is not at home, but somewhere else and doesn't initiate the charging.
- Check for bugs as to why the script stops when charger is not plugged-in or other general scenarios.
- The initialization starts with 2 Amp (Current) charging, then adjusts to available power. But, after initialization, charging should be paused for below 5A power availability. Power = Voltage * Current.

Features to be implemented: Multiple Vehicle Support.
- When both cars are plugged in under the Tesla account, check for the State of Charge (SoC).
- Initiate charging for the vehicle that has lower SoC.
- Scenario 1: If both vehicles are above 50% SoC, switch vehicles after every 5% charge added.
- Scenario 2: If one vehicle has less than 50% SoC, and the other has above 50% SoC, bring the lower SoC first to 50%, then go back to first logic.
- Scenario 3: If both vehicles are below 50%, initiate the lower one and bring it to 50%.
