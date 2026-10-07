# Endpoint Low Disk Space Remediation Guide

## Metadata

- Source Identifier: KB-EUC-003
- Category: End User Computing
- Last Updated: 2026-09-22

## Problem Description

Endpoint laptops running low on primary storage capacity (below 10% or under 10 GB free), leading to degraded performance, failed system updates, and crashing applications.

## Symptoms

- Operating system displays "Low disk space" warning banner.
- Visual Studio Code or development tools crash with write errors.
- Windows updates or security patch installations fail with error code 0x80070070.

## Preconditions

- Standard corporate Windows or macOS managed endpoint.
- User is logged into their local profile.

## Resolution Steps

1. Empty the operating system Recycle Bin and Trash folders.
2. Clear user temporary directories:
   - On Windows: Press Win+R, type `%TEMP%`, select all files older than 24 hours, and delete them.
   - Run the built-in Windows Storage Sense or Disk Cleanup utility (`cleanmgr.exe`).
   - Select and clean "Temporary Files", "Windows Update Cleanup", and "Thumbnails".
3. Purge developer tool and package caches:
   - Node.js npm cache: run `npm cache clean --force`.
   - Python pip cache: run `pip cache purge`.
   - Docker build cache: run `docker builder prune -f` and remove unused dangling images `docker image prune -f`.
4. Clear web browser caches (Google Chrome, Microsoft Edge) via Settings > Privacy > Clear Browsing Data (Cached images and files).
5. Move personal archival files, large video recordings, or virtual machine images to corporate Microsoft OneDrive or SharePoint cloud storage.

## Escalation Conditions

- Available free disk space remains below 5 GB after all cleanup steps.
- The user profile folder is bloated by system-level or unremovable corporate agent logs.
- Hard drive physical failure or SMART diagnostic errors reported.
- Escalate to the End User Computing support group for remote diagnostic assistance or storage drive expansion.
