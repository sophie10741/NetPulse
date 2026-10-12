import paramiko

def execute_ssh_command(host, username, command, private_key_path=None):
	try:
		client = paramiko.SSHClient()
		client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

		if private_key_path:
			key = paramiko.RSAKey.from_private_key_file(private_key_path)
			client.connect(hostname=host, username=username, pkey=key)
		else:
			client.connect(hostname=host, username=username)

		stdin, stdout, stderr = client.exec_command(command)
		output = stdout.read().decode()
		error = stderr.read().decode()

		client.close()

		if error:
			return f"Error: {error}"
		return output.strip()

	except Exception as e:
		return f"SSH Error: {str(e)}"
