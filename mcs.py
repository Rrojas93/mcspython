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

MCS_DIR = "mcspython"
MCS_DIR_PATH = MCS_DIR
FIFO_IN_NAME = "mcsinput.fifo"
FIFO_IN_PATH = FIFO_IN_NAME
SCRIPT_VERSION = "mcs.py version: v0.0.1"
args = None


def main():
    parse_arguments(sys.argv[1:])
    run_args()
    

def run_args():
    '''
        Performs any actions by the command line arguments.
    '''
    if(args.setup):
        arg_setup()
    elif(args.run):
        arg_setup()
        arg_run()


def arg_setup():
    '''
        Performs initial setup. This can be safetly called multiple times as 
        nothing will be overwritten.
    '''

    if(not(os.path.exists(MCS_DIR_PATH))):
        os.mkdir(MCS_DIR_PATH)
    if(not(os.path.exists(FIFO_IN_PATH))):
        os.mkfifo(FIFO_IN_PATH)

def is_server_running()->bool:
    '''
        Determine if the server is currently running. 
    '''
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd']):
        # keywords = [
        #     'java',
        #     '-jar',
        #     'server.jar'
        # ]
        keywords = [
            'someproc.py', 
        ]
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

def arg_run():
    '''
        Starts the Minecraft server.
    '''
    if(is_server_running()):
        exit("Server is already running.")

    # start_cmd = "java "
    # if(args.jav_args):
    #     start_cmd += args.jav_args + ' '
    # start_cmd += "-jar server.jar "
    # if(args.svr_args):
    #     start_cmd += args.svr_args + " "
    start_cmd = "./test/someproc.py"
    output_file = "./mcspython/output.txt"
    print("someproc exists?: " + str(os.path.exists(start_cmd)))
    print("fifo in exists?: " + str(os.path.exists(FIFO_IN_PATH)))
    print("output file exist?: " + str(os.path.exists(output_file)))
    full_cmd = f"/usr/bin/tail -f {FIFO_IN_PATH} | {start_cmd} > {output_file} & "
    try:
        proc = subprocess.Popen(full_cmd, shell=True)
    except Exception as e:
        exit("Error occured when attempting to start server: " + str(e))
    else:
        # print(f"tail proc: {tail_proc.pid}")
        print(f"server proc: {proc.pid}")

def arg_stop()->bool:
    '''
        Send the stop command to the server.
    '''
    pass

def terminal(cmd:str)->tuple:
    '''
        Runs a terminal command as a child process and returns the output as a 
        tuple (out, err).
    '''
    print("Running: " + cmd)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = proc.communicate()
    return (out.decode('utf-8').strip(), err.decode('utf-8').strip())

def parse_server_cmds(help_output:str):
    '''
        
    '''
    pass

def parse_arguments(arg_list:list):
    '''
        Parses the command line arguments.
    '''
    parser = argparse.ArgumentParser(
        description="A command line management utility for vanilla minecraft servers."
    )

    parser.add_argument("--setup",
        action="store_true",
        help="Performs initial setup."
    )

    parser.add_argument("--run",
        action='store_true',
        help="Starts the server if it is not already running. This script may not work correctly unless the server is started by this script."
    )

    parser.add_argument("--stop",
        action='store_true',
        help="Sends a stop request to the server."
    )

    parser.add_argument("--run_args",
        nargs='*',
        help="Ignore this, this is used internally."
    )

    parser.add_argument("--svr_dir",
        type=str,
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

    global args
    args = parser.parse_args(arg_list)

    if(os.path.exists(args.svr_dir)):
        os.chdir(args.svr_dir)
    else:
        exit("Server directory does not exist.")
    
    global MCS_DIR_PATH
    global FIFO_IN_PATH
    MCS_DIR_PATH = os.path.join(args.svr_dir, MCS_DIR)
    FIFO_IN_PATH = os.path.join(MCS_DIR_PATH, FIFO_IN_NAME)

if __name__ == "__main__":
    main()