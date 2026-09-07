"""Train TF-IDF + Logistic Regression role classifier into backend/models/."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.role_classifier import train_and_save

if __name__ == "__main__":
    info = train_and_save()
    print("Role prediction model trained and saved!")
    print(f"   Algorithm : {info['algorithm']}")
    print(f"   Samples   : {info['samples']}")
    print(f"   Classes   : {', '.join(str(c) for c in info['classes'])}")
    print(f"   Model     : {info['model_path']}")
    print(f"   Vectorizer: {info['vectorizer_path']}")
