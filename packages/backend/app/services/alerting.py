"""Alerting service for critical failures and events."""

from __future__ import annotations

import asyncio
import json
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Dict, Optional

import aiohttp

from ..dependencies import get_settings

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertingService:
    """Service for sending alerts via email and webhooks."""

    def __init__(self):
        """Initialize the alerting service."""
        self.settings = get_settings()
        self._alert_history: list[Dict[str, Any]] = []
        self._max_history = 100

    async def send_alert(
        self,
        title: str,
        message: str,
        level: AlertLevel = AlertLevel.ERROR,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send an alert via configured channels.
        
        Args:
            title: Alert title
            message: Alert message
            level: Alert severity level
            details: Additional details dictionary
            
        Returns:
            True if alert was sent successfully
        """
        if not self.settings.alerting_enabled:
            logger.debug(f"Alerting disabled, skipping alert: {title}")
            return False

        # Record in history
        alert_data = {
            "title": title,
            "message": message,
            "level": level,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._alert_history.append(alert_data)
        
        # Trim history
        if len(self._alert_history) > self._max_history:
            self._alert_history = self._alert_history[-self._max_history:]

        # Send via configured channels
        tasks = []
        
        if self.settings.alert_email_enabled:
            tasks.append(self._send_email_alert(title, message, level, details))
        
        if self.settings.alert_webhook_enabled:
            tasks.append(self._send_webhook_alert(title, message, level, details))

        if not tasks:
            logger.warning("No alert channels configured")
            return False

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Return True if at least one channel succeeded
        success = any(r is True for r in results if not isinstance(r, Exception))
        
        if not success:
            logger.error(f"All alert channels failed for alert: {title}")
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Alert channel error: {result}")
        
        return success

    async def _send_email_alert(
        self,
        title: str,
        message: str,
        level: AlertLevel,
        details: Optional[Dict[str, Any]],
    ) -> bool:
        """Send alert via email.
        
        Args:
            title: Alert title
            message: Alert message
            level: Alert severity level
            details: Additional details
            
        Returns:
            True if email was sent successfully
        """
        if not all([
            self.settings.alert_email_to,
            self.settings.alert_email_from,
            self.settings.smtp_host,
        ]):
            logger.warning("Email alerting not fully configured")
            return False

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[TradingAgents {level.upper()}] {title}"
            msg["From"] = self.settings.alert_email_from
            msg["To"] = self.settings.alert_email_to

            # Create email body
            text_body = self._format_email_text(title, message, level, details)
            html_body = self._format_email_html(title, message, level, details)

            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            # Send email (run in thread pool to avoid blocking)
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._send_smtp_email,
                msg,
            )

            logger.info(f"Alert email sent: {title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False

    def _send_smtp_email(self, msg: MIMEMultipart):
        """Send email via SMTP (synchronous).
        
        Args:
            msg: Email message to send
        """
        if self.settings.smtp_use_tls:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
                server.starttls()
                if self.settings.smtp_username and self.settings.smtp_password:
                    server.login(self.settings.smtp_username, self.settings.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
                if self.settings.smtp_username and self.settings.smtp_password:
                    server.login(self.settings.smtp_username, self.settings.smtp_password)
                server.send_message(msg)

    def _format_email_text(
        self,
        title: str,
        message: str,
        level: AlertLevel,
        details: Optional[Dict[str, Any]],
    ) -> str:
        """Format alert as plain text email.
        
        Args:
            title: Alert title
            message: Alert message
            level: Alert severity level
            details: Additional details
            
        Returns:
            Formatted text body
        """
        lines = [
            f"TradingAgents Alert - {level.upper()}",
            "=" * 50,
            "",
            f"Title: {title}",
            f"Level: {level.upper()}",
            f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "Message:",
            message,
        ]

        if details:
            lines.extend([
                "",
                "Additional Details:",
                json.dumps(details, indent=2),
            ])

        return "\n".join(lines)

    def _format_email_html(
        self,
        title: str,
        message: str,
        level: AlertLevel,
        details: Optional[Dict[str, Any]],
    ) -> str:
        """Format alert as HTML email.
        
        Args:
            title: Alert title
            message: Alert message
            level: Alert severity level
            details: Additional details
            
        Returns:
            Formatted HTML body
        """
        level_colors = {
            AlertLevel.INFO: "#0ea5e9",
            AlertLevel.WARNING: "#f59e0b",
            AlertLevel.ERROR: "#ef4444",
            AlertLevel.CRITICAL: "#991b1b",
        }
        
        color = level_colors.get(level, "#6b7280")
        
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background-color: {color}; color: white; padding: 15px; border-radius: 5px;">
                        <h2 style="margin: 0;">TradingAgents Alert - {level.upper()}</h2>
                    </div>
                    
                    <div style="padding: 20px; background-color: #f9fafb; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 5px 5px;">
                        <h3 style="margin-top: 0;">{title}</h3>
                        <p><strong>Time:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                        
                        <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
                            <h4 style="margin-top: 0;">Message:</h4>
                            <p>{message}</p>
                        </div>
        """
        
        if details:
            html += """
                        <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
                            <h4 style="margin-top: 0;">Additional Details:</h4>
                            <pre style="background-color: #f3f4f6; padding: 10px; border-radius: 3px; overflow-x: auto;">
            """
            html += json.dumps(details, indent=2)
            html += """
                            </pre>
                        </div>
            """
        
        html += """
                    </div>
                </div>
            </body>
        </html>
        """
        
        return html

    async def _send_webhook_alert(
        self,
        title: str,
        message: str,
        level: AlertLevel,
        details: Optional[Dict[str, Any]],
    ) -> bool:
        """Send alert via webhook.
        
        Args:
            title: Alert title
            message: Alert message
            level: Alert severity level
            details: Additional details
            
        Returns:
            True if webhook was sent successfully
        """
        if not self.settings.alert_webhook_url:
            logger.warning("Webhook URL not configured")
            return False

        try:
            payload = {
                "title": title,
                "message": message,
                "level": level,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": details or {},
                "source": "TradingAgents",
            }

            headers = {"Content-Type": "application/json"}
            
            # Parse custom headers if provided
            if self.settings.alert_webhook_headers:
                try:
                    custom_headers = json.loads(self.settings.alert_webhook_headers)
                    headers.update(custom_headers)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse webhook headers")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.settings.alert_webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status >= 200 and response.status < 300:
                        logger.info(f"Alert webhook sent: {title}")
                        return True
                    else:
                        logger.error(f"Webhook returned status {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False

    def get_alert_history(self, limit: int = 50) -> list[Dict[str, Any]]:
        """Get recent alert history.
        
        Args:
            limit: Maximum number of alerts to return
            
        Returns:
            List of recent alerts
        """
        return self._alert_history[-limit:]


# Global alerting service instance
_alerting_service: Optional[AlertingService] = None


def get_alerting_service() -> AlertingService:
    """Get or create the global alerting service instance.
    
    Returns:
        AlertingService instance
    """
    global _alerting_service
    if _alerting_service is None:
        _alerting_service = AlertingService()
    return _alerting_service
