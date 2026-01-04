import json

# Mock Data from user's previous output
mock_json_output = """
{"peers":{"total":0,"connected":0,"details":null},"cliVersion":"0.60.9","daemonVersion":"0.60.9","management":{"url":"https://api.netbird.io:443","connected":false,"error":""},"signal":{"url":"https://signal.netbird.io:443","connected":false,"error":""},"relays":{"total":1,"available":0,"details":[{"uri":"rels://relay.netbird.io:443","available":false,"error":"relay connection is not established"}]},"netbirdIp":"","publicKey":"","usesKernelInterface":false,"fqdn":"","quantumResistance":false,"quantumResistancePermissive":false,"networks":null,"forwardingRules":0,"dnsServers":[],"events":[{"id":"07bb5b3b","severity":"INFO","category":"NETWORK","message":"Default route added","userMessage":"Exit node connected.","timestamp":"2025-12-25T21:49:49.903807444Z","metadata":{"id":"Exit Node (Hinemoa)"}},{"id":"222d1676","severity":"WARNING","category":"NETWORK","message":"Default route disconnected","userMessage":"Exit node connection lost.","timestamp":"2025-12-25T22:53:24.838037967Z","metadata":{"id":"Exit Node (Hinemoa)"}}],"lazyConnectionEnabled":false,"profileName":"hinemoa","sshServer":{"enabled":false,"sessions":[]}}
"""

def test_parsing(json_str):
    status_data = json.loads(json_str)
    lines = []
    
    # Simulate get_os_info
    lines.append(f"OS: linux/x86_64") # Mocked
    
    lines.append(f"Daemon version: {status_data.get('daemonVersion', 'Unknown')}")
    lines.append(f"CLI version: {status_data.get('cliVersion', 'Unknown')}")
    
    mgmt = status_data.get('management', {})
    lines.append(f"Management: {'Connected' if mgmt.get('connected') else 'Disconnected'}")
    
    signal = status_data.get('signal', {})
    lines.append(f"Signal: {'Connected' if signal.get('connected') else 'Disconnected'}")
    
    relays = status_data.get('relays', {})
    lines.append(f"Relays: {relays.get('available', 0)}/{relays.get('total', 0)} Available")
    
    nameservers = status_data.get('dnsServers', [])
    lines.append(f"Nameservers: {len(nameservers)} Available")
    
    lines.append(f"FQDN: {status_data.get('fqdn', '')}")
    lines.append(f"NetBird IP: {status_data.get('netbirdIp', '')}")
    lines.append(f"Interface type: {'Kernel' if status_data.get('usesKernelInterface') else 'Userspace'}")
    lines.append(f"Quantum resistance: {'true' if status_data.get('quantumResistance') else 'false'}")
    lines.append(f"Lazy connection: {'true' if status_data.get('lazyConnectionEnabled') else 'false'}")
    
    ssh = status_data.get('sshServer', {})
    lines.append(f"SSH Server: {'Enabled' if ssh.get('enabled') else 'Disabled'}")
    
    lines.append(f"Peers count: {status_data.get('peers', {}).get('connected', 0)}/{status_data.get('peers', {}).get('total', 0)} Connected")

    # Exit node logic similar to implemented code
    exit_node_name = "N/A"
    events = status_data.get("events", [])
    for event in reversed(events):
        if event.get("userMessage") == "Exit node connected.":
            exit_node_name = event.get("metadata", {}).get("id", "Unknown")
            break
        if event.get("userMessage") == "Exit node connection lost.":
             exit_node_name = "Disconnected"
             break
    
    if exit_node_name == "Disconnected":
        exit_node_name = "N/A"
        
    return lines, exit_node_name

lines, exit_node = test_parsing(mock_json_output)
print("--- Generated Lines ---")
for l in lines:
    print(l)
print(f"Exit Node: {exit_node}")

# Assertions
assert "Management: Disconnected" in lines
assert "Signal: Disconnected" in lines
assert "Relays: 0/1 Available" in lines
assert "Interface type: Userspace" in lines # usesKernelInterface was false
assert exit_node == "N/A" # "Exit node connection lost" was later in the list (so earlier in reversed traversal?) 
# Wait, list is chronological usually. reversed() means looking at latest first. 
# In mock data: 
# 1. "Exit node connected." (21:49)
# 2. "Exit node connection lost." (22:53)
# reversed() -> sees "connection lost" first. -> breaks loop with "Disconnected". -> sets to "N/A". Correct.

print("Verification Passed!")
