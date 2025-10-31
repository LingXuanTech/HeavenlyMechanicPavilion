"""Alerting service for critical failures and events."""

from __future__ import annotations

import logging
import smtplib
from collections import deque
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Deque, Dict, Optional
from enum import Enum
from datetime import datetime
import json

import aiohttp
from pydantic import BaseModel

from ..config.settings import Settings

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """Alert level enumeration."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertingService:
    """Service for sending alerts via email and webhooks."""

    def __init__(self, settings: Settings):
        """初始化告警服务.
        
        Args:
            settings: 应用配置
        """
        self.settings = settings
        self._alert_history: Deque[Dict[str, Any]] = deque(maxlen=100)

    async def send_alert(
        self,
        title: str,
        message: str,
        level: AlertLevel = AlertLevel.ERROR,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send an alert.

        Args:
            title: Alert title
            message: Alert message
            level: Alert level
            metadata: Optional metadata

        Returns:
            True if alert was sent successfully, False otherwise
        """
        alert_data = {
            "title": title,
            "message": message,
            "level": level.value,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._alert_history.append(alert_data)

        success = True
        if self.settings.alerting_enabled:
            if self.settings.alert_email_to:
                email_sent = await self._send_email_alert(
                    title, message, level, metadata
                )
                if not email_sent:
                    success = False

            if self.settings.alert_webhook_url:
                webhook_sent = await self._send_webhook_alert(
                    title, message, level, metadata
                )
                if not webhook_sent:
                    success = False
        else:
            logger.info(f"Alerting disabled, skipping alert: {title}")

        return success

    async def _send_email_alert(
        self,
        title: str,
        message: str,
        level: AlertLevel,
        metadata: Optional[Dict[str, Any]],
    ) -> bool:
        """Send alert via email.

        Args:
            title: Alert title
            message: Alert message
            level: Alert level
            metadata: Optional metadata

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.settings.smtp_host or not self.settings.alert_email_to:
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[{level.value.upper()}] {title}"
        msg["From"] = self.settings.smtp_from
        msg["To"] = self.settings.alert_email_to

        text_part = self._format_email_text(title, message, level, metadata)
        html_part = self._format_email_html(title, message, level, metadata)

        msg.attach(MIMEText(text_part, "plain"))
        msg.attach(MIMEText(html_part, "html"))

        try:
            self._send_smtp_email(msg)
            return True
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False

    def _send_smtp_email(self, msg: MIMEMultipart):
        """Send email using SMTP.

        Args:
            msg: Email message
        """
        if self.settings.smtp_tls:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
                server.starttls()
                server.login(self.settings.smtp_user, self.settings.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
                server.send_message(msg)

    def _format_email_text(
        self,
        title: str,
        message: str,
        level: AlertLevel,
        metadata: Optional[Dict[str, Any]],
    ) -> str:
        """Format email as plain text.

        Args:
            title: Alert title
            message: Alert message
            level: Alert level
            metadata: Optional metadata

        Returns:
            Plain text email body
        """
        body = f"ALERT: {title}\n"
        body += f"Level: {level.value.upper()}\n"
        body += f"Time: {datetime.utcnow().isoformat()}\n\n"
        body += f"{message}\n\n"

        if metadata:
            body += "Metadata:\n"
            for key, value in metadata.items():
                body += f"- {key}: {value}\n"

        return body

    def _format_email_html(
        self,
        title: str,
        message: str,
        level: AlertLevel,
        metadata: Optional[Dict[str, Any]],
    ) -> str:
        """Format email as HTML.

        Args:
            title: Alert title
            message: Alert message
            level: Alert level
            metadata: Optional metadata

        Returns:
            HTML email body
        """
        level_color = {
            AlertLevel.INFO: "#3b82f6",
            AlertLevel.WARNING: "#f59f00",
            AlertLevel.ERROR: "#ef476f",
            AlertLevel.CRITICAL: "#ef476f",
        }.get(level, "#6b7280")

        html = f"""
        <html>
            <body style="font-family: sans-serif; color: #111827;">
                <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px;">
                    <h1 style="color: {level_color}; font-size: 24px;">{level.value.upper()}: {title}</h1>
                    <p><strong>Time:</strong> {datetime.utcnow().isoformat()}</p>
                    <p>{message}</p>
        """

        if metadata:
            html += "<h2>Metadata</h2><ul>"
            for key, value in metadata.items():
                html += f"<li><strong>{key}:</strong> {value}</li>"
            html += "</ul>"

        html += "</div></body></html>"
        return html

    async def _send_webhook_alert(
        self,
        title: str,
        message: str,
        level: AlertLevel,
        metadata: Optional[Dict[str, Any]],
    ) -> bool:
        """Send alert via webhook.

        Args:
            title: Alert title
            message: Alert message
            level: Alert level
            metadata: Optional metadata

        Returns:
            True if webhook was sent successfully, False otherwise
        """
        if not self.settings.alert_webhook_url:
            return False

        try:
            payload = {
                "title": title,
                "message": message,
                "level": level.value,
                "metadata": metadata or {},
            }

            headers = {"Content-Type": "application/json"}
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
        return list(self._alert_history)[-limit:]
