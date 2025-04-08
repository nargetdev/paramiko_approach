FROM python:3.9-slim

WORKDIR /app

# Install required dependencies
RUN pip install --no-cache-dir paramiko paho-mqtt

# Copy necessary files
COPY poe_control_mqtt.py .
COPY poe_control_config.json .

# Set execution permissions
RUN chmod +x poe_control_mqtt.py

# Run the script
CMD ["python", "poe_control_mqtt.py"]

