# Digital Ocean Deployment Guide

## 🚀 Complete Guide to Deploy StudyAI Django API on Digital Ocean

### Prerequisites
- Digital Ocean account
- Domain name (optional but recommended)
- GitHub repository with your code
- Basic knowledge of Linux commands

---

## Step 1: Create Digital Ocean Droplet

### 1.1 Create Droplet
```bash
# Login to Digital Ocean and create a new droplet
# Choose: Ubuntu 22.04 LTS
# Size: Basic plan - $6/month (1GB RAM, 1 CPU, 25GB SSD)
# Region: Choose closest to your users
# Add SSH keys for secure access
```

### 1.2 Connect to Droplet
```bash
ssh root@YOUR_DROPLET_IP
```

---

## Step 2: Initial Server Setup

### 2.1 Update System
```bash
apt update && apt upgrade -y
```

### 2.2 Create Non-Root User
```bash
adduser studyai
usermod -aG sudo studyai
```

### 2.3 Setup SSH for New User
```bash
rsync --archive --chown=studyai:studyai ~/.ssh /home/studyai
```

### 2.4 Switch to New User
```bash
su - studyai
```

---

## Step 3: Install Required Software

### 3.1 Install Python and Dependencies
```bash
sudo apt install python3 python3-pip python3-venv python3-dev -y
sudo apt install postgresql postgresql-contrib nginx curl git -y
```

### 3.2 Install Node.js (for frontend)
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

---

## Step 4: Setup PostgreSQL Database

### 4.1 Create Database and User
```bash
sudo -u postgres psql

# Inside PostgreSQL prompt:
CREATE DATABASE study_api;
CREATE USER study_user WITH PASSWORD 'your_secure_password';
ALTER ROLE study_user SET client_encoding TO 'utf8';
ALTER ROLE study_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE study_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE study_api TO study_user;
\q
```

---

## Step 5: Clone and Setup Application

### 5.1 Clone Repository
```bash
cd /home/studyai
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO/study-api
```

### 5.2 Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 5.3 Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 5.4 Create Environment File
```bash
nano .env
```

Add the following content:
```env
SECRET_KEY=your_super_secret_key_here_make_it_long_and_random
DEBUG=False
DOMAIN_NAME=your-domain.com
SERVER_IP=YOUR_DROPLET_IP

# Database
DB_NAME=study_api
DB_USER=study_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Email (optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
ADMIN_EMAIL=admin@your-domain.com
```

### 5.5 Setup Django
```bash
# Set environment variable
export DJANGO_SETTINGS_MODULE=config.production_settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Create log directory
sudo mkdir -p /var/log/django
sudo chown studyai:studyai /var/log/django
```

---

## Step 6: Configure Gunicorn

### 6.1 Test Gunicorn
```bash
gunicorn --bind 0.0.0.0:8000 config.wsgi:application
# Press Ctrl+C to stop
```

### 6.2 Create Gunicorn Socket File
```bash
sudo nano /etc/systemd/system/gunicorn.socket
```

Add:
```ini
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock

[Install]
WantedBy=sockets.target
```

### 6.3 Create Gunicorn Service File
```bash
sudo nano /etc/systemd/system/gunicorn.service
```

Add:
```ini
[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target

[Service]
User=studyai
Group=www-data
WorkingDirectory=/home/studyai/YOUR_REPO/study-api
Environment="DJANGO_SETTINGS_MODULE=config.production_settings"
ExecStart=/home/studyai/YOUR_REPO/study-api/venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/run/gunicorn.sock \
          config.wsgi:application

[Install]
WantedBy=multi-user.target
```

### 6.4 Start and Enable Gunicorn
```bash
sudo systemctl start gunicorn.socket
sudo systemctl enable gunicorn.socket
sudo systemctl status gunicorn.socket
```

---

## Step 7: Configure Nginx

### 7.1 Create Nginx Configuration
```bash
sudo nano /etc/nginx/sites-available/studyai
```

Add:
```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /home/studyai/YOUR_REPO/study-api;
    }
    
    location /media/ {
        root /home/studyai/YOUR_REPO/study-api;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeout for AI processing
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
}
```

### 7.2 Enable Nginx Site
```bash
sudo ln -s /etc/nginx/sites-available/studyai /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

### 7.3 Configure Firewall
```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh
sudo ufw enable
```

---

## Step 8: Setup SSL (Optional but Recommended)

### 8.1 Install Certbot
```bash
sudo apt install certbot python3-certbot-nginx -y
```

### 8.2 Get SSL Certificate
```bash
sudo certbot --nginx -d your-domain.com
```

---

## Step 9: Deploy Frontend (React)

### 9.1 Build Frontend
```bash
cd /home/studyai/YOUR_REPO/sui-fe
npm install
npm run build
```

### 9.2 Configure Nginx for Frontend
```bash
sudo nano /etc/nginx/sites-available/studyai-frontend
```

Add:
```nginx
server {
    listen 80;
    server_name frontend.your-domain.com;

    root /home/studyai/YOUR_REPO/sui-fe/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 9.3 Enable Frontend Site
```bash
sudo ln -s /etc/nginx/sites-available/studyai-frontend /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl reload nginx
```

---

## Step 10: Maintenance Scripts

### 10.1 Create Deployment Script
```bash
nano /home/studyai/deploy.sh
```

Add:
```bash
#!/bin/bash
cd /home/studyai/YOUR_REPO

# Pull latest code
git pull origin main

# Backend
cd study-api
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput

# Restart services
sudo systemctl restart gunicorn
sudo systemctl reload nginx

# Frontend
cd ../sui-fe
npm install
npm run build

echo "Deployment completed successfully!"
```

### 10.2 Make Script Executable
```bash
chmod +x /home/studyai/deploy.sh
```

---

## Step 11: Monitoring and Logs

### 11.1 Check Service Status
```bash
# Check Gunicorn
sudo systemctl status gunicorn

# Check Nginx
sudo systemctl status nginx

# Check logs
sudo journalctl -u gunicorn
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/django/django.log
```

### 11.2 Setup Log Rotation
```bash
sudo nano /etc/logrotate.d/django
```

Add:
```
/var/log/django/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 studyai studyai
}
```

---

## 📋 Quick Commands Reference

### Restart Services
```bash
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```

### View Logs
```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
sudo journalctl -u gunicorn -f
```

### Deploy Updates
```bash
./deploy.sh
```

---

## 🔒 Security Checklist

- ✅ Firewall configured (UFW)
- ✅ Non-root user created
- ✅ SSH key authentication
- ✅ SSL certificate installed
- ✅ Environment variables secured
- ✅ Database secured with strong password
- ✅ Debug mode disabled in production

---

## 🌐 Accessing Your Application

- **API**: `https://your-domain.com/api/`
- **Admin**: `https://your-domain.com/admin/`
- **Frontend**: `https://frontend.your-domain.com/`
- **API Docs**: `https://your-domain.com/swagger/`

---

## 🔧 Troubleshooting

### Common Issues:

1. **502 Bad Gateway**
   ```bash
   sudo systemctl status gunicorn
   sudo journalctl -u gunicorn
   ```

2. **Static Files Not Loading**
   ```bash
   python manage.py collectstatic --noinput
   sudo systemctl restart nginx
   ```

3. **Database Connection Error**
   ```bash
   sudo -u postgres psql
   \l  # List databases
   \du # List users
   ```

4. **Permission Errors**
   ```bash
   sudo chown -R studyai:www-data /home/studyai/YOUR_REPO/
   sudo chmod -R 755 /home/studyai/YOUR_REPO/
   ```

---

**Your StudyAI API is now live on Digital Ocean! 🎉** 