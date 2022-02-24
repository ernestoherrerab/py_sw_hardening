#! /usr/bin/env python
"""
Script to add hardening to switches
"""

from getpass import getpass
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import re
import sys
from nornir import InitNornir
from nornir_scrapli.tasks import send_commands, send_configs_from_file
from nornir_utils.plugins.functions import print_result
import inventory_builder as inv
import parse_args as pargs

def get_data_task(task):
    """
    Task to send commands to Devices via Nornir/Scrapli
    """
    commands =["show cdp neighbors detail", "show vlan", "show etherchannel summary"]
    data_results = task.run(task=send_commands, commands=commands)
    for data_result in data_results:
        for data, command in zip(data_result.scrapli_response, commands):
            task.host[command.replace(" ","_")] = data.genie_parse_output()

def send_config_task(task, dryrun_param):
    """
    Task to send rendered templates to devices via Nornir/Scrapli
    """
    nornir_host = task.host
    host = str(nornir_host) + ".cfg"
    config_path = Path("sw_configs/") / host
    task.run(task=send_configs_from_file, file=str(config_path), dry_run=dryrun_param)

def generate_config(my_dict, my_template, hostname):
    """
    Generate candidate configuration from Python Dictionary
    """
    path_file = Path("sw_configs/") / hostname
    template_dir = Path('templates/')
    env = Environment(loader=FileSystemLoader(str(template_dir)), trim_blocks=True , lstrip_blocks=True)
    template = env.get_template(my_template)
    configuration = template.render(my_dict = my_dict)
    with open(path_file, "w") as open_file:
        open_file.write(configuration)

def main():
    """Main Function"""
    """
    -h For Help

    To build a Nornir host file from a csv file within the csv_data folder:
    -i + file_name.csv
    Example: -i switchInventory.csv
    
    To Build a PyATS testbed file from the Nornir Inventory
    -t testbed

    Required: Dry Run True or False
    -dryrun True/False
    """

    args = pargs.parse_args()
    try:
        dryrun_arg = args.dryrun.capitalize()
        dryrun_param = eval(dryrun_arg)
    except NameError as e:
        print("Invalid Parameter. Dryrun can only be True or False...")
        print(e)
        print("Use -h for help...")
        print("Exiting...")
        sys.exit()

    if args.inventory:
        try:
            csv_path = Path('csv_data') / args.inventory
            print(f"Building Inventory from: {csv_path}...")
            inv.build_inventory(inv.csv_to_yaml(csv_path))
        except FileNotFoundError as e:
            print("Inventory File Not Found")
            print("Exiting...")
            sys.exit()

    if args.testbed:
        inv.build_testbed()
        print(f"Building Testbed File...")

    ### PROGRAM VARIABLES ###
    username = input("Username: ")
    password = getpass(prompt="Password: ", stream=None)
    dict_output = {}
    snoop_ifs_dict = {}
    platform_ids = ["swn", "cs", "as", "edgertr"]

    ### INITIALIZE NORNIR ###
    """
    Fetch sent command data, format results, and put them in a dictionary variable
    """
    try:
        print("Initializing connections to devices...")
        nr = InitNornir(config_file="config/config.yml", core={"raise_on_error": True})
        nr.inventory.defaults.username = username
        nr.inventory.defaults.password = password
        results = nr.run(task=get_data_task)
    except KeyError as e:
        print(f"Connection to device failed: {e}")

    print("Parsing generated output...")
    for result in results.keys():  
        tmp_dict_output = dict(nr.inventory.hosts[result])
        host = str(nr.inventory.hosts[result])
        dict_output[host] = {}
        snoop_ifs_dict[host] = {}
        snoop_ifs_dict[host]["interfaces"] = []
        snoop_ifs_dict[host]["port_channels"] = {}
        snoop_ifs_dict[host]["vlans"] = []
        dict_output[host]["cdp"] = tmp_dict_output["show_cdp_neighbors_detail"]["index"]
        dict_output[host]["port_channels"] = tmp_dict_output["show_etherchannel_summary"]["interfaces"]
        dict_output[host]["vlans"] = tmp_dict_output["show_vlan"]["vlans"]
 
    ### EVALUATE OUTPUT DICTIONARIES ###
    """
    To find candidate interfaces and VLANs for DHCP snooping trust
    """
    print("Evaluating output...")
    for key, value in dict_output.items():
        for _, cdp_data in value["cdp"].items():
            platforms = re.findall(r'^\w+-([a-z]+|[A-Z]+)', cdp_data["device_id"])
            if any(item in platform_ids for item in platforms):
                snoop_ifs_dict[key]["interfaces"].append(cdp_data["local_interface"])
        for pc_key, pc_data in value["port_channels"].items():
            if "members" in pc_data:
                snoop_ifs_dict[key]["port_channels"][pc_key] = []
                for if_members in pc_data["members"].keys():
                    if if_members in snoop_ifs_dict[key]["interfaces"]:
                        snoop_ifs_dict[key]["port_channels"][pc_key].append(if_members)
        vlan_list = [vlan_id for vlan_id, vlan_data in value["vlans"].items() if vlan_data['state'] == "active"]
        snoop_ifs_dict[key]["vlans"] = vlan_list
    ### REMOVE PORT CHANNELS THAT ARE NOT CONNECTED TO SWITCHES OR ROUTERS ###
        for port_channel in snoop_ifs_dict[key]["port_channels"].copy():
            if not snoop_ifs_dict[key]["port_channels"][port_channel].copy():
                snoop_ifs_dict[key]["port_channels"].pop(port_channel, None)
    
    ### CREATE JINJA2 TEMPLATES ###
    template = "dhcp_snooping.j2"
    print("Generating Configuration Files...")
    for key, _ in snoop_ifs_dict.items():
        host_file = key + ".cfg"
        generate_config(key, template, host_file)

    ### DEPLOY CONFIGURATION FILES TO DEVICES ###
    print("Deploying configurations to devices...")
    if not dryrun_param:
        print("WARNING: You are about to deploy configurations to the devices")
        decision = input("Do you want to continue [y/n]?").lower()
        if decision == "y" or decision == "yes":
            print("Configuration will be deployed to devices...")
            deployment_result = nr.run(task=send_config_task, dryrun_param=False)
            print_result(deployment_result)
        else:
            print("A dry run will be performed...")
            deployment_result = nr.run(task=send_config_task, dryrun_param=True)
            print_result(deployment_result)
    elif dryrun_param:
        print("A dry run will be performed...")
        deployment_result = nr.run(task=send_config_task, dryrun_param=True)
        print_result(deployment_result)
    else:
        print("Only True or False are accepted...")
        print("Exiting...")

if __name__ == '__main__':
    main()