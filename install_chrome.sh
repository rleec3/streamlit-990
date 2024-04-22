
#!/bin/bash

# Update the apt package index
sudo apt-get update

# Install necessary packages for adding the Google Chrome repository
sudo apt-get install -y wget gnupg

# Download the Google Chrome stable package
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

# Install Google Chrome
sudo dpkg -i google-chrome-stable_current_amd64.deb

# Fix any broken dependencies
sudo apt-get install -f

# Cleaning up the downloaded package
rm google-chrome-stable_current_amd64.deb
