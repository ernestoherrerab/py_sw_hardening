#! /usr/bin/env python
"""
Module to transform CSV data to a Nornir Inventory

"""

import csv
import re
from pathlib import Path
from decouple import config
from yaml import dump, load, SafeDumper
from yaml.loader import FullLoader

class NoAliasDumper(SafeDumper):
    """
    To Handle Long Lines in YAML Dumps
    """
    def ignore_aliases(self, data):
        return True
    def increase_indent(self, flow=False, indentless=False):
        return super(NoAliasDumper, self).increase_indent(flow, False)

def build_inventory(csv_yaml_func):
    """
    To build a Nornir Inventory From CSV Data
    """
    def create_inventory():
        path_file = Path("inventory/") / "hosts.yml"
        with open(path_file, "w") as open_file:
            open_file.write("----\n\n" + csv_yaml_func)
        host_file = open(path_file)
        lines = host_file.readlines()
        host_file.close()
        host_file = open(path_file, 'w')
        for line in lines:
            host_file.write(line[1:])
        host_file.close()
    return create_inventory()

#@build_inventory
def csv_to_yaml(csv_path):
    """
    Function to Convert CSV Data to YAML
    """
    host_dict = {}
    host_dict_list = []
    platform_ids = ["swn", "cs", "as", "switch"]
    with open(csv_path) as f:
        csv_data = csv.reader(f, delimiter=';')
        next(csv_data)
        csv_data_list = list(csv_data)
    for csv_item in csv_data_list:
        host_dict = {}
        platforms = re.findall(r'^\w+-([a-z]+|[A-Z]+)', csv_item[0].lower())
        if any(item in platform_ids for item in platforms) and platforms:
                host_dict[csv_item[0].lower().replace(config('DOMAIN_NAME_1'), '').replace(config('DOMAIN_NAME_2'), '')] = {
                'hostname' : csv_item[1],
                'groups': ['ios_devices'] }
        if len(host_dict): 
            host_dict_list.append(host_dict)
    hosts_yaml = dump(host_dict_list, default_flow_style=False)
    return hosts_yaml

def build_testbed():
    """
    To Build PyATS Testbed File
    """
    testbed_inv = {}
    testbed_inv["devices"] = {}
    yaml_file = Path("inventory/") / "hosts.yml"
    testbed_file = "testbed.yml"
    with open(yaml_file) as f:
        dict_result = load(f, Loader=FullLoader )
    for key, value in dict_result.items():
        testbed_inv["devices"][key] = {}
        testbed_inv["devices"][key]["connections"] = {}
        testbed_inv["devices"][key]["connections"]["cli"] = {}
        testbed_inv["devices"][key]["connections"]["cli"]["ip"] = value["hostname"]
        testbed_inv["devices"][key]["connections"]["cli"]["protocol"] = "ssh"
        if "iosXE_devices" or "ios_devices" in value["groups"]:
            testbed_inv["devices"][key]["os"] = "iosxe"
            testbed_inv["devices"][key]["type"] = "iosxe"
    yaml_dump = dump(testbed_inv, default_flow_style=False)
    with open(testbed_file, "w") as f:
        f.write("---\n\n" + yaml_dump)

# This does not work when using the decorator @build_inventory
#csv_to_yaml = build_inventory(csv_to_yaml(Path('csv_data') / "example.csv"))
#csv_to_yaml

# This works without using the @decorator
#csv_path = Path('csv_data') / "example.csv"
#csv_to_yaml = build_inventory(csv_to_yaml(csv_path))
#csv_to_yaml