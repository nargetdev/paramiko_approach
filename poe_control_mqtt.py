#!/usr/bin/env python3
import json
import time
import paramiko
import paho.mqtt.client as mqtt
from pathlib import Path

def load_config():
    """Loads configuration from poe_control_config.json file."""
    config_path = Path(__file__).parent / "poe_control_config.json"
    try:
        with open(config_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config file: {e}")
        exit(1)

def send_poe_command(host, user, password, interface, command):
    """Connects via SSH and sends PoE commands."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"Connecting to {host}...")
    ssh.connect(host, username=user, password=password, look_for_keys=False)
    
    # Get an interactive shell
    shell = ssh.invoke_shell()
    
    # Wait for initial prompt
    shell.recv(1000).decode()
    
    # Send enable command and password
    shell.send('enable\n')
    time.sleep(0.1)
    shell.recv(1000).decode()
    
    shell.send(password + '\n')
    time.sleep(0.1)
    shell.recv(1000).decode()
    
    # Enter configuration mode
    shell.send('configure\n')
    time.sleep(0.1)
    shell.recv(1000).decode()
    
    # Enter interface configuration
    shell.send(f'interface {interface}\n')
    time.sleep(0.1)
    shell.recv(1000).decode()
    
    # Send the PoE command
    print(f"Sending command: {command}")
    shell.send(command + '\n')
    time.sleep(0.3)
    output = shell.recv(1000).decode()
    print("Command output:", output)
    
    # Exit configuration
    shell.send('exit\n')
    time.sleep(0.1)
    shell.send('exit\n')
    time.sleep(0.1)
    
    shell.close()
    ssh.close()

def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker."""
    print(f"Connected to MQTT broker with result code {rc}")
    # Subscribe to all PoE control topics
    client.subscribe("ubnt24/poe/+")

def on_message(client, userdata, msg):
    """Callback when message is received."""
    try:
        topic = msg.topic
        command = msg.payload.decode()
        
        # Extract port number from topic (e.g., "ubnt24/poe/07" -> "0/7")
        port_match = topic.split('/')[-1]
        interface = f"0/{int(port_match):d}"
        
        print(f"Received command {command} for interface {interface}")
        
        # Convert command to PoE operation mode
        if command.strip() == "0":
            poe_command = "poe opmode shutdown"
        elif command.strip() == "1":
            poe_command = "poe opmode auto"
        else:
            print(f"Invalid command received: {command}")
            return
        
        # Send command to switch
        config = userdata  # Config passed as userdata
        send_poe_command(
            config["servers"][0]["host"],  # Assuming first server in config
            config["servers"][0]["user"],
            config["servers"][0]["password"],
            interface,
            poe_command
        )
        
    except Exception as e:
        print(f"Error processing message: {e}")

def main():
    # Load configuration
    config = load_config()
    
    # Setup MQTT client
    client = mqtt.Client(userdata=config)  # Pass config as userdata
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Connect to MQTT broker
    print(f"Connecting to MQTT broker at {config['mqtt']['broker']}...")
    client.connect(config["mqtt"]["broker"])
    
    # Loop forever
    client.loop_forever()

if __name__ == "__main__":
    main() 