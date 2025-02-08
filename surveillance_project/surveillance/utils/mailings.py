import numpy as np
from collections import Counter
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Count
from datetime import datetime, timedelta
from django.utils import timezone  # Add this import

from ..models import Alert


class ThreatStatistics:
    def __init__(self):
        self.alerts_model = Alert

    def get_threat_statistics_test(self, time_window_minutes=60):
        """
        Get threat statistics for the specified time window in minutes
        Args:
            time_window_minutes (int): Number of minutes to look back (default: 60 minutes)
        """
        try:
            # Use timezone.now() instead of datetime.now()
            time_threshold = timezone.now() - timedelta(minutes=time_window_minutes)

            print("=== Debug Information ===")
            print(f"Current time: {timezone.now()}")
            print(f"Time threshold: {time_threshold}")

            # Get all alerts and print their count
            all_alerts = self.alerts_model.objects.all()
            print(f"Total alerts in database: {all_alerts.count()}")

            # Print some sample timestamps
            print("\nSample alert timestamps:")
            for alert in all_alerts[:5]:
                print(f"Alert ID: {alert.id}, Timestamp: {alert.timestamp}, Type: {alert.threat_type}")

            # Get recent alerts
            recent_alerts = self.alerts_model.objects.filter(
                timestamp__gte=time_threshold
            )
            print(f"\nRecent alerts count: {recent_alerts.count()}")

            # Print recent alert details
            print("\nRecent alert details:")
            for alert in recent_alerts[:5]:
                print(f"Alert ID: {alert.id}, Timestamp: {alert.timestamp}, Type: {alert.threat_type}")

            # Count threats by type with error handling
            threat_counts = []
            try:
                threat_counts = recent_alerts.values('threat_type') \
                    .annotate(count=Count('id')) \
                    .order_by('-count')
                print("\nThreat counts:", list(threat_counts))
            except Exception as e:
                print(f"Error in threat counting: {str(e)}")

            # Get top threats with error handling
            top_threats = []
            try:
                top_threats = recent_alerts.order_by('-confidence')[:3]
                print("\nTop threats:", list(top_threats))
            except Exception as e:
                print(f"Error in top threats: {str(e)}")

            return {
                'threat_counts': list(threat_counts),
                'top_threats': list(top_threats),
                'total_alerts': recent_alerts.count(),
                'time_window': f'Last {time_window_minutes} minutes',
                'query_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        except Exception as e:
            print(f"Critical error in get_threat_statistics: {str(e)}")
            return {
                'error': str(e),
                'threat_counts': [],
                'top_threats': [],
                'total_alerts': 0,
                'time_window': f'Last {time_window_minutes} minutes',
                'query_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }