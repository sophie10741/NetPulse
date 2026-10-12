import asyncio
from pysnmp.hlapi.v3arch.asyncio import *

async def get_snmp_data(ip, oid, community='public'):

	snmpEngine = SnmpEngine()

	try:
		errorIndication, errorStatus, errorIndex, varBinds = await get_cmd(
			snmpEngine,
			CommunityData(community, mpModel=0),
			await UdpTransportTarget.create((ip, 161)),
			ContextData(),
			ObjectType(ObjectIdentity(oid))
		)

		if errorIndication:
			return f"Error: {errorIndication}"
		elif errorStatus:
			return f"{errorStatus.prettyPrint()} at {errorIndex and varBinds[int(errorIndex) - 1][0] or '?'}"

		else:
			return " = ".join([x.prettyPrint() for x in varBinds[0]])
	finally:
		snmpEngine.close_dispatcher()

async def main():
	ip = "192.168.1.1"
	oid = "1.3.6.1.2.1.1.1.0"
	result = await get_snmp_data(ip, oid)
	print(f"Результат для {ip}: {result}")

if __name__ == "__main__":
	asyncio.run(main())
