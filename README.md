# mcspython
A python script created to help manage a vanilla Minecraft server.

# Quick Setup
This script assumes you have already done the following when integrating into a 
minecraft server: 
* The server is already in a working state.
* A world has already been created. 
* You have already accepted the eula.txt for the server.

## Step 1: Clone
Clone the repository into your server directory: 
``` bash
host$ cd /path/to/your/minecraft/server/directory 
host$ git clone https://github.com/Rrojas93/mcspython.git
host$ cp ./mcspython/mcs.py .
host$ sudo chmod +x mcs.py  # If not already executable.
```

## Step 2: Install Python Requirements
```bash
host$ python3 -m pip install ./mcspython/requirements.txt
```

## Step 3: Setup
Run the setup command: 
```bash
host$ mcs.py --setup
```

## Step 4: Start The Server
```bash
# The server should not be running. If it is, stop it manually (This scripts --stop command won't work).
host$ mcs.py --run
# Done
```

