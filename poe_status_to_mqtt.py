#!/usr/bin/env python3
import re
import time
import json
import paramiko
import paho.mqtt.client as mqtt
from pathlib import Path

def get_command_output(host, user, password, command):
    """Connects via SSH, executes a command, and returns the output."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"Connecting to {host}...")
    ssh.connect(host, username=user, password=password, look_for_keys=False)
    
    # Get an interactive shell
    shell = ssh.invoke_shell()
    
    # Wait for initial prompt
    output = shell.recv(1000).decode()
    print("Initial prompt:", output)
    
    # Send enable command
    print("Sending 'enable' command...")
    shell.send('enable\n')
    time.sleep(0.1)  # Wait for password prompt
    output = shell.recv(1000).decode()
    print("After enable command:", output)
    
    # Send enable password
    print("Sending enable password...")
    shell.send(password + '\n')
    time.sleep(0.1)  # Wait for command to process
    output = shell.recv(1000).decode()
    print("After enable password:", output)
    
    # Send the actual command
    print(f"Sending command: {command}")
    shell.send(command + '\n')
    time.sleep(0.3)  # Wait for command to complete
    
    # Get the command output
    output = shell.recv(4096).decode()
    print("Command output:", output)
    
    shell.close()
    ssh.close()
    return output

def parse_poe_output(output):
    """
    Parses the 'show poe status' command output.
    Skips header lines and handles the actual data rows.
    """
    # Split output into lines and skip header lines
    lines = output.strip().split('\n')
    data_lines = []
    for line in lines:
        # Skip empty lines, header lines, and separator lines
        if not line or 'Intf' in line or '---------' in line or '#' in line:
            continue
        data_lines.append(line)

    results = []
    for line in data_lines:
        # Split the line by whitespace and map to fields
        parts = line.split()
        if len(parts) >= 8:  # Ensure we have all fields
            result = {
                'intf': parts[0],
                'detection': parts[1],
                'class': parts[2],
                'consumed': parts[3],
                'voltage': parts[4],
                'current': parts[5],
                'meter': parts[6],
                'temp': parts[7]
            }
            results.append(result)

    return results

def publish_to_mqtt(broker, topic, message):
    """Publishes a message to an MQTT broker."""
    print(f"Connecting to MQTT broker at {broker}...")
    client = mqtt.Client()
    try:
        client.connect(broker)
        print(f"Publishing to topic {topic}")
        result = client.publish(topic, message)
        print(f"Publish result: {result.rc}")  # rc = 0 indicates success
        client.disconnect()
    except Exception as e:
        print(f"Error publishing to MQTT: {e}")

def load_config():
    """Loads configuration from config.json file."""
    config_path = Path(__file__).parent / "config.json"
    try:
        with open(config_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config file: {e}")
        exit(1)

if __name__ == "__main__":
    # Load configuration
    config = load_config()
    
    # Process each server
    for server in config["servers"]:
        print(f"\nProcessing server: {server['host']}")
        
        full_output = ""
        for cmd in server["commands"]:
            full_output += get_command_output(
                server["host"],
                server["user"],
                server["password"],
                cmd
            )
            time.sleep(0.5)  # small delay between commands

        print("==========")
        print(full_output)
        print("==========")
        
        # Parse the combined output
        parsed_data = parse_poe_output(full_output)
        
        # Add server identification to the data
        message_data = {
            "server": server["host"],
            "timestamp": time.time(),
            "poe_status": parsed_data
        }
        
        message = json.dumps(message_data)

        # Publish the result to the MQTT broker
        publish_to_mqtt(
            config["mqtt"]["broker"],
            config["mqtt"]["topic"],
            message
        )

        print("Data published to MQTT:")
        print(message)
        
        time.sleep(1)  # Add delay between processing servers