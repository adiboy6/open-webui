#!/bin/bash
# Enable required Apache modules for WebSocket support

sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod proxy_wstunnel
sudo a2enmod rewrite
sudo a2enmod headers

# Restart Apache to apply changes
sudo systemctl restart apache2

# Check if modules are loaded
apache2ctl -M | grep -E "(proxy|rewrite|headers)"
