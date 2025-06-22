import time
import os
import logging
import sys
import json
from google.cloud import pubsub_v1
from concurrent.futures import TimeoutError

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# GCP Configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "nca-toolkit-438301")
TOPIC_NAME = "gpu-tasks-gke"
SUBSCRIPTION_NAME = "gpu-runner-sub" # Subscription name

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_NAME)

def process_message(message):
    """Callback function to process a single Pub/Sub message."""
    start_time = time.time()
    logging.info(f"Received message: {message.data}")
    
    try:
        data = json.loads(message.data)
        logging.info(f"Processing task for file_id: {data.get('file_id', 'N/A')}")

        # Simulate GPU-intensive work
        task_duration = 5 + (os.getpid() % 5) # Simulate a longer task
        logging.info(f"Simulating GPU work for {task_duration} seconds.")
        time.sleep(task_duration)
        
        processing_time = time.time() - start_time
        logging.info(f"Task completed successfully. processingTime={processing_time:.2f} sec")
        
        message.ack()
        logging.info(f"Message {message.message_id} acknowledged.")

    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode message data: {e}")
        message.nack()
    except Exception as e:
        logging.error(f"An error occurred during task processing: {e}")
        # Nack the message so it can be redelivered for another attempt
        message.nack()

def ensure_subscription_exists():
    """Creates the subscription if it doesn't exist."""
    topic_path = pubsub_v1.PublisherClient().topic_path(PROJECT_ID, TOPIC_NAME)
    try:
        subscriber.get_subscription(subscription=subscription_path)
        logging.info(f"Subscription '{SUBSCRIPTION_NAME}' already exists.")
    except Exception:
        logging.info(f"Subscription '{SUBSCRIPTION_NAME}' not found. Creating...")
        subscriber.create_subscription(
            name=subscription_path,
            topic=topic_path,
            ack_deadline_seconds=600 # 10 minutes for long processing
        )
        logging.info(f"Subscription '{SUBSCRIPTION_NAME}' created.")


def main():
    """
    Main function to start the Pub/Sub subscriber.
    """
    ensure_subscription_exists()
    
    # The subscriber is non-blocking, so we need to keep the main thread alive.
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=process_message)
    logging.info(f"Listening for messages on {subscription_path}...")

    try:
        # Wait indefinitely for messages.
        streaming_pull_future.result()
    except TimeoutError:
        streaming_pull_future.cancel()
        logging.info("Streaming pull future timed out.")
    except Exception as e:
        logging.error(f"An error occurred with the subscriber: {e}")
        streaming_pull_future.cancel()

if __name__ == "__main__":
    main()
