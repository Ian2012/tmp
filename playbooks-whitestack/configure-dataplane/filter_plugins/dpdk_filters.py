import yaml

class FilterModule(object):
    def filters(self):
        return {
            'get_cores_from_numa_cores': self.get_cores_from_numa_cores,
            'get_coremask_from_cores': self.get_coremask_from_cores,
            'get_address_from_netplan_file_content': self.get_address_from_netplan_file_content,
            'get_isolated_core_list_from_cmdline_output': self.get_isolated_core_list_from_cmdline_output,
        }

    def _parse_lscpu_output(self, lscpu_output):
        """ Receives the output of lscpu command and parses it on
        a dict {'node': ['cpus']} returning such structure.
        For example, if the output of lscpu is:
        # Node,CPU
        0,0
        0,2
        0,4
        1,1
        1,3
        1,5
        This function will return the following dict:
        { '0': ['0', '2', '4'], '1': ['1', '3', '5'] }
        """
        numa_cores_to_cores = {}
        for line in lscpu_output.split('\n'):
            if line.startswith('#') or len(line.split(',')) != 2:
                continue
            node = line.split(',')[0]
            cpu = line.split(',')[1]
            if node in numa_cores_to_cores:
                numa_cores_to_cores[node].append(cpu)
            else:
                numa_cores_to_cores[node] = [cpu]
        return numa_cores_to_cores


    def get_cores_from_numa_cores(self, numa_cores, lscpu_output):
        """ Receives a string list of numa_cores and returns the required
        cores translated by the output of lscpu command.
        For example, if the output of lscpu is:
        # Node,CPU
        0,0
        0,2
        0,4
        1,1
        1,3
        1,5
        The following will be the return values of the function on each case:
        get_cores_from_numa_cores('0.1,0.2') -> '2,4'
        get_cores_from_numa_cores('1.1,0.2') -> '3,4'
        get_cores_from_numa_cores('3,0.2') -> '3,4'
        get_cores_from_numa_cores('0.1,1.-1') -> '2,5'
        """
        numa_cores_to_cores = self._parse_lscpu_output(lscpu_output)
        numa_core_list = numa_cores.split(',')
        core_list = []
        for numa_core in numa_core_list:
            if len(numa_core.split('.')) == 1:
                core_list.append(numa_core)
                continue
            node_key = numa_core.split('.')[0]
            cpu_index = int(numa_core.split('.')[1])
            core = numa_cores_to_cores[node_key][cpu_index]
            core_list.append(core)

        return ','.join(core_list)

    def get_coremask_from_cores(self, cores):
        """ Receives a string list of cores and returns the required coremask.
        Examples:
        get_coremask_from_cores('6') -> '0x40'
        get_coremask_from_cores('1,2') -> '0x6'
        get_coremask_from_cores('1,2,6,10') -> '0x446'
        """
        core_list = cores.split(',')
        coremask = 0
        for core in core_list:
            core_number = int(core)
            coremask = coremask | (1 << core_number)
        return hex(coremask)


    def get_address_from_netplan_file_content(self, netplan_file_content, interface):
        """ Receives the content of a netplan YAML file and retrieves the IP
        address of a requested interface. The interface is expected to be
        defined on the network.ethernets section of the YAML.
        For example, if the content of the netplan file is:
        network:
          version: 2
          ethernets:
            br-ex:
              addresses:
              - 192.168.199.41/24
        Then calling the function with 'br-ex' will return '192.168.199.41/24'.
        """
        netplan_data = yaml.safe_load(netplan_file_content)
        interfaces_data = netplan_data.get('network', {}).get('ethernets', {})
        return interfaces_data.get(interface, {}).get('addresses', [''])[0]


    def get_isolated_core_list_from_cmdline_output(self, cores):
        core_list = cores.split(',')
        processed_core_list = []
        for cores in core_list:
            if '-' in cores:
                splitted_cores = cores.split('-')
                if int(splitted_cores[-1]) < int(splitted_cores[0]):
                    raise Exception('The upper limit of the range must be greater than the lower limit.')
                cores = list(range(int(splitted_cores[0]), int(splitted_cores[-1]) + 1))
                processed_core_list += cores
            else:
                processed_core_list.append(int(cores))
        return list(map(int, processed_core_list))
