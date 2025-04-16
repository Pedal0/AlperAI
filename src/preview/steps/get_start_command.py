"""
Détermine la commande de démarrage à utiliser selon le type de projet.
"""
import sys
import json
import subprocess
from pathlib import Path
from .detect_project_type import ProjectType
from .find_free_port import find_free_port

def get_start_command(project_dir: str, project_type: str, session_id: str = None):
    project_dir = Path(project_dir)
    env = None
    if project_type == ProjectType.FLASK:
        for file in ["app.py", "main.py", "server.py", "run.py"]:
            if (project_dir / file).exists():
                return [sys.executable, str(project_dir / file)], env
        return [sys.executable, "app.py"], env
    elif project_type == ProjectType.EXPRESS:
        if (project_dir / "package.json").exists():
            try:
                with open(project_dir / "package.json", "r", encoding="utf-8") as f:
                    package_json = json.load(f)
                    scripts = package_json.get("scripts", {})
                    if "start" in scripts:
                        return ["npm", "start"], env
                    elif "dev" in scripts:
                        return ["npm", "run", "dev"], env
            except:
                pass
        main_files = ["server.js", "app.js", "index.js"]
        for file in main_files:
            if (project_dir / file).exists():
                return ["node", str(project_dir / file)], env
        return ["npm", "start"], env
    elif project_type in [ProjectType.REACT, ProjectType.VUE, ProjectType.ANGULAR]:
        if (project_dir / "package.json").exists():
            try:
                with open(project_dir / "package.json", "r", encoding="utf-8") as f:
                    package_json = json.load(f)
                    scripts = package_json.get("scripts", {})
                    if "start" in scripts:
                        return ["npm", "start"], env
                    elif "dev" in scripts:
                        return ["npm", "run", "dev"], env
                    elif "serve" in scripts:
                        return ["npm", "run", "serve"], env
            except:
                pass
        return ["npm", "start"], env
    elif project_type == ProjectType.STATIC:
        if (project_dir / "package.json").exists():
            try:
                with open(project_dir / "package.json", "r", encoding="utf-8") as f:
                    package_json = json.load(f)
                    scripts = package_json.get("scripts", {})
                    if "start" in scripts:
                        return ["npm", "start"], env
                    elif "dev" in scripts:
                        return ["npm", "run", "dev"], env
                    elif "serve" in scripts:
                        return ["npm", "run", "serve"], env
            except:
                pass
        port = find_free_port()
        if port is None:
            port = 3000
        if session_id is not None:
            from src.preview.preview_manager import session_ports
            session_ports[session_id] = port
        try:
            subprocess.check_output(["python3", "--version"])
            python_code = (
                "import http.server, socketserver; "
                f"handler = http.server.SimpleHTTPRequestHandler; "
                f"handler.directory = r'{project_dir}'; "
                f"socketserver.TCPServer(('0.0.0.0', {port}), handler).serve_forever()"
            )
            return ["python3", "-c", python_code], env
        except (subprocess.SubprocessError, FileNotFoundError):
            try:
                subprocess.check_output(["node", "--version"], stderr=subprocess.STDOUT)
                try:
                    subprocess.check_output(["npx", "--version"], stderr=subprocess.STDOUT)
                    return ["npx", "serve", "-s", str(project_dir), "-p", str(port)], env
                except (subprocess.SubprocessError, FileNotFoundError):
                    http_server_script = f"""
const http = require('http');
const fs = require('fs');
const path = require('path');
const port = {port};
const mimeTypes = {{ '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpg', '.gif': 'image/gif', '.svg': 'image/svg+xml', '.wav': 'audio/wav', '.mp3': 'audio/mpeg', '.mp4': 'video/mp4', '.woff': 'application/font-woff', '.ttf': 'application/font-ttf', '.eot': 'application/vnd.ms-fontobject', '.otf': 'application/font-otf', '.wasm': 'application/wasm' }};
const server = http.createServer((req, res) => {{
  let url = req.url;
  const queryIndex = url.indexOf('?');
  if (queryIndex !== -1) url = url.substring(0, queryIndex);
  if (url === '/') url = '/index.html';
  const filePath = path.join(process.cwd(), url);
  fs.stat(filePath, (err, stats) => {{
    if (err) {{
      if (url !== '/index.html') {{
        fs.readFile(path.join(process.cwd(), 'index.html'), (err, data) => {{
          if (err) {{ res.writeHead(404, {{ 'Content-Type': 'text/plain' }}); res.end('404 Not Found'); return; }}
          res.writeHead(200, {{ 'Content-Type': 'text/html' }}); res.end(data); }});
        return;
      }}
      res.writeHead(404, {{ 'Content-Type': 'text/plain' }}); res.end('404 Not Found'); return;
    }}
    if (stats.isDirectory()) {{
      fs.readFile(path.join(filePath, 'index.html'), (err, data) => {{
        if (err) {{ res.writeHead(404, {{ 'Content-Type': 'text/plain' }}); res.end('404 Not Found'); return; }}
        res.writeHead(200, {{ 'Content-Type': 'text/html' }}); res.end(data); }});
      return;
    }}
    const ext = path.extname(filePath);
    const contentType = mimeTypes[ext] || 'application/octet-stream';
    fs.readFile(filePath, (err, data) => {{
      if (err) {{ res.writeHead(500, {{ 'Content-Type': 'text/plain' }}); res.end('Internal Server Error'); return; }}
      res.writeHead(200, {{ 'Content-Type': contentType }}); res.end(data); }});
  }});
}});
server.listen(port, () => {{ console.log(`Server running at http://localhost:${{port}}/`); }});
"""
                    node_script_path = project_dir / "serve_static.js"
                    with open(node_script_path, "w", encoding="utf-8") as f:
                        f.write(http_server_script)
                    return ["node", str(node_script_path)], env
            except Exception:
                return ["python3", "-m", "http.server", str(port)], env
    else:
        if (project_dir / "package.json").exists():
            try:
                with open(project_dir / "package.json", "r", encoding="utf-8") as f:
                    package_json = json.load(f)
                    scripts = package_json.get("scripts", {})
                    if "start" in scripts:
                        return ["npm", "start"], env
                    elif "dev" in scripts:
                        return ["npm", "run", "dev"], env
                    elif "serve" in scripts:
                        return ["npm", "run", "serve"], env
            except Exception:
                return ["npm", "start"], env
        main_py_files = ["app.py", "main.py", "server.py", "run.py"]
        for file in main_py_files:
            if (project_dir / file).exists():
                return [sys.executable, str(project_dir / file)], env
        main_js_files = ["server.js", "app.js", "index.js", "main.js"]
        for file in main_js_files:
            if (project_dir / file).exists():
                return ["node", str(project_dir / file)], env
        if (project_dir / "index.html").exists() or (project_dir / "public" / "index.html").exists():
            return get_start_command(project_dir, ProjectType.STATIC, session_id)
        return ["npm", "start"], env
