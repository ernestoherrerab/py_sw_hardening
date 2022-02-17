import argparse

def parse_args():
    """
    Process the command line arguments
    """
    parser = argparse.ArgumentParser(
        description = "Type -i inventory path to generate a Nornir Inventory\n"
                        " Type -t testbed to generate a Testbed file based on the Nornir Inventory\n"
                        " Type -dryrun True/False"
        )
    parser.add_argument(
        "-i", "--inventory", help = "CSV File Location"
        )
    parser.add_argument(
        "-t", "--testbed", help = "testbed"
        )
    required_argument = parser.add_argument_group("Required Arguments")
    required_argument.add_argument(
        "-dryrun", "--dryrun", help = "True or False", default="stdout", required=True
    )
    args = parser.parse_args()
    return args