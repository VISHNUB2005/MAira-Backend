"""MAIRA Phase 1 - Live SMTP Relay Verification and Diagnostics.

Tests:
1. Configuration loading and secret sanitization
2. DNS resolution for SMTP host
3. TCP socket connectivity to host:port
4. TLS/STARTTLS handshake negotiation
5. SMTP authentication
6. Live email delivery (if credentials valid)
"""

import argparse
import html
import logging
import os
import smtplib
import socket
import ssl
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from email.message import EmailMessage
from typing import Optional, Tuple

from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("maira.smtp_verify")


def mask_string(val: Optional[str], is_email: bool = False) -> str:
    if not val:
        return "<NOT SET>"
    if is_email and "@" in val:
        local, domain = val.split("@", 1)
        masked_local = (local[0] + "***" + local[-1]) if len(local) > 2 else (local[0] + "***")
        return f"{masked_local}@{domain}"
    return f"*** ({len(val)} chars)"


def inspect_smtp_config():
    settings = get_settings()
    print("=" * 65)
    print("MAIRA Phase 1 — SMTP Configuration Inspection")
    print("=" * 65)
    print(f"EMAIL_PROVIDER:     {settings.EMAIL_PROVIDER}")
    print(f"EMAIL_HOST:         {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT:         {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS:      {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_TIMEOUT:      {settings.EMAIL_TIMEOUT}s")
    print(f"EMAIL_FROM_NAME:    {settings.EMAIL_FROM_NAME}")
    print(f"EMAIL_FROM_ADDRESS: {settings.EMAIL_FROM_ADDRESS}")
    print(f"EMAIL_USERNAME:     {mask_string(settings.EMAIL_USERNAME, is_email=True)}")
    print(f"EMAIL_PASSWORD:     {mask_string(settings.EMAIL_PASSWORD)}")
    print("=" * 65)
    return settings


def test_dns_resolution(host: str, port: int) -> Tuple[bool, str]:
    print("\n[Stage 1] Testing DNS Resolution for host:", host)
    try:
        addr_info = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        ips = sorted(list(set(info[4][0] for info in addr_info)))
        print(f"  [PASS] DNS resolved successfully to {len(ips)} IP address(es): {', '.join(ips[:4])}")
        return True, f"Resolved to {ips[0]}"
    except socket.gaierror as e:
        err = f"DNS resolution failed: {e.strerror or type(e).__name__}"
        print(f"  [FAIL] {err}")
        return False, err
    except Exception as e:
        err = f"DNS resolution failed: {type(e).__name__}"
        print(f"  [FAIL] {err}")
        return False, err


def test_tcp_connectivity(host: str, port: int, timeout: float) -> Tuple[bool, str]:
    print(f"\n[Stage 2] Testing TCP Socket Connectivity to {host}:{port} (timeout={timeout}s)...")
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        print(f"  [PASS] TCP socket connection established successfully.")
        return True, "TCP connection successful"
    except (socket.timeout, TimeoutError):
        err = f"TCP connection timed out after {timeout}s"
        print(f"  [FAIL] {err}")
        return False, err
    except ConnectionRefusedError:
        err = f"TCP connection refused by {host}:{port}"
        print(f"  [FAIL] {err}")
        return False, err
    except OSError as e:
        err = f"TCP socket connection error: {e.strerror or type(e).__name__}"
        print(f"  [FAIL] {err}")
        return False, err


def test_tls_and_auth(settings, test_email: Optional[str] = None) -> Tuple[bool, str, str]:
    """Tests TLS handshake, SMTP authentication, and optionally sends an OTP email."""
    host = settings.EMAIL_HOST
    port = settings.EMAIL_PORT
    use_tls = settings.EMAIL_USE_TLS
    timeout = settings.EMAIL_TIMEOUT
    username = settings.EMAIL_USERNAME
    password = settings.EMAIL_PASSWORD
    from_addr = settings.EMAIL_FROM_ADDRESS
    from_name = settings.EMAIL_FROM_NAME

    print(f"\n[Stage 3] Testing TLS Handshake & Negotiation on {host}:{port}...")
    server = None
    try:
        if use_tls and port == 465:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, timeout=timeout, context=context)
            print("  [PASS] Implicit SSL/TLS connection established.")
        else:
            server = smtplib.SMTP(host, port, timeout=timeout)
            ehlo_code, _ = server.ehlo()
            if use_tls:
                if not server.has_extn("starttls"):
                    err = "Server does not support STARTTLS"
                    print(f"  [FAIL] {err}")
                    return False, "TLS_FAIL", err
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()
                print("  [PASS] STARTTLS negotiation completed successfully.")
            else:
                print("  [INFO] TLS not requested (plain connection).")

        print(f"\n[Stage 4] Testing SMTP Authentication...")
        if not username or not password or username == "mock_user@example.com":
            print(f"  [BLOCKED] Placeholder/Mock credentials detected: username='{mask_string(username, is_email=True)}'. Real institutional SMTP credentials required.")
            return False, "AUTH_PLACEHOLDER", "Mock/placeholder credentials configured"

        try:
            auth_res = server.login(username, password)
            print(f"  [PASS] SMTP authentication succeeded: {auth_res}")
        except smtplib.SMTPAuthenticationError as e:
            sanitized_err = f"Authentication rejected by SMTP relay: code={e.smtp_code}, message={str(e.smtp_error)[:100]}"
            print(f"  [FAIL] {sanitized_err}")
            return False, "AUTH_REJECTED", sanitized_err
        except smtplib.SMTPServerDisconnected as e:
            sanitized_err = f"SMTP server unexpectedly disconnected during auth: {type(e).__name__}"
            print(f"  [FAIL] {sanitized_err}")
            return False, "AUTH_DISCONNECTED", sanitized_err

        if test_email:
            print(f"\n[Stage 5] Sending test registration OTP email to {mask_string(test_email, is_email=True)}...")
            msg = EmailMessage()
            msg["Subject"] = f"{settings.APP_NAME}: Verification Test Delivery"
            msg["From"] = f"{from_name} <{from_addr}>"
            msg["To"] = test_email
            msg.set_content(
                f"This is a live SMTP integration verification test from {settings.APP_NAME}.\n"
                f"Generated verification test code: 849201\n"
                f"Expires in {settings.OTP_EXPIRY_MINUTES} minutes."
            )
            server.send_message(msg)
            print(f"  [PASS] Message accepted by SMTP relay for delivery to {mask_string(test_email, is_email=True)}.")
            return True, "DELIVERED", "Email sent and accepted by relay"

        return True, "AUTH_SUCCESS", "Authentication successful"

    except (smtplib.SMTPConnectError, ConnectionResetError, OSError) as e:
        sanitized_err = f"Connection error during TLS/SMTP exchange: {type(e).__name__}"
        print(f"  [FAIL] {sanitized_err}")
        return False, "CONNECTION_ERROR", sanitized_err
    except smtplib.SMTPException as e:
        sanitized_err = f"SMTP protocol error: {type(e).__name__}"
        print(f"  [FAIL] {sanitized_err}")
        return False, "PROTOCOL_ERROR", sanitized_err
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="MAIRA Live SMTP Verification")
    parser.add_argument("--test-email", type=str, default=None, help="Authorized destination email for test OTP dispatch")
    args = parser.parse_args()

    settings = inspect_smtp_config()

    # Step 1: DNS Resolution
    dns_ok, dns_msg = test_dns_resolution(settings.EMAIL_HOST, settings.EMAIL_PORT)
    if not dns_ok:
        print(f"\n[SUMMARY] SMTP Verification BLOCKED: {dns_msg}")
        sys.exit(1)

    # Step 2: TCP Connectivity
    tcp_ok, tcp_msg = test_tcp_connectivity(settings.EMAIL_HOST, settings.EMAIL_PORT, settings.EMAIL_TIMEOUT)
    if not tcp_ok:
        print(f"\n[SUMMARY] SMTP Verification BLOCKED: {tcp_msg}")
        sys.exit(2)

    # Step 3 & 4: TLS & Auth
    auth_ok, stage, msg = test_tls_and_auth(settings, test_email=args.test_email)
    print("\n" + "=" * 65)
    print("SMTP Verification Summary:")
    print(f"  DNS Resolution:    {'PASS' if dns_ok else 'FAIL'}")
    print(f"  TCP Connectivity:  {'PASS' if tcp_ok else 'FAIL'}")
    print(f"  TLS Handshake:     {'PASS' if stage not in ('TLS_FAIL', 'CONNECTION_ERROR') else 'FAIL'}")
    print(f"  Authentication:    {'PASS' if auth_ok else 'FAIL/BLOCKED'} ({stage}: {msg})")
    print("=" * 65)

    if not auth_ok:
        sys.exit(3)
    sys.exit(0)


if __name__ == "__main__":
    main()
