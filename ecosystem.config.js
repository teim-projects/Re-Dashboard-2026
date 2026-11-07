module.exports = {
  apps: [{
    name: 're_dashboard',
    script: 'manage.py',
    args: 'runserver 0.0.0.0:8080',
    interpreter: './env/bin/python',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      DJANGO_SETTINGS_MODULE: 're_dashboard.settings',
      PYTHONUNBUFFERED: '1'
    }
  }]
};
