# TeslaChargingWithExcessSolar
Charge Tesla vehicles with Excess solar production compatible for Enphase Inverters

Intial Goal
- Check for bugs as to why the script stops when charger is not plugged-in or other general scenarios.

Features to be implemented: Multiple Vehicle Support.
- When both cars are plugged in under the Tesla account, check for the State of Charge (SoC).
- Initiate charging for the vehicle that has lower SoC.
- Scenario 1: If both vehicles are above 50% SoC, switch vehicles after every 5% charge added.
- Scenario 2: If one vehicle has less than 50% SoC, and the other has above 50% SoC, bring the lower SoC first to 50%, then go back to first logic.
- Scenario 3: If both vehicles are below 50%, initiate the lower one and bring it to 50%.
