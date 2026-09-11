# Wagtail Headless Blog Platform

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Django](https://img.shields.io/badge/Django-4.2%2B-green)
![Wagtail](https://img.shields.io/badge/Wagtail-5.2%2B-darkgreen)
![REST%20API](https://img.shields.io/badge/DRF-REST%20API-red)
![AWS%20S3](https://img.shields.io/badge/AWS-S3%20Storage-orange)
![Docker](https://img.shields.io/badge/Docker-Supported-blue)

A high-performance, headless Content Management System (CMS) built with **Wagtail**, **Django**, and **Django REST Framework (DRF)**. Designed for modern web and mobile frontends (React, Next.js, Vue, Nuxt, Flutter, iOS, Android), featuring real-time automated SEO & Readability scoring, threaded commenting workflows, device-based post likes, author profile management, and cloud media storage.

---

## 🌟 Key Features

* **🎨 Dynamic Content Builder (StreamField Blocks)**
  * Compose rich articles using modular blocks: Headings (`H1`-`H6`), RichText Paragraphs, Code Blocks with syntax highlighting (Python, JS, HTML, CSS, JSON, Shell, SQL), Callout Alert Boxes (Info, Success, Warning, Danger), Images with Alt text & Captions, Structured Data Tables, Bulleted/Numbered Lists, Media Embeds (YouTube, Vimeo, Twitter/X), Blockquotes, and Dividers.

* **🏷️ Categories, Subcategories & Page Hierarchy**
  * Two-tier taxonomy with auto-synchronization (selecting a subcategory links its parent category).
  * Supports parent-child article page trees for multi-part tutorial series.

* **⚡ Real-time Automated SEO Engine (25+ Checks)**
  * Evaluates keyphrase optimization in titles, slugs, meta descriptions, image alt text, introductions, and headings.
  * Calculates keyphrase density, validates word counts (≥ 300 words), SEO title length (40–60 chars), meta description length (120–160 chars), single H1 tag rules, duplicate keyphrase detection, custom canonical URLs, cornerstone flagging, and meta robots indexing/following.

* **📖 Automated Readability Analysis**
  * Calculates **Flesch Reading Ease** scores.
  * Evaluates transition words ratio (≥ 30%), passive voice usage (≤ 10%), sentence length distribution, paragraph word count limits (≤ 150 words), and subheading distribution across long text blocks.

* **🌐 Social Media & Schema.org JSON-LD**
  * Custom OpenGraph and Twitter card metadata (title, description, image).
  * Automatically generates structured `BlogPosting` JSON-LD schema for Google search engine rich results.

* **💬 Threaded Commenting System with Moderation**
  * Public comment and reply submission.
  * Admin moderation workflow (`Pending`, `Approved`, `Rejected`) managed via Wagtail Admin Snippets.

* **❤️ Anonymous / Device-Based Like Toggle**
  * Instant like/unlike toggle per client device identifier (`device_id`).
  * Real-time like counts and status checking without requiring user login.

* **👤 Author Profiles & AWS S3 Integration**
  * User profile snippet with biography and profile photo upload.
  * Automatic direct upload of profile media to AWS S3 when configured, with seamless fallback to local media storage.

* **🔍 RESTful Headless API & Draft Preview**
  * Full DRF API suite with pagination, searching, category/subcategory/author filtering.
  * Native support for headless live draft previews using tokenized preview URLs.

---

## 📁 Repository Structure

```text
Wagtail/
├── blog/                      # Main Blog application
│   ├── blocks.py              # StreamField block definitions (Code, Callout, Heading, etc.)
│   ├── models.py              # BlogPage, BlogCategory, BlogSubCategory, BlogComment, BlogLike
│   ├── seo_analyzer.py        # Real-time SEO & Readability analysis engine
│   ├── serializers.py        # DRF serializers for pages, snippets & StreamField
│   ├── views.py               # REST API endpoints & Preview view
│   └── urls.py                # API route definitions
├── core/                      # Core application
│   ├── models.py              # UserProfile model with AWS S3 auto-upload signal
│   ├── pagination.py          # Standard pagination setup
│   └── responses.py           # Standardized API response formatters
├── home/                      # Wagtail home page app
├── search/                    # Search app setup
├── wagtail_blog/              # Project settings & URL routing
│   ├── settings/              # Environment configurations (dev, base, production)
│   └── urls.py                # Root URL dispatcher
├── Dockerfile                 # Containerization setup
├── manage.py                  # Django management script
├── requirements.txt           # Python dependencies
├── DOCUMENTATION.md           # Full feature & API documentation guide
└── README.md                  # Project README
```

---

## 🚀 Quick Start & Installation

### Prerequisites
* Python 3.10+
* Virtual environment (`venv`)
* Pip package manager

### 1. Clone the Repository & Set Up Virtual Environment

```bash
# Clone the repository
git clone https://github.com/vrajmakwana-create/wagtail.git
cd wagtail

# Create and activate virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the root directory (or copy from `.env.example`):

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=*

# Optional: AWS S3 Configuration
USE_S3=False
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_REGION_NAME=us-east-1
```

### 4. Database Setup & Migrations

```bash
# Run database migrations
python manage.py migrate

# Create Wagtail Admin Superuser
python manage.py createsuperuser
```

### 5. Run Development Server

```bash
python manage.py runserver
```

* **Wagtail Admin Dashboard**: Visit `http://127.0.0.1:8000/admin/`
* **REST API Base URL**: `http://127.0.0.1:8000/api/v1/`

---

## 📡 REST API Reference

| Endpoint | Method | Description | Key Query Parameters |
| :--- | :--- | :--- | :--- |
| `/api/v1/blogs/` | `GET` | List published blog posts | `page`, `category`, `subcategory`, `search`, `author` |
| `/api/v1/blogs/<slug>/` | `GET` | Single blog details with body, SEO & readability reports | `device_id` |
| `/api/v1/blogs/preview/` | `GET` | Fetch live draft preview for headless frontends | `token`, `content_type` |
| `/api/v1/blogs/categories/` | `GET` | List categories with subcategories | None |
| `/api/v1/blogs/subcategories/` | `GET` | List subcategories | `category` (slug or ID) |
| `/api/v1/blogs/author/<user_id>/` | `GET` | List blogs written by author | `page`, `page_size` |
| `/api/v1/blogs/<slug>/comments/` | `GET` | Get approved comments & replies | `page`, `page_size` |
| `/api/v1/blogs/<slug>/comments/` | `POST` | Submit comment or nested reply | Payload: `name`, `email`, `message`, `parent` |
| `/api/v1/blogs/<slug>/like/` | `POST` | Toggle post like status | Payload: `device_id` |

*For detailed API request/response samples and full integration instructions, see [`DOCUMENTATION.md`](DOCUMENTATION.md).*

---

## 🐳 Running with Docker

Build and run the application in a Docker container:

```bash
# Build the Docker image
docker build -t wagtail-headless-blog .

# Run the container
docker run -p 8000:8000 --env-file .env wagtail-headless-blog
```

---

## 📚 Detailed Feature Documentation

For step-by-step instructions on using every feature in Wagtail Admin, managing comments, using the SEO analyzer, setting up S3, and integrating headless previews, refer to the full guide:

➡️ **[Full Feature & User Documentation (DOCUMENTATION.md)](DOCUMENTATION.md)**

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
