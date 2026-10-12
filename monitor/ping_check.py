from ping3 import ping

def check_ping(ip_address):
	response = ping(ip_address)
	if response is not None:
		return True
	return False

if __name__ == "__main__":
	print(check_ping("192.168.1.1"))
