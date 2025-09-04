# Obligation Extractor

A tool for extracting and analyzing obligations from text documents and contracts.

## Overview

The Obligation Extractor is designed to automatically identify, extract, and categorize obligations from various types of documents including contracts, legal agreements, and policy documents. It uses natural language processing and machine learning techniques to accurately identify obligation-related content.

## Features

- **Text Processing**: Extract obligations from plain text, PDF, and document files
- **Obligation Classification**: Categorize obligations by type (e.g., payment, delivery, compliance)
- **Entity Recognition**: Identify parties, dates, and key terms in obligations
- **Export Capabilities**: Export extracted obligations in various formats (JSON, CSV, Excel)
- **API Integration**: RESTful API for programmatic access
- **Web Interface**: User-friendly web interface for document upload and analysis

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/obligation-extractor.git
cd obligation-extractor
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Usage

#### Command Line Interface

```bash
# Extract obligations from a text file
python extractor.py --input document.txt --output obligations.json

# Extract from multiple files
python extractor.py --input-dir ./documents --output-dir ./results

# Use specific extraction model
python extractor.py --input document.txt --model legal --output obligations.json
```

#### Python API

```python
from obligation_extractor import ObligationExtractor

# Initialize extractor
extractor = ObligationExtractor()

# Extract obligations from text
text = "The supplier shall deliver the goods within 30 days."
obligations = extractor.extract(text)

# Process results
for obligation in obligations:
    print(f"Type: {obligation.type}")
    print(f"Subject: {obligation.subject}")
    print(f"Deadline: {obligation.deadline}")
```

#### Web Interface

1. Start the web server:
```bash
python app.py
```

2. Open your browser and navigate to `http://localhost:5000`
3. Upload your document and view extracted obligations

## Configuration

Create a `config.yaml` file to customize extraction settings:

```yaml
models:
  default: "general"
  legal: "legal_specialized"
  
extraction:
  confidence_threshold: 0.8
  max_obligations: 100
  
output:
  format: "json"
  include_metadata: true
```

## API Reference

### REST API Endpoints

- `POST /api/extract` - Extract obligations from uploaded text
- `GET /api/models` - List available extraction models
- `GET /api/health` - Health check endpoint

### Request Format

```json
{
  "text": "Document text content",
  "model": "general",
  "options": {
    "confidence_threshold": 0.8,
    "include_metadata": true
  }
}
```

## Project Structure

```
obligation-extractor/
├── src/
│   ├── extractor/          # Core extraction logic
│   ├── models/             # ML models and training
│   ├── utils/              # Utility functions
│   └── api/                # API endpoints
├── tests/                  # Test files
├── data/                   # Training and test data
├── docs/                   # Documentation
├── requirements.txt        # Python dependencies
├── config.yaml            # Configuration file
└── README.md              # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Testing

Run the test suite:

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src

# Run specific test file
python -m pytest tests/test_extractor.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [spaCy](https://spacy.io/) for NLP processing
- Uses [Transformers](https://huggingface.co/transformers/) for advanced text analysis
- Web interface powered by [Flask](https://flask.palletsprojects.com/)

## Support

For questions, issues, or feature requests, please:

1. Check the [Issues](https://github.com/yourusername/obligation-extractor/issues) page
2. Create a new issue with detailed description
3. Contact the maintainers at support@obligation-extractor.com

## Roadmap

- [ ] Support for more document formats (Word, RTF)
- [ ] Multi-language support
- [ ] Advanced obligation clustering
- [ ] Real-time collaboration features
- [ ] Integration with document management systems
