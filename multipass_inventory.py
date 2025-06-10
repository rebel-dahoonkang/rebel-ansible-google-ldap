#!/usr/bin/env python3
import json
import subprocess

def get_multipass_inventory():
    try:
        # multipass list 명령어의 결과를 JSON으로 받음
        result = subprocess.run(['multipass', 'list', '--format', 'json'], capture_output=True, text=True, check=True)
        vms = json.loads(result.stdout)['list']

        inventory = {"_meta": {"hostvars": {}}}
        vm_group = []

        for vm in vms:
            # 실행 중인 VM만 대상으로 함
            if vm['state'] == 'Running':
                vm_name = vm['name']
                vm_ip = vm['ipv4'][0] if vm['ipv4'] else None

                if vm_ip:
                    vm_group.append(vm_name)
                    inventory["_meta"]["hostvars"][vm_name] = {
                        "ansible_host": vm_ip,
                        "ansible_user": "ubuntu"
                    }
        
        inventory["your_ubuntu_servers"] = {"hosts": vm_group}
        
        print(json.dumps(inventory, indent=4))

    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
        print(json.dumps({"_meta": {"hostvars": {}}}, indent=4))

if __name__ == '__main__':
    get_multipass_inventory()