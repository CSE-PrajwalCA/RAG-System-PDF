import requests
import time
import os
import sys

# Configuration
BACKEND_URL = "http://localhost:8000"
PDF_FILE_PATH = "tests/sample.pdf"  # You will need a sample PDF here

def generate_dummy_pdf(path):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="This is a test PDF for RAG system verification.", ln=1, align="C")
    pdf.cell(200, 10, txt="It contains explicit information about ShaktiDB architecture.", ln=2, align="C")
    pdf.output(path)
    print(f"Generated dummy PDF at {path}")

def test_health():
    print("Testing Health Check...")
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if resp.status_code == 200:
            print("✅ Backend is Healthy")
            return True
        else:
            print(f"❌ Backend returned {resp.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Backend. Is it running?")
        return False

def test_upload(file_path):
    print(f"Testing PDF Upload ({file_path})...")
    with open(file_path, "rb") as f:
        files = {"file": f}
        try:
            resp = requests.post(f"{BACKEND_URL}/upload-pdf", files=files, timeout=60)
            if resp.status_code == 200:
                print(f"✅ Upload Successful: {resp.json()}")
                return True
            else:
                print(f"❌ Upload Failed: {resp.text}")
                return False
        except Exception as e:
            print(f"❌ Upload Error: {e}")
            return False

def test_query(question):
    print(f"Testing Query: '{question}'...")
    try:
        resp = requests.post(f"{BACKEND_URL}/query", params={"question": question}, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Answer: {data['answer']}")
            print(f"   Sources: {len(data['sources'])} found")
            return True
        else:
            print(f"❌ Query Failed: {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Query Error: {e}")
        return False

if __name__ == "__main__":
    if not os.path.exists("tests"):
        os.makedirs("tests")
    
    # Generate a dummy PDF if it doesn't exist
    if not os.path.exists(PDF_FILE_PATH):
        try:
            generate_dummy_pdf(PDF_FILE_PATH)
        except ImportError:
            print("❗ fpdf not installed. install with 'pip install fpdf' to generate sample PDF.")
            print("❗ Skipping upload test for now unless you provide 'tests/sample.pdf'.")
            sys.exit(1)

    # Run tests
    if not test_health():
        print("Aborting tests - System not healthy.")
        sys.exit(1)

    if test_upload(PDF_FILE_PATH):
        # Wait a bit for indexing if async? currently synchronous so should be fine immediately.
        if test_query("What is this document about?"):
            print("\n🎉 All Verification Tests Passed!")
        else:
            print("\n⚠️ Query Test Failed.")
    else:
        print("\n⚠️ Upload Test Failed.")
