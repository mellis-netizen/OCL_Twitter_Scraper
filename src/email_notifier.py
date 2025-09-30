"""
Email Notification System for Crypto TGE Alerts
"""

import smtplib
import logging
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import List, Dict, Optional

from config import EMAIL_CONFIG, COMPANIES, TGE_KEYWORDS  # COMPANIES/KEYWORDS used in footer


class EmailNotifier:
    """Class for sending email notifications about TGE events."""

    def __init__(self):
        self.setup_logging()
        self.smtp_server = EMAIL_CONFIG.get('smtp_server')
        self.smtp_port = EMAIL_CONFIG.get('smtp_port')
        self.email_user = EMAIL_CONFIG.get('email_user')
        self.email_password = EMAIL_CONFIG.get('email_password')
        self.recipient_email = EMAIL_CONFIG.get('recipient_email')

        # Check if email is configured
        if not all([self.smtp_server, self.smtp_port, self.email_user, self.email_password, self.recipient_email]):
            self.logger.warning("Email configuration incomplete. Email notifications will be disabled.")
            self.enabled = False
        else:
            # Validate configuration
            if not self._validate_email_config():
                self.logger.warning("Email configuration validation failed. Email notifications will be disabled.")
                self.enabled = False
            else:
                self.enabled = True

    def setup_logging(self):
        """Setup logging configuration."""
        self.logger = logging.getLogger("email_notifier")

    def _sanitize_header(self, header: str) -> str:
        """Sanitize email header to prevent injection attacks."""
        if not header or not isinstance(header, str):
            return ""
        
        # Remove newlines and carriage returns to prevent header injection
        header = header.replace('\r', '').replace('\n', '').replace('\r\n', '')
        
        # Limit length
        header = header[:200]
        
        return header.strip()

    def _sanitize_content(self, content: str, escape_html: bool = True) -> str:
        """Enhanced sanitize email content with comprehensive security."""
        if not content or not isinstance(content, str):
            return ""

        # Use enhanced sanitization from utils
        from utils import sanitize_text, sanitize_html_content
        
        if escape_html:
            # For plain text content, use text sanitization with HTML escaping
            return sanitize_text(content, max_length=1024*1024, escape_html=True)
        else:
            # For HTML content, use HTML-specific sanitization
            return sanitize_html_content(content)

    def _clean_summary(self, summary: str) -> str:
        """Clean up article summary for email display."""
        if not summary:
            return "No summary available"

        # Remove HTML tags that might be in RSS content
        import re
        summary = re.sub(r'<[^>]+>', '', summary)

        # Clean up common RSS artifacts (but be careful with entity decoding)
        import html
        summary = html.unescape(summary)  # Properly decode HTML entities
        summary = re.sub(r'The post.*?appeared on.*$', '', summary)
        summary = re.sub(r'^\s*TLDR\s*', '', summary)

        # Enhanced sanitization with truncation
        from utils import sanitize_text
        return sanitize_text(summary.strip(), max_length=300, escape_html=True)

    def _sanitize_url(self, url: str) -> str:
        """Sanitize URLs for safe inclusion in emails."""
        from utils import validate_and_sanitize_url
        sanitized = validate_and_sanitize_url(url)
        return sanitized if sanitized else "#"

    def _validate_email_config(self) -> bool:
        """Validate email configuration."""
        try:
            # Validate SMTP server
            if not self.smtp_server or not isinstance(self.smtp_server, str):
                self.logger.error("Invalid SMTP server configuration")
                return False
            
            # Validate SMTP port
            if not isinstance(self.smtp_port, int) or not (1 <= self.smtp_port <= 65535):
                self.logger.error(f"Invalid SMTP port: {self.smtp_port}")
                return False
            
            # Validate email addresses
            if not self._validate_email(self.email_user):
                self.logger.error(f"Invalid sender email: {self.email_user}")
                return False
            
            # Validate recipient emails
            for recipient in self.recipient_email.split(','):
                recipient = recipient.strip()
                if not self._validate_email(recipient):
                    self.logger.error(f"Invalid recipient email: {recipient}")
                    return False
            
            # Validate password
            if not self.email_password or len(self.email_password) < 6:
                self.logger.error("Email password too short or empty")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Email configuration validation error: {str(e)}")
            return False

    def _validate_email(self, email: str) -> bool:
        """Validate email address format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email)) and len(email) <= 254

    # -------------------------
    # Low-level send helper (with detailed SMTP logging)
    # -------------------------
    def _send_email(self, subject: str, html: str, text: Optional[str] = None, max_retries: int = 3) -> bool:
        if not self.enabled:
            self.logger.warning("Email notifications disabled - configuration incomplete")
            return False

        # Sanitize inputs to prevent header injection
        subject = self._sanitize_header(subject)
        # Don't escape HTML in the main HTML content (it's already properly formatted)
        html = self._sanitize_content(html, escape_html=False)
        if text:
            text = self._sanitize_content(text, escape_html=True)

        # Build MIME message (HTML + optional plain text)
        msg = MIMEMultipart('alternative')
        msg['From'] = self.email_user
        msg['To'] = self.recipient_email
        msg['Subject'] = subject
        if text:
            msg.attach(MIMEText(text, 'plain', 'utf-8'))
        msg.attach(MIMEText(html, 'html', 'utf-8'))

        # Retry logic for email sending
        for attempt in range(max_retries):
            try:
                use_ssl = str(self.smtp_port) == "465"
                if use_ssl:
                    server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=20)
                else:
                    server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=20)

                try:
                    # Disable debug logging in production (only enable for troubleshooting)
                    server.set_debuglevel(0)
                    self.logger.info("Connecting to SMTP %s:%s (SSL=%s) [attempt %d/%d]", 
                                   self.smtp_server, self.smtp_port, use_ssl, attempt + 1, max_retries)

                    # EHLO before auth (and before STARTTLS on 587)
                    code, hello = server.ehlo()
                    self.logger.info("SMTP EHLO: %s %s", code, hello)

                    if not use_ssl:
                        # 587 path: STARTTLS upgrade
                        code, resp = server.starttls()
                        self.logger.info("SMTP STARTTLS: %s %s", code, resp)
                        code, hello2 = server.ehlo()
                        self.logger.info("SMTP EHLO (post-TLS): %s %s", code, hello2)

                    # Login
                    server.login(self.email_user, self.email_password)
                    self.logger.info("SMTP login OK for %s", self.email_user)

                    # Support multiple recipients separated by commas
                    from_addr = self.email_user
                    to_addrs = []
                    for addr in self.recipient_email.split(","):
                        addr = addr.strip()
                        if addr and self._validate_email(addr):
                            to_addrs.append(addr)
                        elif addr:
                            self.logger.warning("Invalid email address skipped: %s", addr)
                    
                    if not to_addrs:
                        self.logger.error("No valid recipient email addresses found")
                        return False

                    # Use sendmail so we can inspect refused recipients
                    refused = server.sendmail(from_addr, to_addrs, msg.as_string())

                    if refused:
                        # Dict of {recipient: (code, resp)} for failures
                        self.logger.error("SMTP refused recipients: %s", refused)
                        return False

                    self.logger.info("Email accepted by SMTP server for: %s", to_addrs)
                    return True

                finally:
                    try:
                        server.quit()
                    except Exception:
                        server.close()

            except smtplib.SMTPAuthenticationError as e:
                self.logger.error("SMTP authentication failed (attempt %d/%d): %s", attempt + 1, max_retries, e)
                if attempt == max_retries - 1:
                    return False
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            except smtplib.SMTPRecipientsRefused as e:
                self.logger.error("All recipients refused (attempt %d/%d): %s", attempt + 1, max_retries, getattr(e, "recipients", {}))
                if attempt == max_retries - 1:
                    return False
                time.sleep(2 ** attempt)
                continue
            except smtplib.SMTPException as e:
                self.logger.error("SMTP error (attempt %d/%d): %s", attempt + 1, max_retries, e)
                if attempt == max_retries - 1:
                    return False
                time.sleep(2 ** attempt)
                continue
            except Exception as e:
                self.logger.error("Unexpected error sending email (attempt %d/%d): %s", attempt + 1, max_retries, e)
                if attempt == max_retries - 1:
                    return False
                time.sleep(2 ** attempt)
                continue

        return False

    # -------------------------
    # Public API
    # -------------------------
    def send_tge_alert_email(
        self,
        news_alerts: List[Dict],
        twitter_alerts: List[Dict],
        meta: Optional[Dict] = None,
    ) -> bool:
        """Send email with TGE alerts from news and Twitter."""
        if not self.enabled:
            self.logger.warning("Email notifications disabled - configuration incomplete")
            return False

        # Even if there are no alerts, return True (pipeline shouldn’t error on “nothing found”)
        if not news_alerts and not twitter_alerts:
            self.logger.info("No TGE alerts to send")
            return True

        meta = meta or {}
        subject = self._generate_email_subject(news_alerts, twitter_alerts, meta)
        body = self._generate_email_body(news_alerts, twitter_alerts, meta)
        return self._send_email(subject, body)

    def send_test_email(self) -> bool:
        """
        Lightweight test used by test_components().
        Sends a small HTML test so the full SMTP path is exercised.
        """
        if not self.enabled:
            self.logger.warning("Email notifications disabled - cannot send test email.")
            return False

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        subject = "🧪 Crypto TGE Monitor — Test Email"
        html = f"""
        <html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <h2>✅ Crypto TGE Monitor — Test Email</h2>
            <p>This is a connectivity test from the monitor.</p>
            <p><strong>Time:</strong> {ts}</p>
        </body></html>
        """
        return self._send_email(subject, html, f"Crypto TGE Monitor test at {ts}")

    def send_weekly_summary(self, news_count: int, twitter_count: int, total_processed: int) -> bool:
        """Send weekly summary email."""
        if not self.enabled:
            return False
        try:
            # Use PST timezone for weekly summary
            from datetime import timezone, timedelta
            pst = timezone(timedelta(hours=-8))  # PST is UTC-8
            pst_time = datetime.now(pst)
            
            subject = f"📊 Weekly TGE Monitor Summary - Week of {pst_time.strftime('%Y-%m-%d')}"
            html = f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="UTF-8"></head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width:600px;margin:0 auto;padding:20px;">
                    <h2>📊 Weekly Summary — Week Ending {pst_time.strftime('%Y-%m-%d')} (PST)</h2>
                    <p>Here's your weekly TGE monitoring report:</p>
                    <ul>
                        <li><strong>Total items processed</strong>: {total_processed:,}</li>
                        <li><strong>TGE-related news alerts</strong>: {news_count}</li>
                        <li><strong>TGE-related Twitter alerts</strong>: {twitter_count}</li>
                        <li><strong>Total potential TGE alerts</strong>: {news_count + twitter_count}</li>
                    </ul>
                    <p><strong>Monitored Companies:</strong> {len(COMPANIES)} portfolio companies</p>
                    <p><strong>News Sources:</strong> {len(NEWS_SOURCES)} RSS feeds</p>
                    <p><em>Report generated at {pst_time.strftime('%Y-%m-%d %H:%M:%S')} PST</em></p>
                    <hr>
                    <p style="font-size:12px;color:#666;">This is an automated weekly report from the Crypto TGE Monitor. 
                    The system runs every Monday at 8:00 AM PST to scan for token launch announcements.</p>
                </div>
            </body>
            </html>
            """
            return self._send_email(subject, html)
        except Exception as e:
            self.logger.error("Failed to send weekly summary email: %s", e, exc_info=True)
            return False

    # -------------------------
    # Rendering helpers
    # -------------------------
    def _generate_email_subject(
        self,
        news_alerts: List[Dict],
        twitter_alerts: List[Dict],
        meta: Dict
    ) -> str:
        total = len(news_alerts) + len(twitter_alerts)
        rl = " (partial, rate-limited)" if meta.get("twitter_rate_limited") else ""
        
        # Collect high priority companies for subject
        high_priority_companies = set()
        high_confidence_alerts = 0
        
        for alert in (news_alerts + twitter_alerts):
            details = alert.get('match_details', {})
            if details.get('priority_level') == 'HIGH':
                high_priority_companies.update(details.get('matched_companies', []))
            if details.get('confidence_score', 0) >= 80:
                high_confidence_alerts += 1
        
        if total == 0:
            return f"Crypto TGE Monitor — No alerts{rl}"
        
        # Build informative subject
        priority_text = f" - {', '.join(list(high_priority_companies)[:2])}" if high_priority_companies else ""
        confidence_text = f" [{high_confidence_alerts} high confidence]" if high_confidence_alerts > 0 else ""
        
        if total == 1:
            src = (news_alerts or twitter_alerts)[0]
            details = src.get('match_details', {})
            companies = details.get('matched_companies', [])
            confidence = details.get('confidence_score', 0)
            label = companies[0] if companies else "Unknown"
            return f"🚀 TGE Alert: {label} ({confidence}% confidence){rl}"
        
        return f"🚀 {total} TGE Alerts{priority_text}{confidence_text}{rl}"

    def _news_item_from_alert(self, alert: Dict) -> Dict:
        """
        Normalize both shapes:
        - flat: {'title','link','summary','published','source',...}
        - nested: {'article': {...}, ...}
        """
        if "article" in alert and isinstance(alert["article"], dict):
            art = alert["article"]
            return {
                "title": art.get("title"),
                "link": art.get("link"),
                "summary": art.get("summary"),
                "published": art.get("published"),
                "source_name": art.get("source_name") or alert.get("source") or "",
            }
        # flat
        return {
            "title": alert.get("title"),
            "link": alert.get("link"),
            "summary": alert.get("summary"),
            "published": alert.get("published"),
            "source_name": alert.get("source") or "",
        }

    def _generate_email_body(
        self,
        news_alerts: List[Dict],
        twitter_alerts: List[Dict],
        meta: Dict
    ) -> str:
        ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        rl_banner = ""
        if meta.get("twitter_rate_limited"):
            rl_banner = (
                '<div style="background:#fff3cd;border:1px solid #ffeeba;padding:10px;'
                'border-radius:6px;margin-bottom:16px;">'
                '⚠️ Twitter/API rate limiting detected this cycle — results may be partial.'
                '</div>'
            )

        # Create alert summary
        all_companies = set()
        high_priority_companies = set()
        all_keywords = set()
        high_confidence_count = 0
        
        for alert in (news_alerts + twitter_alerts):
            details = alert.get('match_details', {})
            all_companies.update(details.get('matched_companies', []))
            if details.get('priority_level') == 'HIGH':
                high_priority_companies.update(details.get('matched_companies', []))
            all_keywords.update(details.get('matched_keywords', []))
            if details.get('confidence_score', 0) >= 80:
                high_confidence_count += 1
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #2c3e50;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                .container {{
                    background-color: white;
                    border-radius: 12px;
                    padding: 30px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                    border: 1px solid #e9ecef;
                }}
                .header {{
                    text-align: center;
                    border-bottom: 2px solid #007bff;
                    padding-bottom: 25px;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    color: #007bff;
                    margin: 0 0 10px 0;
                    font-size: 28px;
                    font-weight: 700;
                }}
                .header p {{
                    margin: 5px 0;
                    color: #6c757d;
                }}
                .alert-section {{
                    margin-bottom: 35px;
                    border: 1px solid #dee2e6;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
                }}
                .alert-header {{
                    background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
                    color: white;
                    padding: 15px 20px;
                    font-weight: 700;
                    font-size: 16px;
                }}
                .alert-content {{ padding: 20px; }}
                .alert-item {{
                    border-bottom: 1px solid #f1f3f4;
                    padding: 20px 0;
                    transition: background-color 0.2s ease;
                }}
                .alert-item:last-child {{ border-bottom: none; }}
                .alert-item:hover {{ background-color: #f8f9fa; }}
                .alert-title {{
                    font-size: 16px;
                    font-weight: 600;
                    color: #1a365d;
                    margin-bottom: 8px;
                    line-height: 1.4;
                }}
                .alert-meta {{
                    font-size: 13px;
                    color: #718096;
                    margin-bottom: 12px;
                }}
                .companies, .keywords, .tokens, .score {{
                    padding: 6px 12px;
                    border-radius: 6px;
                    margin: 4px 6px 4px 0;
                    display: inline-block;
                    font-size: 12px;
                    font-weight: 500;
                }}
                .companies {{
                    background-color: #e3f2fd;
                    color: #1565c0;
                    border: 1px solid #bbdefb;
                }}
                .keywords {{
                    background-color: #fff8e1;
                    color: #ef6c00;
                    border: 1px solid #ffcc02;
                }}
                .tokens {{
                    background-color: #f3e5f5;
                    color: #7b1fa2;
                    border: 1px solid #ce93d8;
                }}
                .score {{
                    background-color: #e8f5e8;
                    color: #2e7d32;
                    border: 1px solid #c8e6c9;
                    font-weight: 600;
                }}
                .tweet-content {{
                    background: #f8f9fa;
                    padding: 16px;
                    border-radius: 8px;
                    border-left: 4px solid #007bff;
                    margin: 12px 0;
                    font-style: italic;
                    color: #495057;
                }}
                .summary-content {{
                    background-color: #f8f9fa;
                    padding: 16px;
                    border-radius: 8px;
                    border-left: 4px solid #28a745;
                    font-size: 14px;
                    color: #495057;
                    line-height: 1.5;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 2px solid #e9ecef;
                    color: #6c757d;
                    font-size: 13px;
                }}
                .link {{
                    color: #007bff;
                    text-decoration: none;
                    font-weight: 500;
                    padding: 8px 16px;
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    display: inline-block;
                    margin: 8px 0;
                    transition: all 0.2s ease;
                }}
                .link:hover {{
                    background-color: #007bff;
                    color: white;
                    text-decoration: none;
                }}
                @media only screen and (max-width: 600px) {{
                    body {{ padding: 10px; }}
                    .container {{ padding: 20px; }}
                    .alert-content {{ padding: 15px; }}
                    .companies, .keywords, .score {{
                        display: block;
                        margin: 4px 0;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 Crypto TGE Monitor Alert</h1>
                    <p>Token Generation Event Detection Report</p>
                    <p><strong>{ts}</strong></p>
                    {rl_banner}
                </div>
                
                <div style="background-color: #e3f2fd; border: 2px solid #1976d2; border-radius: 8px; padding: 20px; margin: 20px 0;">
                    <h2 style="margin-top: 0; color: #1976d2;">📋 Alert Summary</h2>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                        <div>
                            <strong>Total Alerts:</strong> {len(news_alerts) + len(twitter_alerts)}<br>
                            <strong>News Alerts:</strong> {len(news_alerts)}<br>
                            <strong>Twitter Alerts:</strong> {len(twitter_alerts)}
                        </div>
                        <div>
                            <strong>Companies Detected:</strong> {len(all_companies)}<br>
                            <strong>High Priority:</strong> {len(high_priority_companies)}<br>
                            <strong>High Confidence Alerts:</strong> {high_confidence_count}
                        </div>
                    </div>
                    {f'<div style="margin-top: 15px;"><strong>🏢 Companies:</strong> {", ".join(sorted(all_companies))}</div>' if all_companies else ''}
                    {f'<div style="margin-top: 10px;"><strong>🚨 High Priority Companies:</strong> <span style="color: #d32f2f; font-weight: bold;">{", ".join(sorted(high_priority_companies))}</span></div>' if high_priority_companies else ''}
                </div>
        """

        # News section
        if news_alerts:
            html += f"""
                <div class="alert-section">
                    <div class="alert-header">📰 News Alerts ({len(news_alerts)} found)</div>
                    <div class="alert-content">
            """
            for alert in news_alerts:
                art = self._news_item_from_alert(alert)
                pubs = art.get('published')
                if isinstance(pubs, datetime):
                    try:
                        if pubs.tzinfo is None:
                            pubs = pubs.replace(tzinfo=timezone.utc)
                        pub_str = pubs.strftime('%Y-%m-%d %H:%M UTC')
                    except Exception:
                        pub_str = str(pubs)
                else:
                    pub_str = 'Unknown'

                # Extract match details for enhanced display
                match_details = alert.get('match_details', {})
                companies = match_details.get('matched_companies', [])
                keywords = match_details.get('matched_keywords', [])
                tokens = match_details.get('matched_tokens', [])
                confidence = match_details.get('confidence_score', 0)
                strategy = match_details.get('match_strategy', 'unknown')
                priority = match_details.get('priority_level', 'UNKNOWN')
                match_reasons = match_details.get('match_reasons', [])

                # Generate company tags with priority indicators
                comps = ''.join(f'<span class="companies" title="Priority: {priority}">🏢 {c}</span>'
                                for c in sorted(companies))

                # Generate keyword tags with strategy info
                keys = ''.join(f'<span class="keywords" title="Strategy: {strategy}">🔑 {k}</span>'
                               for k in sorted(keywords))

                # Add token tags if any
                token_tags = ''.join(f'<span class="tokens" title="Token Symbol">🪙 {t}</span>'
                                   for t in sorted(tokens)) if tokens else ''

                # Enhanced confidence score with strategy info
                score = f'<span class="score" title="Strategy: {strategy}">📊 {confidence}% confidence</span>'
                
                # Format match reasons
                match_reasons_html = ''
                if match_reasons:
                    match_reasons_html = '''
                    <div style="margin: 8px 0; padding: 8px; background-color: #e8f5e9; border-left: 4px solid #4caf50; border-radius: 4px;">
                        <strong>✅ Match Reasons:</strong>
                        <ul style="margin: 4px 0; padding-left: 20px;">
                    '''
                    for reason in match_reasons:
                        match_reasons_html += f'<li>{self._sanitize_content(reason)}</li>'
                    match_reasons_html += '</ul></div>'

                html += f"""
                        <div class="alert-item">
                            <div class="alert-title">{self._sanitize_content(art.get('title') or 'Untitled')}</div>
                            <div class="company-info" style="margin: 8px 0; padding: 8px; background-color: #f0f8ff; border-left: 4px solid #007bff; border-radius: 4px;">
                                <strong>🎯 Detected Companies:</strong> {comps or '<span style="color: #666;">None detected</span>'}
                            </div>
                            <div class="alert-meta">
                                <strong>Source:</strong> {self._sanitize_content(art.get('source_name',''))} |
                                <strong>Published:</strong> {pub_str}
                            </div>
                            <div><a href="{self._sanitize_url(art.get('link'))}" class="link" target="_blank" rel="noopener noreferrer">Read Full Article →</a></div>
                            <div class="keyword-info" style="margin: 8px 0; padding: 8px; background-color: #fff8e1; border-left: 4px solid #ffa000; border-radius: 4px;">
                                <strong>🔍 Triggering Keywords:</strong> {keys or '<span style="color: #666;">None detected</span>'}
                                {f'<br><strong>🪙 Token Symbols:</strong> {token_tags}' if token_tags else ''}
                            </div>
                            <div style="margin-top: 8px;">{score}</div>
                            {match_reasons_html}
                            <div class="summary-content" style="margin-top: 12px;">
                                {self._clean_summary(art.get('summary') or '')}
                            </div>
                        </div>
                """
            html += "</div></div>"

        # Twitter section
        if twitter_alerts:
            html += f"""
                <div class="alert-section">
                    <div class="alert-header">🐦 Twitter Alerts ({len(twitter_alerts)} found)</div>
                    <div class="alert-content">
            """
            for alert in twitter_alerts:
                tweet = alert.get('tweet', {})
                ts_t = tweet.get('created_at')
                if isinstance(ts_t, datetime):
                    try:
                        if ts_t.tzinfo is None:
                            ts_t = ts_t.replace(tzinfo=timezone.utc)
                        ts_str = ts_t.strftime('%Y-%m-%d %H:%M UTC')
                    except Exception:
                        ts_str = str(ts_t)
                else:
                    ts_str = 'Unknown'

                # Extract match details for Twitter alerts
                match_details = alert.get('match_details', {})
                companies = match_details.get('matched_companies', [])
                keywords = match_details.get('matched_keywords', [])
                tokens = match_details.get('matched_tokens', [])
                confidence = match_details.get('confidence_score', 0)
                strategy = match_details.get('match_strategy', 'unknown')
                priority = match_details.get('priority_level', 'UNKNOWN')
                match_reasons = match_details.get('match_reasons', [])

                # Generate company tags
                comps = ''.join(f'<span class="companies" title="Priority: {priority}">🏢 {c}</span>'
                                for c in sorted(companies))

                # Generate keyword tags
                keys = ''.join(f'<span class="keywords" title="Strategy: {strategy}">🔑 {k}</span>'
                               for k in sorted(keywords))

                # Add token tags if any
                token_tags = ''.join(f'<span class="tokens" title="Token Symbol">🪙 {t}</span>'
                                   for t in sorted(tokens)) if tokens else ''

                # Enhanced confidence score
                score = f'<span class="score" title="Strategy: {strategy}">📊 {confidence}% confidence</span>'
                
                # Format match reasons for Twitter
                match_reasons_html = ''
                if match_reasons:
                    match_reasons_html = '''
                    <div style="margin: 8px 0; padding: 8px; background-color: #e8f5e9; border-left: 4px solid #4caf50; border-radius: 4px;">
                        <strong>✅ Match Reasons:</strong>
                        <ul style="margin: 4px 0; padding-left: 20px;">
                    '''
                    for reason in match_reasons:
                        match_reasons_html += f'<li>{self._sanitize_content(reason)}</li>'
                    match_reasons_html += '</ul></div>'

                html += f"""
                        <div class="alert-item">
                            <div class="alert-title">@{tweet.get('user',{}).get('screen_name','unknown')} - {tweet.get('user',{}).get('name','Unknown')}</div>
                            <div class="company-info" style="margin: 8px 0; padding: 8px; background-color: #f0f8ff; border-left: 4px solid #007bff; border-radius: 4px;">
                                <strong>🎯 Detected Companies:</strong> {comps or '<span style="color: #666;">None detected</span>'}
                            </div>
                            <div class="alert-meta">
                                <strong>Posted:</strong> {ts_str} |
                                <strong>Engagement:</strong> {tweet.get('retweet_count',0)} RTs, {tweet.get('favorite_count',0)} Likes |
                                <strong>Followers:</strong> {tweet.get('user',{}).get('followers_count',0):,}
                            </div>
                            <div><a href="{self._sanitize_url(tweet.get('url'))}" class="link" target="_blank" rel="noopener noreferrer">View Tweet →</a></div>
                            <div class="tweet-content">{self._sanitize_content(tweet.get('text',''))}</div>
                            <div class="keyword-info" style="margin: 8px 0; padding: 8px; background-color: #fff8e1; border-left: 4px solid #ffa000; border-radius: 4px;">
                                <strong>🔍 Triggering Keywords:</strong> {keys or '<span style="color: #666;">None detected</span>'}
                                {f'<br><strong>🪙 Token Symbols:</strong> {token_tags}' if token_tags else ''}
                            </div>
                            <div style="margin-top: 8px;">{score}</div>
                            {match_reasons_html}
                        </div>
                """
            html += "</div></div>"

        # Footer
        html += f"""
                <div class="footer">
                    <p>This alert was generated by the Crypto TGE Monitor system.</p>
                    <p>Monitor configured for {len(COMPANIES)} companies and {len(TGE_KEYWORDS)} TGE keywords.</p>
                    <p>Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html
