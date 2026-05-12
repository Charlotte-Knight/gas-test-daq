import time
import os
from venv import logger
from datetime import datetime

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

bot_token = os.getenv("SLACK_BOT_TOKEN")
slack_channel = os.getenv("SLACK_CHANNEL")
if not bot_token:
    raise ValueError("SLACK_BOT_TOKEN not set. Please set SLACK_BOT_TOKEN environment variable")
if not slack_channel:
    raise ValueError("SLACK_CHANNEL not set. Please set SLACK_CHANNEL environment variable")

client = WebClient(token=bot_token)

class GasPressureAlert:
    
    def __init__(self):

        self.name = "Pressure Alert"              
        self.thr_low = 0.5          # the low threshold
        self.thr_high = 10          # the high threshold
        self.triggered = False          # whether it has been triggered
        self.alert_time = None
        self.last_alert = 0
        self.alert_interval = 60
    
    def check(self, current_pressure):

        # Check if the current pressure is outside the thresholds
        if current_pressure > self.thr_high or current_pressure < self.thr_low:
            current_time = time.time()
            should_alert = True
        
        # If it should alert and hasn't been triggered yet
            if not self.triggered or (current_time - self.last_alert) >= self.alert_interval:
                self.triggered = True      # Reset the flag to True
                self.last_alert = current_time
                self.alert_time = datetime.now()
                return True                # trigger the alert
        
        # If it shouldn't alert but was previously triggered
        if not should_alert and self.triggered:
            self.triggered = False     # Reset the flag to False
            print("Pressure back to normal")
            
        return False

    def send_slack_message(self, current_pressure):

        print(f"   !ALERT!{self.name}")
        print(f"   Threshold Range: {self.thr_low} - {self.thr_high} bar")
        print(f"   Current Pressure: {current_pressure} bar")
        print(f"   Time: {self.alert_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
               
        message = (
            f"⚠️ *{self.name}*\n"
            f"Threshold Range: {self.thr_low} - {self.thr_high} bar\n"
            f"Current Pressure: {current_pressure} bar\n"
            f"Time: {self.alert_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
                
        try:
            response = client.chat_postMessage(
                channel=slack_channel,
                text=message
            )
            print("Slack message sent successfully!")

        except SlackApiError as e:
            print("Failed to send message!")
            print("Error message:", e.response["error"])

