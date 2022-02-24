#! /usr/bin/env python
"""Script to replace hostname"""

from getpass import getpass
from re import findall
from nornir import InitNornir
from nornir_scrapli.tasks import send_command
from nornir.core.exceptions import NornirExecutionError
from nornir_utils.plugins.functions import print_result

def get_data_task(task):
    """
    Task to send commands to Devices via Nornir/Scrapli
    """
    result = task.run(task=send_command, command="show version")
    task.host["facts"] = result.scrapli_response.genie_parse_output()

def main():
    ### PROGRAM VARIABLES ###
    username = input("Username: ")
    password = getpass(prompt="Password: ", stream=None)
    host_tuple_list = []

    print("Initializing connections to devices...")
    try:
        nr = InitNornir(config_file="config/config.yml", core={"raise_on_error": True})
        nr.inventory.defaults.username = username
        nr.inventory.defaults.password = password
        results = nr.run(task=get_data_task)
    except NornirExecutionError as e:
        print(f"Unable to run task on host: {e}")
        print("Possible authentication issue")

    print("Parsing generated output...")

    for result in results.keys():  
        tmp_dict_output = dict(nr.inventory.hosts[result]["facts"])
        host = str(nr.inventory.hosts[result])
        hostname = tmp_dict_output["version"]["hostname"]
        host_tuple = (host, hostname)
        host_tuple_list.append(host_tuple)
    
    ### EVALUATE TUPLES ###
    for host_tuple in host_tuple_list:
        curr_hostname = host_tuple[0]
        dev_type = findall(r'^\w+-(\w+)', curr_hostname)
        


if __name__ == '__main__':
    main()