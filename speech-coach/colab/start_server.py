# Colab me ek naye cell me ye poora paste karke chalao.
# Pehle: Colab ke Secrets (🔑) me ASSEMBLYAI_API_KEY daalo aur "Notebook access" on karo.
import os
import re
import subprocess
import time
from google.colab import userdata

REPO = "https://github.com/YOUR_USERNAME/speech-coach.git"   # <- apna repo URL daalo

# 1) repo clone / update
if os.path.exists("speech-coach"):
    subprocess.run(["git", "-C", "speech-coach", "pull"], check=True)
else:
    subprocess.run(["git", "clone", REPO, "speech-coach"], check=True)

# 2) jo packages Colab me nahi hote sirf wahi install karo
subprocess.run(["pip", "install", "-q", "fastapi", "uvicorn", "python-multipart",
                "assemblyai", "gtts"], check=True)

# 3) purana server/tunnel band karo
subprocess.run("pkill -f uvicorn; pkill -f cloudflared", shell=True)
time.sleep(1)

# 4) server chalao
os.environ["ASSEMBLYAI_API_KEY"] = userdata.get("ASSEMBLYAI_API_KEY")
subprocess.Popen(["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"],
                 cwd="speech-coach/backend")

# 5) public link (cloudflared)
if not os.path.exists("cloudflared"):
    subprocess.run(["wget", "-q",
                    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
                    "-O", "cloudflared"], check=True)
    subprocess.run(["chmod", "+x", "cloudflared"], check=True)
subprocess.Popen("./cloudflared tunnel --url http://localhost:8000 > tunnel.log 2>&1", shell=True)

url = None
for _ in range(40):
    time.sleep(1)
    m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", open("tunnel.log").read())
    if m:
        url = m.group(0)
        break
print("✅ Ye URL frontend ke sidebar me daalo:", url)
