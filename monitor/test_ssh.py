from ssh_manager import execute_ssh_command

host = "192.168.4.2"
username = "root"
command = "uname -a"
private_key_path = "/root/.ssh/id_rsa"

result = execute_ssh_command(host, username, command, private_key_path)
print(result)
