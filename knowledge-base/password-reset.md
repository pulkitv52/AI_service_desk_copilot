# Self-Service Password Reset Guide

## Metadata

- Source Identifier: KB-SEC-001
- Category: Identity and Access Management
- Last Updated: 2026-09-15

## Problem Description

Employees are locked out of their domain account or need to reset an expired corporate Active Directory password without calling the Service Desk.

## Symptoms

- User receives "The user name or password is incorrect" on Windows login.
- Account is temporarily locked out due to multiple failed logon attempts.
- Microsoft 365 or Single Sign-On portal rejects credentials.

## Preconditions

- The employee has previously registered authentication methods in the corporate Self-Service Password Reset (SSPR) portal.
- Access to an approved multi-factor authentication (MFA) device or registered mobile number.

## Resolution Steps

1. Navigate to the corporate SSPR portal at `https://passwordreset.corp.internal`.
2. Enter your corporate user principal name (e.g., `username@corp.com`) and complete the security verification captcha.
3. Choose your verification method:
   - Authenticator App push notification or 6-digit one-time code.
   - SMS verification code sent to your registered mobile device.
4. Once verified, specify a new password that satisfies the corporate password policy:
   - Minimum 14 characters in length.
   - At least one uppercase letter and one lowercase letter.
   - At least one number and one special symbol.
   - Must not contain your username, first name, or last name.
   - Cannot match any of your last 10 previous passwords.
5. Submit the form and wait 60 seconds for Active Directory replication across all domain controllers.
6. Reconnect your corporate laptop to the corporate network or GlobalProtect VPN and log in with the new password.

## Escalation Conditions

- The user has not registered MFA verification methods and cannot verify identity.
- Account remains locked after successful password reset.
- User is on an isolated machine and cannot establish network connectivity to domain controllers.
- In these cases, create an incident ticket assigned to the Identity & Access Support group.
