from typing import List

# Simple curated fallback bank; extend as needed
BANK = {
    "python": [
        "Explain list vs tuple and when to use each.",
        "What are list comprehensions and why are they useful?",
        "How does Python's GIL affect multithreading?",
        "What is a generator? Show a simple example.",
        "Explain context managers and the 'with' statement."
    ],
    "django": [
        "What are Django models and migrations?",
        "Explain Django's MVT architecture.",
        "How do you optimize ORM queries in Django?",
        "What is middleware and a use case for custom middleware?",
        "How would you implement authentication in Django?"
    ],
    "flask": [
        "How do blueprints help structure a Flask app?",
        "What is the difference between app.run debug and production WSGI servers?",
        "Explain request context and application context in Flask.",
        "How do you handle configuration and secrets in Flask?",
        "How would you add authentication/authorization in Flask?"
    ],
    "sql": [
        "Explain INNER JOIN vs LEFT JOIN with a simple example.",
        "What are indexes and how can they speed up queries?",
        "How do you find slow queries and optimize them?",
        "Explain ACID properties in relational databases.",
        "What is normalization and when would you denormalize?"
    ],
    "pandas": [
        "How do you handle missing values in pandas DataFrames?",
        "Explain vectorization and why it's faster than loops in pandas.",
        "How do you merge/join DataFrames and when to use each?",
        "What is groupby and an example use case?",
        "How do you optimize memory usage in pandas?"
    ],
    "numpy": [
        "Explain broadcasting in NumPy with an example.",
        "How do you create views vs copies and why does it matter?",
        "What is vectorization and why is it useful in NumPy?",
        "How do you compute the dot product and matrix multiplication?",
        "How to efficiently filter arrays by conditions?"
    ],
    "pytorch": [
        "Explain autograd and computational graphs in PyTorch.",
        "What is the difference between Module and Tensor?",
        "How do you prevent overfitting in a PyTorch model?",
        "How do you move tensors between CPU and GPU?",
        "What is DataLoader and why is it useful?"
    ],
    "tensorflow": [
        "What are eager execution and graph execution in TensorFlow?",
        "How do you save and load a trained model?",
        "How do you implement early stopping?",
        "What is tf.data and why is it useful?",
        "Explain difference between Keras Sequential and Functional API."
    ],
    "ml": [
        "Explain bias-variance tradeoff with an example.",
        "How do you choose between classification and regression models?",
        "What is cross-validation and why is it important?",
        "Explain precision, recall, and F1-score.",
        "How do you handle class imbalance?"
    ],
    "javascript": [
        "Explain var vs let vs const.",
        "What are closures and a practical example?",
        "How does the event loop work in JS?",
        "Explain promise vs async/await.",
        "What is debounce vs throttle and a use case for each?"
    ],
    "react": [
        "Explain state vs props.",
        "What are hooks and why use useEffect?",
        "How do you optimize performance in React apps?",
        "What is reconciliation and keys in lists?",
        "How do you manage global state?"
    ]
}

def generate_fallback_questions(tech_stack: str, max_questions: int = 5) -> List[str]:
    techs = [t.strip().lower() for t in tech_stack.split(",")]
    seen = set()
    out: List[str] = []
    for t in techs:
        for key in BANK.keys():
            if key in t and key not in seen:
                out.extend(BANK[key][:max_questions])
                seen.add(key)
                break
        if len(out) >= max_questions:
            break
    if not out:
        out = [
            "Explain a challenging problem you solved with your preferred technology.",
            "How do you test and debug your code effectively?",
            "Describe a time you optimized performance in an application.",
            "How do you ensure code quality and readability?",
            "What best practices do you follow in your projects?"
        ]
    return out[:max_questions]
