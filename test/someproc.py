#!/usr/bin/python3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
OUTPUT_LOG = os.path.join(BASE_DIR, "test.log")

def printlog(str):
    '''
        prints and logs
    '''
    print(str, flush=True)
    with open(OUTPUT_LOG, 'a') as f: 
        f.write(str)

printlog("started some process.\n")

while(True):
    inp = input("Enter Command: ")
    printlog(f"Received Command: {inp}\n")
    if('exit' in inp):
        break