command_templates = {
	"change_ip": {
		"description": "Change IP Address",
		"command": "ip addr add {ip}/{mask} dev {interface} && ip addr del {old_ip}/{mask} dev {interface}"
	}
}

command_templates.update({
	"create_user": {
		"description": "Create User",
		"command": "useradd -u {uid} -p $(openssl passwd -1 {password}) {username}"
	},
	"modify_user": {
		"description": "Modify User",
		"command": "usermod -u {uid} -p $(openssl passwd -1 {password}) {username}"
	},
	"sudo_no_auth": {
		"description": "Allow Sudo Without Password",
		"command": "echo '{username} ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers"
	},

	"default_route": {
		"description": "Set Default Route",
		"command": "ip route add default via {gateway}"
	},

	"change_ssh_port": {
		"description": "Change SSH Port",
		"command": "sed -i 's/#Port 22/Port {port}/' /etc/ssh/sshd_config && systemctl restart sshd"
	},

	"allow_ssh_user": {
		"description": "Allow SSH User",
		"command": "echo 'AllowUsers {username}' >> /etc/ssh/sshd_config && systemctl restart sshd"
	},

	"set_ssh_attempts": {
		"description": "Set SSH Login Attempts",
		"command": "sed -i 's/#MaxAuthTries 6/MaxAuthTries {attempts}/' /etc/ssh/sshd_config && systemctl restart sshd"
	},

	"set_ssh_banner": {
		"description": "Set SSH Banner",
		"command": "echo '{banner}' > /etc/issue && sed -i 's/#Banner none/Banner \/etc\/issue/' /etc/ssh/sshd_config && systemctl restart sshd"
	},

	"create_gre_tunnel": {
		"description": "Create GRE Tunnel",
		"command": "ip tunnel add {tunnel_name} mode gre remote {remote_ip} local {local_ip} ttl 255 && ip link set {tunnel_name} up"
	},

	"configure_dhcp": {
		"description": "Configure DHCP",
		"command": "echo 'subnet {subnet} netmask {netmask} {{ range {range_start} {range_end}; option routers {gateway}; option domain-name-servers {dns_server}; }}' > /etc/dhcp/dhcpd.conf && systemctl restart isc-dhcp-server"
	},

	"configure_dns": {
		"description": "Configure DNS",
		"command": "echo 'zone \"{domain}\" {{ type master; file \"/etc/bind/db.{domain}\"; }};' >> /etc/bind/named.conf.local && systemctl restart bind9"
	 },

	"set_timezone": {
		"description": "Set Timezone",
		"command": "timedatectl set-timezone {timezone}"
	},

	"configure_chrony": {
		"description": "Configure Chrony",
		"command": "echo 'server {server} iburst' >> /etc/chrony/chrony.conf && systemctl restart chronyd"
	},

	"configure_ansible": {
		"description": "Configure Ansible Inventory",
		"command": "echo -e '[all]\n{hosts}' > /etc/ansible/hosts && ansible all -m ping"
	}

})
