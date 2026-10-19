# How to Run the PDF LLM Analyzer

This document provides direct instructions for setting up, running, and using this lightweight PDF document analysis application.

---

## 1. Prerequisites

Ensure you have Python 3.8 or higher installed on your system. You will also need a command prompt or terminal window.

---

## 2. Installation

Open your terminal, navigate to this project directory, and install the required dependencies:

```bash
pip install -r requirements.txt
```

This will install the following packages:
- `flask`: The web framework running the server.
- `google-generativeai`: The official Google SDK for the Gemma 4 LLM integration.
- `pypdf`: The local library used to instantly parse PDF text contents.

---

## 3. Configuration

The Gemini API key is already configured inside `app.py`. If you need to change the API key in the future, open `app.py` and replace the string value on this line:

```python
API_KEY = "AIzaSyAdzP9nGj-gfIWgLEJamwHBV48u6g99FqY"
```

---

## 4. Running the Application

To start the Flask development server, execute the following command in your terminal:

```bash
python app.py
```

Once running, open your web browser and navigate to:
```
http://127.0.0.1:5000
```


   ```
