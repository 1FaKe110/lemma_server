import os
import re
from src.config import Config

additional = """
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
"""


# Открываем файл app.py и читаем содержимое
with open('src/main.py', 'r') as file:
    content = file.read()

# Ищем все декораторы @app.route
routes = re.findall(r"@app.route\(['\"](.*?)['\"].*?\)", content)


# Генерируем конфигурацию для Nginx
nginx_config = "server {\n"
nginx_config += "    listen 80;\n"
nginx_config += f"    server_name 147.45.246.25;\n\n"

for route in routes:
    location = route if '<' not in route else re.sub(r'/<.*?>', r'/*', route)
    nginx_config += f"    location {location} {{\n"
    nginx_config += (f"        proxy_pass http://{Config.Nginx.docker_ip}:{Config.Nginx.port}"
                     + re.sub(r'<\w+>', '*', route) + ";")
    nginx_config += additional
    nginx_config += "    }\n"

nginx_config += "}\n"

print(nginx_config)
with open('/etc/nginx/sites-enabled/chgk', 'w', encoding='utf-8') as f:
    f.write(nginx_config)

print(os.popen('nginx -t').read())
