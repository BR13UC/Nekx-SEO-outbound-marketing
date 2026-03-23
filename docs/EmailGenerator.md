# Nekx SEO – Gemini AI Email Generator

## 1. File Architecture

The project is structured around three main files.

### `gemini_service.py`
Contains the `GeminiEmailGenerator` class. This is where all the generation logic lives: connection to the Gemini API, prompt construction, and response parsing.  
This is the only file to modify if you want to change the model, tone, or prompt structure.

### `demo_gemini.py`
Standalone demo script. It includes three fictional Dutch companies with simulated SEO issues and calls `gemini_service.py` to generate an email for each.  
This is the entry point for testing the system.

### `email_service_v2.py`
Abstraction layer that allows switching between template-based generation (default mode) and AI-based generation (Gemini).  
This file is used in the rest of the backend application.

---

## 2. Prerequisites

### Python and dependencies
Python 3.10 or higher is required.

Install the Gemini package:
```bash
pip install google-genai
```

If an older version of `google-generativeai` is already installed, remove it to avoid conflicts:
```bash
pip uninstall google-generativeai -y
```

### Google Gemini API Key
A Google API key is required. It can be obtained for free from Google AI Studio.  
Usage for this project stays within the free tier limits (10 requests per minute, 250 per day).

Before running the script, set the environment variable:
```bash
export GOOGLE_API_KEY='your-key-here'
```

The key must be linked to a Google Cloud project with billing enabled.  
Enabling billing does not mean you will be charged. Google requires a card to unlock free quotas, but normal usage of this project generates no cost.

---

## 3. How to Run the Project

Once the key is set, run the demo script at the root of the project:

```bash
#Set API key
export GOOGLE_API_KEY='your-key-here'

#Run the demo
python demo_gemini.py
```

The script will:
- Generate three personalized emails for the companies defined in `demo_gemini.py`
- Display them in the terminal
- Show a summary with the word count for each email

---

## 4. Gemini Model Used

The project currently uses:
```
gemini-2.5-flash
```

Previous versions (`gemini-1.5-flash`, `gemini-2.0-flash`) were deprecated by Google in early 2026 and are no longer available to new users.

To change the model, edit this line in `gemini_service.py` (line 25):
```python
self.model = "gemini-2.5-flash"
```

To list available models on your account:
```bash
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=$GOOGLE_API_KEY" | python3 -m json.tool | grep '"name"'
```

---

## 5. Customizing Target Companies

The three test companies are defined in `demo_gemini.py` inside the `DUTCH_COMPANIES` variable.

Each entry follows this structure:

```python
{
  "company": "Company Name",
  "website": "https://website.nl",
  "industry": "industry sector",
  "seo_issues": [
    "Detailed description of SEO issue 1",
    "Detailed description of SEO issue 2"
  ],
  "messaging_angle": "message angle (e.g., local visibility)",
  "email_format": "short"
}
```

The more specific and detailed the `seo_issues`, the more personalized and persuasive the generated email will be.

---

## 6. Gemini Prompt Parameters

The prompt is dynamically built in the `_build_prompt` method of `gemini_service.py`.

Several parameters influence the output:

| Parameter | Default Value | Role |
|----------|--------------|------|
| temperature | 0.85 | Creativity level. Higher = more varied but less predictable |
| max_output_tokens | 8192 | Maximum response length. Do not go below 2000 |
| email_format | short | Target length: short (130–160 words), medium (200–260), long (300–380) |
| top_p | 0.95 | Vocabulary diversity. Usually leave as is |
