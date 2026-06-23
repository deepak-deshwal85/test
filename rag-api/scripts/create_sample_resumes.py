"""Create sample resume PDFs for local RAG development."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fpdf import FPDF

from paths import KNOWLEDGE_BASE_DIR

RESUMES = {
    "resume_1.pdf": {
        "name": "Alice Johnson",
        "title": "Senior Software Engineer",
        "summary": (
            "Alice Johnson is a senior software engineer with eight years of experience "
            "building backend services, APIs, and cloud-native applications."
        ),
        "skills": "Python, FastAPI, PostgreSQL, AWS, Docker, Kubernetes, system design",
        "experience": (
            "Led a team that migrated a monolith to microservices at Northwind Labs. "
            "Built appointment scheduling APIs used by healthcare clinics. "
            "Improved API latency by forty percent through caching and query optimization."
        ),
        "education": "B.S. Computer Science, State University",
        "availability": "Available for in-person or remote interviews on weekdays after 2 PM Eastern.",
    },
    "resume_2.pdf": {
        "name": "Bob Smith",
        "title": "Lead Data Scientist",
        "summary": (
            "Bob Smith is a lead data scientist focused on machine learning, analytics, "
            "and production ML systems for customer support and voice products."
        ),
        "skills": "Python, PyTorch, scikit-learn, SQL, RAG pipelines, vector search, MLOps",
        "experience": (
            "Built retrieval-augmented generation systems for enterprise support bots. "
            "Deployed ranking models that reduced escalations by twenty-five percent. "
            "Mentored analysts on experiment design and model monitoring."
        ),
        "education": "M.S. Data Science, Riverdale Institute of Technology",
        "availability": "Prefers video interviews and is generally available Tuesday through Thursday mornings.",
    },
}


def _write_resume_pdf(path: Path, content: dict[str, str]) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, content["name"], ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, content["title"], ln=True)
    pdf.ln(4)

    for heading, body in (
        ("Professional Summary", content["summary"]),
        ("Core Skills", content["skills"]),
        ("Experience", content["experience"]),
        ("Education", content["education"]),
        ("Interview Availability", content["availability"]),
    ):
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, heading, ln=True)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, body)
        pdf.ln(2)

    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))


def main() -> None:
    for filename, content in RESUMES.items():
        output_path = KNOWLEDGE_BASE_DIR / filename
        _write_resume_pdf(output_path, content)
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
