from __future__ import print_function

class AmazonEC2:
    def __init__(self, username, password):
        pass

    # Provider-independent API below
    def create_server(self, machine_type, distro):
        return (True, (privkey, ipaddress, machine_id))

    def stop_server(self, machine_id):
        return True

    def start_server(self, machine_id):
        return True

    def destroy_server(self, machine_id):
        return True

