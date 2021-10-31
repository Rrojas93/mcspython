#!/usr/bin/python3
'''
    mcs.py
    Author: Raul Rojas
    Contact: rrojas994@gmail.com
    Description: 
        A python script that helps manage a vanilla minecraft server from the 
        command line when the server is running in a background process. It 
        achieves this by sending commands to a named pipe that is created 
        upon setup or launching the server from this script and inspecting the 
        output latest log file in ./logs/latest.log. This script intends to 
        present all of the available management commands from the server to 
        a command line utility. This makes managing the server from a different 
        remote session possible as direct access to the server's command line is 
        not required.
'''

import os, sys, re, argparse, subprocess, time, psutil

TEMP_DIR = "tempfiles"
TEMP_DIR_PATH = TEMP_DIR
FIFO_IN_NAME = "mcsinput.fifo"
FIFO_IN_PATH = FIFO_IN_NAME
OUTPUT_FILE = "output"
OUTPUT_FILE_PATH = OUTPUT_FILE
SCRIPT_VERSION = "mcs.py version: v0.1.0"
COM_TIMEOUT = 5
args = None


def main():
    parse_arguments(sys.argv[1:])
    run_args()
    
def run_args():
    '''
        Performs any actions by the command line arguments.
    '''
    if(args.is_running):
        print(is_server_running())
    elif(args.stop):
        arg_stop()
    elif(args.setup):
        arg_setup()
    elif(args.run):
        arg_setup()
        arg_run()
    elif(args.send):
        arg_send()
    elif(args.list):
        arg_list()

def communicate(cmd:str)->str:
    '''
        Sends a command to the server and returns it's response.
    '''
    # Get the end of file position.
    with open(OUTPUT_FILE_PATH, 'r') as f:
        f.seek(0, 2)
        position = f.tell()
    
    # Send command to server.
    with open(FIFO_IN_PATH, 'w') as f: 
        f.write(cmd.strip() + '\n')
    
    # Wait for a response or timeout
    size = position
    t_start = time.time()
    while(size <= position and (time.time() <= (t_start + COM_TIMEOUT - 1))):
        with open(OUTPUT_FILE_PATH, 'r') as f: 
            f.seek(0, 2)
            size = f.tell()
        time.sleep(0.1)
        # print("waiting for response..")

    # Return response from output file
    #   Start reading output file from position acquired above.
    data = ''
    if(size > position):
        with open(OUTPUT_FILE_PATH, 'r') as f: 
            f.seek(position)
            data = f.read()
    return data

def is_server_running()->bool:
    '''
        Determine if the server is currently running. 
    '''
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd']):
        keywords = [
            'java',
            '-jar',
            'server.jar'
        ]
        # keywords = [ # for testing
        #     'someproc.py', 
        # ]
        cmd_args = proc.info.get('cmdline')
        results = list()
        for k in keywords:
            found = False
            for arg in cmd_args:
                if(k in arg):
                    found = True
            results.append(found) # keyword wasn't found in any of the arguments.

        if(all(results) and args.svr_dir == proc.info.get('cwd')):
            return True
    return False

def arg_setup():
    '''
        Performs initial setup. This can be safetly called multiple times as 
        nothing will be overwritten.
    '''

    if(not(os.path.exists(TEMP_DIR_PATH))):
        os.mkdir(TEMP_DIR_PATH)
    if(not(os.path.exists(FIFO_IN_PATH))):
        os.mkfifo(FIFO_IN_PATH)

def arg_run():
    '''
        Starts the Minecraft server.
    '''
    if(is_server_running()):
        exit("Server is already running.")
        return

    start_cmd = "java "
    if(args.jav_args):
        start_cmd += args.jav_args + ' '
    start_cmd += "-jar server.jar "
    if(args.svr_args):
        start_cmd += args.svr_args + " "
    # start_cmd = "./test/someproc.py" # For testing
    full_cmd = f"/usr/bin/tail -f {FIFO_IN_PATH} | {start_cmd} > {OUTPUT_FILE_PATH} & "
    try:
        proc = subprocess.Popen(full_cmd, shell=True)
    except Exception as e:
        exit("Error occured when attempting to start server: " + str(e))
    else:
        print(f"Server PID: {proc.pid}")

def arg_stop()->bool:
    '''
        Send the stop command to the server.
    '''
    if(is_server_running()):
        print(communicate("stop"))
    else:
        print("Server is not running.")

def arg_send():
    '''
        Sends a raw argument to the server and prints it's output.
    '''
    output = communicate(args.send)
    print(clean_output(output))

def arg_list():
    '''
        Lists the number of players currently logged into the server.
    '''
    output = clean_output(communicate("list"))
    if(re.match(r'there are \d+ of a max of \d+ players online:', output.lower())):
        output_spl = output.split()
        if(output_spl[2].isnumeric()):
            num_online = int(output_spl[2])
        if(output_spl[7].isnumeric()):
            num_max = int(output_spl[7])
        print(f"{num_online}/{num_max} Players Online:")
        if(num_online > 0):
            for player in output.split(':')[-1].split(','):
                print(player.strip())

def terminal(cmd:str)->tuple:
    '''
        Runs a terminal command as a child process and returns the output as a 
        tuple (out, err).
    '''
    print("Running: " + cmd)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = proc.communicate()
    return (out.decode('utf-8').strip(), err.decode('utf-8').strip())

def clean_output(svr_output:str)->str:
    '''
        Cleans the server output.
    '''
    # Remove the first two columns of output (time stamp and log type)
    return '\n'.join([':'.join(line.split(':')[3:]).strip() for line in svr_output.splitlines()])

def dir_path(dir_path):
    '''
        Determines if the path is a directory.
    '''
    dir_path = dir_path.replace('\"', '')
    if(os.path.isdir(dir_path)):
        return dir_path
    else:
        raise NotADirectoryError(dir_path)

def parse_arguments(arg_list:list):
    '''
        Parses the command line arguments.
    '''
    parser = argparse.ArgumentParser(
        description="A command line management utility for vanilla minecraft servers.",
        prefix_chars="-"
    )

    parser.add_argument("--setup",
        action="store_true",
        help="Performs initial setup."
    )

    parser.add_argument("--run", "--start",
        action='store_true',
        help="Starts the server if it is not already running. This script may not work correctly unless the server is started by this script."
    )

    parser.add_argument("--stop", "-stop",
        action='store_true',
        help="Sends a stop request to the server."
    )

    parser.add_argument("--send",
        type=str,
        help="Send a raw string command to the server and print it's output. Should be enclosed in quotes."
    )

    parser.add_argument("--is_running",
        action='store_true',
        help="Determines if the server is currently running."
    )

    parser.add_argument("--svr_dir",
        type=dir_path,
        default=os.path.abspath(os.path.dirname(__file__)),
        help="Sets the server directory."
    )

    parser.add_argument("--jav_args",
        type=str,
        help="The command line arguments to add in the server start command for java. Should be a single quoted string."
    )

    parser.add_argument("--svr_args",
        type=str,
        default="nogui",
        help="The command line arguments to add in the server start command. Should be a single quoted string."
    )

    parser.add_argument("-v", "-V", "--version",
        action='version',
        version=SCRIPT_VERSION,
        help="Show script version number and exit."
    )

    # Minecraft Server CLI Commands: 
    parser.add_argument("-list",
        action="store_true",
        help="List players on the server."
    )

    global args
    args = parser.parse_args(arg_list)

    if(os.path.exists(args.svr_dir)):
        os.chdir(args.svr_dir)
    else:
        exit("Server directory does not exist.")
    
    global TEMP_DIR_PATH
    global FIFO_IN_PATH
    global OUTPUT_FILE_PATH
    TEMP_DIR_PATH = os.path.join(args.svr_dir, TEMP_DIR)
    FIFO_IN_PATH = os.path.join(TEMP_DIR_PATH, FIFO_IN_NAME)
    OUTPUT_FILE_PATH = os.path.join(TEMP_DIR_PATH, OUTPUT_FILE)

if __name__ == "__main__":
    main()