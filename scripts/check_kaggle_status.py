"""
Script de monitoramento de status do Kernel Ozz no Kaggle
"""
import os
import sys
import subprocess

if sys.platform == "win32" and not getattr(sys.flags, "utf8_mode", False):
    cmd = [sys.executable, "-X", "utf8"] + sys.argv
    result = subprocess.run(cmd)
    sys.exit(result.returncode)

def check_status():
    token = os.environ.get("KAGGLE_API_TOKEN", "KGAT_01f61b4aa10b1cfaaa2a404e2456fc0f")
    os.environ["KAGGLE_API_TOKEN"] = token
    
    try:
        import kaggle
        api = kaggle.KaggleApi()
        api.authenticate()
        
        kernel_slug = "danielapalma/ozz-halctf-v2"
        print(f"📊 Verificando status do Kernel: {kernel_slug}...")
        
        status_res = api.kernels_status_cli(kernel_slug)
        print(f"🔗 Link no Kaggle: https://www.kaggle.com/code/{kernel_slug}")
        
    except Exception as e:
        print(f"❌ Erro ao consultar status: {e}")

if __name__ == "__main__":
    check_status()
