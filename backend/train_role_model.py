import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# Simple training dataset (you can expand this)
training_data = [
    # ML Engineer
    ("python machine learning deep learning tensorflow pytorch ai data", "Machine Learning Engineer"),
    ("neural networks nlp computer vision python ai models", "Machine Learning Engineer"),

    # Data Analyst
    ("excel sql data analysis power bi tableau statistics pandas", "Data Analyst"),
    ("business intelligence dashboards sql reporting analytics", "Data Analyst"),

    # Full Stack
    ("html css javascript react node mongodb full stack web", "Full Stack Developer"),
    ("frontend backend api react express database", "Full Stack Developer"),

    # DevOps
    ("docker kubernetes aws ci cd linux devops automation", "DevOps Engineer"),
    ("cloud deployment terraform aws pipeline monitoring", "DevOps Engineer"),
]

texts = [x[0] for x in training_data]
labels = [x[1] for x in training_data]

vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(texts)

model = LogisticRegression()
model.fit(X, labels)

# Save model and vectorizer
joblib.dump(model, "role_model.pkl")
joblib.dump(vectorizer, "role_vectorizer.pkl")

print("✅ Role prediction model trained and saved!")
