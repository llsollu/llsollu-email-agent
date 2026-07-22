"""SECRET_ENC_KEY 생성기. 실행: python -m app.tools.genkey"""

from app.services.crypto import generate_key

if __name__ == "__main__":
    print(generate_key())
