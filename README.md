# Obligation Extractor

A full-stack application for extracting and analyzing obligations from legal documents using advanced NLP techniques.

## Overview

The Obligation Extractor is a complete system designed to automatically identify, extract, and analyze obligations from legal documents including contracts, agreements, and policy documents. The system uses a hybrid approach combining spaCy-based natural language processing for initial segmentation and OpenAI LLM integration for advanced document analysis, with intelligent pre-filtering to reduce processing costs while maintaining high accuracy.

## Architecture

This is a full-stack application consisting of:

- **Backend**: FastAPI-based REST API with NLP-powered document processing
- **Frontend**: Next.js 15 web application with React 19 and TypeScript
- **Processing Pipeline**: Multi-stage document analysis with intelligent pre-filtering

## Key Features

### Document Processing
- **Multi-format Support**: Process PDF, DOCX, and plain text files
- **Intelligent Segmentation**: NLP-based legal document segmentation using spaCy
- **Pre-filtering System**: Cost-effective clause filtering to identify obligation candidates before expensive LLM processing
- **Entity Extraction**: Automatic identification of parties, dates, monetary amounts, and legal entities
- **Pattern Recognition**: Detection of legal patterns including obligations, prohibitions, and definitions

### API Endpoints
- **POST /extract**: Extract obligations from uploaded files or text input with pre-filtering
- **POST /ingest**: Ingest and segment documents without obligation filtering
- **GET /ping**: Health check endpoint

### Web Interface
- **Modern UI**: Built with Next.js 15, React 19, and Tailwind CSS
- **Document Upload**: Drag-and-drop file upload or direct text input
- **Results Visualization**: Display of extracted clauses, statistics, and metadata
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## Technology Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **spaCy**: Advanced NLP library for legal document processing
- **OpenAI API**: Large Language Model integration for advanced document analysis
- **python-docx**: DOCX file parsing
- **Uvicorn**: ASGI server for FastAPI
- **Pydantic**: Data validation and settings management

### Frontend
- **Next.js 15**: React framework with App Router
- **React 19**: Latest React features
- **TypeScript**: Type-safe development
- **Tailwind CSS 4**: Modern utility-first CSS framework

### Testing
- **pytest**: Comprehensive test suite
- **pytest-asyncio**: Async test support
- **httpx**: HTTP client for API testing

## Project Structure

The project is organized into clear backend and frontend directories:

**Backend Structure:**
- `api/routes/`: API endpoint definitions (extract, ingest, health)
- `services/`: Core processing services
  - `clause_segmenter/`: Legal document segmentation with NLP
  - `ingest/`: Document parsing and text extraction
  - `llm/`: LLM integration for advanced processing
  - `postprocess/`: Result normalization and validation
- `models/`: Data models and schemas
- `core/`: Configuration and logging
- `utils/`: Utility functions
- `tests/`: Comprehensive test suite

**Frontend Structure:**
- `src/app/`: Next.js App Router pages
  - `page.tsx`: Home page with feature overview
  - `upload/page.tsx`: Document upload and processing interface
- `public/`: Static assets

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Node.js 18 or higher
- npm or yarn package manager
- spaCy English model (automatically downloaded on first run)
- OpenAI API key (required for LLM features)

### Backend Setup

1. Navigate to the backend directory
2. Create a virtual environment
3. Activate the virtual environment
4. Install Python dependencies from requirements.txt
5. Download spaCy English model if not already installed
6. Create a `.env` file in the backend directory with your OpenAI API key:
   - `OPENAI_API_KEY=your_api_key_here`
   - Optionally configure: `OPENAI_MODEL`, `OPENAI_MAX_TOKENS`, `OPENAI_TEMPERATURE`, `OPENAI_TIMEOUT`
7. Start the FastAPI server using uvicorn

The backend API will be available at `http://localhost:8000` by default.

### Frontend Setup

1. Navigate to the frontend directory
2. Install Node.js dependencies using npm or yarn
3. Start the development server

The frontend application will be available at `http://localhost:3000` by default.

## How It Works

### Document Processing Pipeline

1. **Ingestion**: Documents are parsed to extract text content (PDF, DOCX, or TXT)
2. **Segmentation**: Legal document segmenter uses spaCy NLP to identify clauses, sections, and subsections
3. **NLP Analysis**: Each clause is analyzed for:
   - Named entities (parties, dates, amounts)
   - Obligation verbs (shall, must, agrees to, etc.)
   - Legal patterns (obligations, prohibitions, definitions)
   - Confidence scoring
4. **Pre-filtering**: Intelligent filtering system identifies clauses likely to contain obligations based on:
   - Presence of obligation verbs
   - Monetary amounts
   - Deadlines and timeframes
   - Section context
   - Negative signals (definitions, recitals)
5. **Optional LLM Enhancement**: Selected clauses can be processed with OpenAI LLM for:
   - Advanced section analysis
   - Key term extraction
   - Section classification
   - Enhanced metadata extraction
   - Structured text processing
6. **Results**: Filtered clauses are returned with metadata, statistics, and confidence scores

### Pre-filtering System

The pre-filtering system uses heuristic-based scoring to identify obligation candidates before expensive LLM processing. This significantly reduces costs while maintaining high accuracy. The system:

- Scores clauses based on positive signals (obligation verbs, monetary amounts, deadlines)
- Penalizes non-obligation content (definitions, recitals, short clauses)
- Provides confidence levels (high, medium, low)
- Configurable threshold for filtering decisions

### LLM Integration

The system includes comprehensive LLM integration using OpenAI's API for advanced document analysis. The LLM services provide:

**LLM Client Features:**
- OpenAI API integration with configurable models (default: gpt-4o-mini)
- JSON-structured responses for consistent data extraction
- Token management and limit checking
- Error handling with fallback mechanisms
- Connection testing capabilities

**LLM Segmentation Service:**
- Document segmentation using LLM processing
- Section-by-section analysis with context awareness
- Automatic handling of long sections (splitting when needed)
- Token-aware processing to stay within API limits
- Structured output with metadata and processing statistics

**LLM Processing Capabilities:**
- Legal document section analysis
- Key term extraction
- Section type classification
- Text cleaning and structuring
- Summary generation
- Metadata extraction (word counts, legal term detection, number detection)

**LLM Configuration:**
- Model selection (configurable via environment variables)
- Temperature control for response consistency
- Max tokens configuration
- Timeout settings
- JSON response format enforcement

The LLM integration works in conjunction with the spaCy-based segmentation, providing a two-stage approach: initial NLP segmentation followed by optional LLM enhancement for deeper analysis.

## API Usage

### Extract Endpoint

The `/extract` endpoint processes documents and returns obligation clauses with pre-filtering applied. You can submit either a file upload or text input. The response includes:

- Document metadata (filename, character count, preview)
- Filtered clauses with NLP analysis
- Processing statistics (total clauses, filtered count, filter rate, confidence distribution)

### Ingest Endpoint

The `/ingest` endpoint processes documents and returns all legal clauses without obligation filtering. Useful for document segmentation and analysis without pre-filtering.

## Testing

The project includes a comprehensive test suite covering:

- API endpoint testing
- Document parsing and ingestion
- Legal document segmentation
- Integration tests
- End-to-end workflow tests

Run tests using pytest from the backend directory.

## Configuration

The system uses environment-based configuration via a `.env` file in the backend directory. Key settings include:

**LLM Configuration:**
- `OPENAI_API_KEY`: Required OpenAI API key for LLM features
- `OPENAI_MODEL`: Model to use (default: "gpt-4o-mini")
- `OPENAI_MAX_TOKENS`: Maximum tokens per request (default: 1200)
- `OPENAI_TEMPERATURE`: Response temperature (default: 0.1)
- `OPENAI_TIMEOUT`: Request timeout in seconds (default: 30)

**Processing Configuration:**
- Pre-filter threshold (default: 0.35)
- spaCy model selection
- API CORS settings
- Logging configuration

## Features in Detail

### Legal Document Segmentation

The segmentation system identifies:
- Section headings (numbered sections like "1. INTERPRETATION")
- Subsections (numbered like "1.1", "2.1")
- Definitions (numbered like "1.1.1")
- Regular clauses with legal content

### NLP Analysis

Each clause is analyzed for:
- **Entities**: Named entities including persons, organizations, dates, monetary amounts
- **Obligation Verbs**: Legal obligation markers (shall, must, agrees to, etc.)
- **Legal Patterns**: Structured patterns for obligations, prohibitions, monetary terms, definitions
- **Confidence Scores**: Calculated based on presence of legal indicators

### Pre-filtering Intelligence

The pre-filter uses multiple signals:
- **Positive Signals**: Obligation verbs, monetary amounts, deadlines, action verbs, obligation sections
- **Negative Signals**: Definition patterns, non-obligation sections, very short clauses, numbering-only lines
- **Scoring**: Weighted scoring system with configurable threshold

## Development

### Backend Development

The backend follows FastAPI best practices with:
- Modular route organization
- Service layer separation
- Comprehensive logging
- Error handling and validation
- Type hints throughout

### Frontend Development

The frontend uses:
- Next.js App Router architecture
- TypeScript for type safety
- Tailwind CSS for styling
- Client-side form handling
- API integration with error handling

## Testing Strategy

The test suite includes:
- Unit tests for individual components
- Integration tests for API endpoints
- End-to-end tests for complete workflows
- Document parsing tests for various formats
- NLP segmentation tests
- Pre-filtering logic tests

## Future Enhancements

Potential improvements and features:
- PDF parsing implementation (currently placeholder)
- Direct LLM integration in main extraction pipeline
- Multi-language support
- Advanced obligation classification
- Export capabilities (JSON, CSV, Excel)
- Document comparison features
- Batch processing capabilities
- Real-time processing status updates
- LLM-based obligation extraction and classification

## License

This project is licensed under the MIT License.

## Acknowledgments

- **spaCy**: Advanced NLP library for document processing
- **OpenAI**: Large Language Model API for advanced document analysis
- **FastAPI**: Modern Python web framework
- **Next.js**: React framework for the frontend
- **Tailwind CSS**: Utility-first CSS framework

## Support

For questions, issues, or contributions:
- Check existing issues in the repository
- Create a new issue with detailed information
- Follow the contribution guidelines
