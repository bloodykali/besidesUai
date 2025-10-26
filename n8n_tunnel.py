import os
import time
import subprocess
import requests
from pyngrok import ngrok, conf
from typing import Optional

def wait_for_n8n(timeout=60):
    """Wait for n8n server to be ready."""
    print("Waiting for n8n server to initialize...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get("http://localhost:5678/healthz")
            if response.status_code == 200:
                print("n8n server is ready!")
                return True
        except requests.exceptions.ConnectionError:
            time.sleep(2)
            print(".", end="", flush=True)
    print("\nTimeout waiting for n8n server.")
    return False

def start_n8n(webhook_url: str):
    """Start n8n as a background process on Windows."""
    try:
        env = os.environ.copy()
        env.update({
            'N8N_HOST': webhook_url.split('//')[1],
            'N8N_PROTOCOL': 'https',
            'N8N_PORT': '5678', # n8n listens on this port locally
            'WEBHOOK_URL': webhook_url,
            'DB_SQLITE_POOL_SIZE': '10',
            'N8N_RUNNERS_ENABLED': 'true',
            'N8N_BLOCK_ENV_ACCESS_IN_NODE': 'false',
            'N8N_GIT_NODE_DISABLE_BARE_REPOS': 'true',
        })
        
        print("Starting n8n server with webhook configuration...")
        # Use Popen to avoid blocking and capture output later if needed
        subprocess.Popen('n8n start', shell=True, env=env)
        
        if not wait_for_n8n():
            raise Exception("n8n server failed to start within the timeout period.")
            
    except Exception as e:
        print(f"Error starting n8n: {e}")
        raise

def setup_n8n_tunnel():
    """Set up ngrok tunnel and start n8n."""
    # Set your ngrok authtoken
    authtoken = "32eY5En0Fv3BIaD6xRYyKdSYkYP_4dZa6fv2srZEXoaF74Twa"
    ngrok.set_auth_token(authtoken)

    # Configure ngrok
    pyngrok_config = conf.PyngrokConfig(auth_token=authtoken, region='us')

    # Set your custom domain
    custom_domain = "alliteratively-semiexternal-darrin.ngrok-free.dev"
    
    tunnel: Optional[ngrok.NgrokTunnel] = None

    try:
        # Create the ngrok tunnel first to get the public URL
        print("Creating ngrok tunnel...")
        tunnel = ngrok.connect(addr="5678", domain=custom_domain, pyngrok_config=pyngrok_config)
        
        if not tunnel or not tunnel.public_url:
            raise Exception("Failed to create ngrok tunnel.")
            
        tunnel_url = tunnel.public_url
        if not tunnel_url.startswith('https://'):
            tunnel_url = tunnel_url.replace('http://', 'https://')
            
        print(f"Ngrok tunnel created at: {tunnel_url}")
        
        # Now start n8n with the public URL
        start_n8n(tunnel_url)
        
        print(f"\nYour n8n instance should be accessible at: {tunnel_url}")
        
        print("\nPress Enter to stop the server and tunnel...")
        input()
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Cleaning up...")
        try:
            ngrok.kill()
            print("ngrok tunnel stopped.")
        except Exception as e:
            print(f"Error stopping ngrok: {e}")
        
        try:
            # More robust way to kill the n8n process on Windows
            subprocess.run("taskkill /F /IM node.exe", shell=True, check=True)
            print("n8n server stopped.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Could not find or stop the n8n process. It might have already been stopped.")
        except Exception as e:
            print(f"Error stopping n8n: {e}")

if __name__ == "__main__":
    setup_n8n_tunnel()