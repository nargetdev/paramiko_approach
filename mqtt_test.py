#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import logging
import time
import sys

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker."""
    logger.debug(f"Connection callback - rc: {rc}, flags: {flags}")
    if rc == 0:
        logger.info("Connected to MQTT broker successfully")
        # Subscribe to all PoE topics to monitor
        client.subscribe("ubnt24/poe/#")
        logger.info("Successfully subscribed to 'ubnt24/poe/#'")
    else:
        logger.error(f"Failed to connect to MQTT broker with result code {rc}")

def on_message(client, userdata, msg):
    """Callback when message is received."""
    logger.info(f"Received message on topic {msg.topic}: {msg.payload.decode()}")

def main():
    # Setup MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Connect to MQTT broker
    broker = "emqx"
    port = 1883
    
    logger.info(f"Connecting to MQTT broker at {broker}:{port}...")
    client.connect(broker, port)
    
    # Start network loop
    client.loop_start()
    
    try:
        while True:
            # Example: Send a test command
            topic = "ubnt24/poe/07"
            message = "1"
            logger.info(f"Sending message to {topic}: {message}")
            client.publish(topic, message)
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        client.loop_stop()
        client.disconnect()
        sys.exit(0)

if __name__ == "__main__":
    main() 