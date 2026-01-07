#!/bin/bash
# Script to enable required Apache modules and apply WebSocket configuration

echo "Enabling required Apache modules..."
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod proxy_wstunnel
sudo a2enmod rewrite
sudo a2enmod headers

echo "Checking if modules are enabled..."
apache2ctl -M | grep -E "(proxy|rewrite|headers|wstunnel)"

echo ""
echo "Please update your Apache virtual host configuration with the new config."
echo "Then run:"
echo "sudo apache2ctl configtest"
echo "sudo systemctl reload apache2"
