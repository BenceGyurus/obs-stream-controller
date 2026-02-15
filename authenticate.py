#!/usr/bin/env python3
"""
Standalone authentication script for OBS Stream Control.

This script should be run ONCE on a machine with a browser (your laptop, desktop, etc.)
to generate the token.json file. Then copy token.json to your Synology NAS.

Usage:
    python3 authenticate.py

Requirements:
    pip install google-auth-oauthlib
"""

import os
import sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# YouTube OAuth2 Scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

def main():
    print("=" * 70)
    print("OBS Stream Control - YouTube OAuth2 Authentication")
    print("=" * 70)
    print()
    
    client_secret_file = 'client_secret.json'
    token_file = 'token.json'
    
    # Check if client_secret.json exists
    if not Path(client_secret_file).exists():
        print("ERROR: client_secret.json not found!")
        print()
        print("Please download client_secret.json from Google Cloud Console:")
        print("1. Go to https://console.cloud.google.com/apis/credentials")
        print("2. Create OAuth 2.0 Client ID (Desktop app)")
        print("3. Download the JSON file and rename it to client_secret.json")
        print("4. Place it in the same directory as this script")
        print()
        sys.exit(1)
    
    creds = None
    
    # Load existing credentials if available
    if Path(token_file).exists():
        print(f"Found existing {token_file}")
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            print("Loaded existing credentials successfully!")
        except Exception as e:
            print(f"Warning: Failed to load existing credentials: {e}")
            creds = None
    
    # If credentials don't exist or are invalid, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing expired credentials...")
                creds.refresh(Request())
                print("Credentials refreshed successfully!")
            except Exception as e:
                print(f"Failed to refresh credentials: {e}")
                creds = None
        
        if not creds:
            print()
            print("Starting OAuth2 authentication flow...")
            print()
            
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
            
            # Try browser-based authentication first
            try:
                print("Opening browser for authentication...")
                print("If a browser doesn't open automatically, use the manual method below.")
                print()
                creds = flow.run_local_server(host='localhost', port=8080, open_browser=True)
            except Exception as e:
                print(f"Browser-based authentication failed: {e}")
                print()
                print("=" * 70)
                print("MANUAL AUTHENTICATION MODE")
                print("=" * 70)
                print()
                
                # Generate authorization URL
                auth_url, _ = flow.authorization_url(prompt='consent')
                
                print("Please complete the following steps:")
                print()
                print("1. Open this URL in your browser:")
                print()
                print(f"   {auth_url}")
                print()
                print("2. After authorizing, you'll be redirected to a URL like:")
                print("   http://localhost:8080/?code=AUTHORIZATION_CODE&scope=...")
                print()
                print("3. Copy the ENTIRE redirect URL and paste it below:")
                print()
                
                # Get the authorization response from user
                redirect_response = input("Paste the full redirect URL here: ").strip()
                
                # Exchange authorization code for credentials
                flow.fetch_token(authorization_response=redirect_response)
                creds = flow.credentials
        
        # Save credentials
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        print()
        print(f"✓ Credentials saved to {token_file}")
    else:
        print("✓ Existing credentials are still valid!")
    
    print()
    print("=" * 70)
    print("AUTHENTICATION SUCCESSFUL!")
    print("=" * 70)
    print()
    print("Next steps for Synology NAS users:")
    print()
    print(f"1. Copy {token_file} to your Synology NAS")
    print("2. Place it in the same directory as docker-compose.yml")
    print("3. Update docker-compose.yml to mount it:")
    print("   volumes:")
    print("     - ./token.json:/app/token.json:ro")
    print()
    print("Next steps for Docker users:")
    print()
    print(f"1. Ensure {token_file} is in the same directory as docker-compose.yml")
    print("2. It will be automatically mounted to the container")
    print()
    print("The token will be automatically refreshed when needed.")
    print()

if __name__ == '__main__':
    main()
