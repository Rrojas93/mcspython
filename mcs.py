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

import os, sys, re, argparse, subprocess, time, psutil, json

# Path names
TEMP_DIR = "tempfiles"
TEMP_DIR_PATH = TEMP_DIR
FIFO_IN_NAME = "mcsinput.fifo"
FIFO_IN_PATH = FIFO_IN_NAME
OUTPUT_FILE = "output"
OUTPUT_FILE_PATH = OUTPUT_FILE
SERVER_CMDS_FILE = 'servercmds.json'
SERVER_CMDS_FILE_PATH = SERVER_CMDS_FILE

# Other constants
SCRIPT_VERSION = "mcs.py version: v0.0.1"
COM_TIMEOUT = 5

# Globals
args = None


def main():
    parse_arguments(sys.argv[1:])
    run_args()
    # arg_update_cmd_list()
    
def run_args():
    '''
        Performs any actions by the command line arguments.
    '''
    if(args.stop):
        arg_stop()
    elif(args.setup):
        arg_setup()
    elif(args.run):
        arg_setup()
        arg_run()
    elif(args.raw):
        arg_raw()
    else:
        exit("Nothing to do. Did you forget an argument?")

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
        # exit("Server is already running.")
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

def arg_raw():
    '''
        Sends a raw argument to the server and prints it's output.
    '''
    print(communicate(args.raw))

def arg_update_cmd_list():
    '''
        Updates the command list from the server.
    '''
    if(not(is_server_running())):
        exit("The server must be running to perform this command.")
    
    help_text = communicate('help')

    # with open('test/testfiles/helpoutput.txt', 'r') as f:
    #     help_text = f.read()

    data = parse_server_cmds(help_text)
    with open(SERVER_CMDS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def terminal(cmd:str)->tuple:
    '''
        Runs a terminal command as a child process and returns the output as a 
        tuple (out, err).
    '''
    print("Running: " + cmd)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = proc.communicate()
    return (out.decode('utf-8').strip(), err.decode('utf-8').strip())

def parse_server_cmds(help_output:str)->dict:
    '''
        Parses the server commands and returns a dictionary of the commands.

        Data Structure: 
        ```
        {
            cmd_name: {
                'aliases': [],
                'arguments': [
                    {
                        'literal': bool
                        'multiple': bool
                        'choices': [],
                    }
                ]
            }
        }
        ```
    '''
    data = dict()
    aliases = list()
    for line in help_output.splitlines():
        logspl = line.split('/')
        if('->' in logspl[-1]):
            aliases.append(logspl[-1])
            continue
        if(len(logspl) == 3):
            items = logspl[-1].split(' ')
            cmd = items[0]
            data[cmd] = {
                'aliases': list(),
                'arguments': list(),
                'help_txt': ' '.join(items[1:])
            }
            for arg in items[1:]: 
                multiple = False
                if(re.match(r'\(.*\)', arg)):
                    # contains multiple choices.
                    arg = arg.replace('(', '').replace(')', '')
                    choices = arg.split('|')
                elif(re.match(r'\[.*\]', arg)):
                    arg = arg.replace('[', '').replace(']', '')
                    choices = arg.split('|')
                    multiple = True
                
                # If any choices contain a non literal value, we can't provide strict choices.
                literal = not(any([re.match(r'<\w*>', c) is not None for c in choices]))
                data[cmd]['arguments'].append(
                    {
                        'literal': literal,
                        'multiple': multiple,
                        'choices': choices
                    }
                )
    for entry in aliases:
        cmd = entry.split()[-1]
        alias = entry.split()[0]
        if(data.get(cmd)):
            data[cmd]['aliases'].append(alias)
    return data

def load_server_cmds(parser:argparse.ArgumentParser, server_dir:str)->argparse.ArgumentParser:
    '''
        Loads the server commands if they're available and adds them to the parser.

        Parameters: 
            parser: The parser object to add arguments to.

            server_dir: The server directory path.
    '''
    svr_cmd_file = os.path.join(server_dir, TEMP_DIR, SERVER_CMDS_FILE)
    if(not(os.path.exists(svr_cmd_file))):
        print("Update server commands with: --update_cmd_list")
        return parser
    
    try: 
        with open(svr_cmd_file, 'r') as f:
            cmd_data = json.load(f)
    except Exception as e: 
        print("An error occured when loading server command list. Please update with: --update_cmd_list")
        return parser
    
    for cmd in list(cmd_data.keys()):
        args = [f'--mcs_{cmd}']
        if(cmd_data[cmd]['aliases']):
            for alias in cmd_data[cmd]['aliases']:
                args.append(f'--mcs_{alias}')
        helptxt = cmd_data[cmd]['help_txt']
        if(any(a['multiple'] for a in cmd_data[cmd]['arguments']) and (len(cmd_data[cmd]['arguments']) > 0)):
            nargs = '+'
        elif(cmd_data[cmd]['arguments']):
            nargs = len(cmd_data[cmd]['arguments'])
        else:
            nargs = None
        if(all(a['literal'] for a in cmd_data[cmd]['arguments']) and (len(cmd_data[cmd]['arguments']) > 0)):
            choices = [c for a in cmd_data[cmd]['arguments'] for c in a['choices']]
        else:
            choices = None
        parser.add_argument(*args,
            type=str,
            nargs=nargs,
            choices=choices,
            help=helptxt
        )
    return parser

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

    parser.add_argument("--raw",
        type=str,
        help="Send a raw string command to the server and print it's output. Should be enclosed in quotes."
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

    parser.add_argument("--update_cmd_list",
        action='store_true',
        help="Pulls the available commands from the server and updates the command list in this script."
    )

    parser.add_argument("-v", "-V", "--version",
        action='version',
        version=SCRIPT_VERSION,
        help="Show script version number and exit."
    )

    # Need to preemptively look for server directory to look for existing server commands.
    svr_dir = os.path.abspath(os.path.dirname(__file__))
    if('--svr_dir' in arg_list):
        ind = arg_list.index('--svr_dir')
        if(len(arg_list) > ind):
            svr_dir = arg_list[ind + 1]

    parser = load_server_cmds(parser, svr_dir)

    global args
    args = parser.parse_args(arg_list)

    if(os.path.exists(args.svr_dir)):
        os.chdir(args.svr_dir)
    else:
        exit("Server directory does not exist.")
    
    global TEMP_DIR_PATH
    global FIFO_IN_PATH
    global OUTPUT_FILE_PATH
    global SERVER_CMDS_FILE_PATH
    TEMP_DIR_PATH = os.path.join(args.svr_dir, TEMP_DIR)
    FIFO_IN_PATH = os.path.join(TEMP_DIR_PATH, FIFO_IN_NAME)
    OUTPUT_FILE_PATH = os.path.join(TEMP_DIR_PATH, OUTPUT_FILE)
    SERVER_CMDS_FILE_PATH = os.path.join(TEMP_DIR_PATH, SERVER_CMDS_FILE)


if __name__ == "__main__":
    main()