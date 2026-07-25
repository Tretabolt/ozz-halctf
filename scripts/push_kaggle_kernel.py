"""
Script de automação para deploy do Kernel Ozz no Kaggle (Akita Way - Portão 6)
"""
import os
import sys
import json
import subprocess

# Auto-reexec com UTF-8 no Windows para evitar o erro de decoding da biblioteca Kaggle
if sys.platform == "win32" and not getattr(sys.flags, "utf8_mode", False):
    cmd = [sys.executable, "-X", "utf8"] + sys.argv
    result = subprocess.run(cmd)
    sys.exit(result.returncode)

def push_kernel():
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    metadata_path = os.path.join(scripts_dir, "kernel-metadata.json")
    
    if not os.path.exists(metadata_path):
        print(f"❌ Erro: {metadata_path} não encontrado!")
        sys.exit(1)
        
    print("🚀 Iniciando deploy do Kernel no Kaggle...")
    print(f"📁 Pasta: {scripts_dir}")
    
    token = os.environ.get("KAGGLE_API_TOKEN", "KGAT_01f61b4aa10b1cfaaa2a404e2456fc0f")
    os.environ["KAGGLE_API_TOKEN"] = token
    
    try:
        import kaggle
        api = kaggle.KaggleApi()
        api.authenticate()
        print("✅ Autenticado na API do Kaggle!")
        
        print("📦 Enviando Kernel (ozz_kaggle.ipynb) com suporte a GPU...")
        res = api.kernels_push_cli(folder=scripts_dir, timeout=600)
        print("🎉 Deploy concluído com sucesso!")
        print("🔗 Acesse o Kernel em: https://www.kaggle.com/code/danielapalma/ozz-halctf-agent")
        
    except Exception as e:
        print(f"❌ Erro ao enviar kernel: {e}")
        sys.exit(1)

if __name__ == "__main__":
    push_kernel()
