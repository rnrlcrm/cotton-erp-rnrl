"""
GCP Pub/Sub Dead Letter Queue Configuration

This script creates/updates Pub/Sub topics and subscriptions with DLQ support.
Run this as part of infrastructure provisioning before deploying the application.

DLQ Architecture:
1. Main topic receives events from OutboxWorker
2. Subscription processes events with retry policy
3. After max delivery attempts, failed messages go to DLQ topic
4. DLQ subscription stores failures for manual review/replay
5. Alerts trigger when DLQ receives messages (ops team investigation)

Retry Policy:
- Minimum backoff: 10 seconds
- Maximum backoff: 600 seconds (10 minutes)
- Max delivery attempts: 5
- After 5 failures -> DLQ
"""

import argparse
import logging
from google.cloud import pubsub_v1
from google.api_core import retry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PubSubDLQConfigurator:
    """Configure Pub/Sub topics and subscriptions with DLQ support"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()
    
    def create_topic(self, topic_name: str) -> str:
        """
        Create a Pub/Sub topic (idempotent).
        
        Args:
            topic_name: Name of the topic
        
        Returns:
            Full topic path
        """
        topic_path = self.publisher.topic_path(self.project_id, topic_name)
        
        try:
            topic = self.publisher.get_topic(request={"topic": topic_path})
            logger.info(f"Topic already exists: {topic_path}")
            return topic_path
        except Exception:
            logger.info(f"Creating topic: {topic_path}")
            topic = self.publisher.create_topic(request={"name": topic_path})
            logger.info(f"Created topic: {topic.name}")
            return topic.name
    
    def create_subscription_with_dlq(
        self,
        subscription_name: str,
        topic_name: str,
        dlq_topic_name: str,
        max_delivery_attempts: int = 5,
        ack_deadline_seconds: int = 60,
    ) -> str:
        """
        Create a subscription with DLQ support (idempotent).
        
        Args:
            subscription_name: Name of the subscription
            topic_name: Name of the main topic
            dlq_topic_name: Name of the DLQ topic
            max_delivery_attempts: Max attempts before sending to DLQ (default: 5)
            ack_deadline_seconds: Ack deadline in seconds (default: 60)
        
        Returns:
            Full subscription path
        """
        subscription_path = self.subscriber.subscription_path(
            self.project_id, subscription_name
        )
        topic_path = self.publisher.topic_path(self.project_id, topic_name)
        dlq_topic_path = self.publisher.topic_path(self.project_id, dlq_topic_name)
        
        try:
            subscription = self.subscriber.get_subscription(
                request={"subscription": subscription_path}
            )
            logger.info(f"Subscription already exists: {subscription_path}")
            
            # Update subscription with DLQ config
            update_request = {
                "subscription": {
                    "name": subscription_path,
                    "topic": topic_path,
                    "ack_deadline_seconds": ack_deadline_seconds,
                    "dead_letter_policy": {
                        "dead_letter_topic": dlq_topic_path,
                        "max_delivery_attempts": max_delivery_attempts,
                    },
                    "retry_policy": {
                        "minimum_backoff": {"seconds": 10},
                        "maximum_backoff": {"seconds": 600},
                    },
                },
                "update_mask": {
                    "paths": [
                        "ack_deadline_seconds",
                        "dead_letter_policy",
                        "retry_policy",
                    ]
                },
            }
            
            subscription = self.subscriber.update_subscription(request=update_request)
            logger.info(f"Updated subscription: {subscription_path}")
            return subscription_path
            
        except Exception as e:
            logger.info(f"Creating subscription: {subscription_path}")
            
            request = {
                "name": subscription_path,
                "topic": topic_path,
                "ack_deadline_seconds": ack_deadline_seconds,
                "dead_letter_policy": {
                    "dead_letter_topic": dlq_topic_path,
                    "max_delivery_attempts": max_delivery_attempts,
                },
                "retry_policy": {
                    "minimum_backoff": {"seconds": 10},
                    "maximum_backoff": {"seconds": 600},
                },
            }
            
            subscription = self.subscriber.create_subscription(request=request)
            logger.info(f"Created subscription: {subscription.name}")
            return subscription.name
    
    def create_dlq_subscription(
        self,
        dlq_subscription_name: str,
        dlq_topic_name: str,
    ) -> str:
        """
        Create a subscription for the DLQ topic (for monitoring/manual replay).
        
        Args:
            dlq_subscription_name: Name of the DLQ subscription
            dlq_topic_name: Name of the DLQ topic
        
        Returns:
            Full subscription path
        """
        subscription_path = self.subscriber.subscription_path(
            self.project_id, dlq_subscription_name
        )
        topic_path = self.publisher.topic_path(self.project_id, dlq_topic_name)
        
        try:
            subscription = self.subscriber.get_subscription(
                request={"subscription": subscription_path}
            )
            logger.info(f"DLQ subscription already exists: {subscription_path}")
            return subscription_path
        except Exception:
            logger.info(f"Creating DLQ subscription: {subscription_path}")
            
            request = {
                "name": subscription_path,
                "topic": topic_path,
                "ack_deadline_seconds": 600,  # 10 minutes for manual review
            }
            
            subscription = self.subscriber.create_subscription(request=request)
            logger.info(f"Created DLQ subscription: {subscription.name}")
            return subscription.name
    
    def setup_complete_dlq_infrastructure(self):
        """
        Set up complete DLQ infrastructure for Commodity ERP.
        
        Creates:
        1. Main events topic (cotton-erp-events)
        2. DLQ topic (cotton-erp-events-dlq)
        3. Main subscription with DLQ config (cotton-erp-events-sub)
        4. DLQ subscription for monitoring (cotton-erp-events-dlq-sub)
        """
        logger.info("=== Setting up Pub/Sub DLQ Infrastructure ===")
        
        # 1. Create main events topic
        main_topic = "cotton-erp-events"
        self.create_topic(main_topic)
        
        # 2. Create DLQ topic
        dlq_topic = "cotton-erp-events-dlq"
        self.create_topic(dlq_topic)
        
        # 3. Create main subscription with DLQ
        main_subscription = "cotton-erp-events-sub"
        self.create_subscription_with_dlq(
            subscription_name=main_subscription,
            topic_name=main_topic,
            dlq_topic_name=dlq_topic,
            max_delivery_attempts=5,
            ack_deadline_seconds=60,
        )
        
        # 4. Create DLQ subscription (for ops team to monitor failures)
        dlq_subscription = "cotton-erp-events-dlq-sub"
        self.create_dlq_subscription(
            dlq_subscription_name=dlq_subscription,
            dlq_topic_name=dlq_topic,
        )
        
        logger.info("=== DLQ Infrastructure Setup Complete ===")
        logger.info(f"Main Topic: {main_topic}")
        logger.info(f"Main Subscription: {main_subscription}")
        logger.info(f"DLQ Topic: {dlq_topic}")
        logger.info(f"DLQ Subscription: {dlq_subscription}")
        logger.info("\nNext steps:")
        logger.info("1. Grant Pub/Sub Publisher role to OutboxWorker service account")
        logger.info("2. Grant Pub/Sub Subscriber role to event consumers")
        logger.info("3. Set up monitoring alerts for DLQ topic")


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Configure GCP Pub/Sub with Dead Letter Queue support"
    )
    parser.add_argument(
        "--project-id",
        required=True,
        help="GCP Project ID",
    )
    
    args = parser.parse_args()
    
    configurator = PubSubDLQConfigurator(args.project_id)
    configurator.setup_complete_dlq_infrastructure()


if __name__ == "__main__":
    main()
