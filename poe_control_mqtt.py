#!/usr/bin/env python3
import json
import time
import paramiko
import paho.mqtt.client as mqtt
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config():
    """Loads configuration from poe_control_config.json file."""
    config_path = Path(__file__).parent / "poe_control_config.json"
    try:
        with open(config_path) as f:
            config = json.load(f)
            logger.debug(f"Loaded config: {config}")
            return config
    except Exception as e:
        logger.error(f"Error loading config file: {e}")
        exit(1)

def send_poe_command(host, user, password, interface, command):
    """Connects via SSH and sends PoE commands."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    logger.info(f"Connecting to {host}...")
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
    logger.info(f"Sending command: {command}")
    shell.send(command + '\n')
    time.sleep(0.3)
    output = shell.recv(1000).decode()
    logger.debug(f"Command output: {output}")
    
    # Exit configuration
    shell.send('exit\n')
    time.sleep(0.1)
    shell.send('exit\n')
    time.sleep(0.1)
    
    shell.close()
    ssh.close()

def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker."""
    logger.debug(f"Connection callback - rc: {rc}, flags: {flags}")
    if rc == 0:
        logger.info("Connected to MQTT broker successfully")
        logger.info("Subscribing to PoE control topics...")
        # Subscribe to all PoE control topics
        client.subscribe("ubnt24/poe/+")
        logger.info("Successfully subscribed to 'ubnt24/poe/+'")
        logger.info("Ready to receive PoE control commands")
    else:
        logger.error(f"Failed to connect to MQTT broker with result code {rc}")
        # Reconnection will be handled by the loop_forever() method

def on_disconnect(client, userdata, rc):
    """Callback when disconnected from MQTT broker."""
    logger.debug(f"Disconnect callback - rc: {rc}")
    logger.warning(f"Disconnected from MQTT broker with result code {rc}")
    if rc != 0:
        logger.info("Unexpected disconnection. Will attempt to reconnect...")

def on_message(client, userdata, msg):
    """Callback when message is received."""
    try:
        topic = msg.topic
        command = msg.payload.decode()
        
        # Extract port number from topic (e.g., "ubnt24/poe/07" -> "0/7")
        port_match = topic.split('/')[-1]
        interface = f"0/{int(port_match):d}"
        
        logger.info(f"Received command {command} for interface {interface}")
        
        # Convert command to PoE operation mode
        if command.strip() == "0":
            poe_command = "poe opmode shutdown"
        elif command.strip() == "1":
            poe_command = "poe opmode auto"
        else:
            logger.error(f"Invalid command received: {command}")
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
        logger.error(f"Error processing message: {e}")

def main():
    # Load configuration
    config = load_config()
    
    # Setup MQTT client with latest API version
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, userdata=config)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    # Enable automatic reconnection
    client.reconnect_delay_set(min_delay=1, max_delay=120)
    
    # Connect to MQTT broker with retry logic
    max_retries = 5
    retry_delay = 5  # seconds
    
    logger.info(f"Starting MQTT client with configuration: {config['mqtt']}")
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to MQTT broker at {config['mqtt']['broker']} (attempt {attempt + 1}/{max_retries})...")
            client.connect(config["mqtt"]["broker"])
            logger.info("Connection attempt successful, starting network loop...")
            break
        except Exception as e:
            logger.error(f"Connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("Max retries reached. Exiting...")
                return
    
    # Loop forever with automatic reconnection
    logger.info("Starting MQTT network loop...")
    client.loop_forever()

if __name__ == "__main__":
    main() 