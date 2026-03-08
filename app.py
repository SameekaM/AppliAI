from flask import Flask, Response, render_template, request, redirect, stream_with_context, url_for, jsonify
from models import db, Job, Resume
import anthropic
import os

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tracker.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Create tables on first run
with app.app_context():
    db.create_all()
    # Add a starter resume if none exists
    if not Resume.query.first():
        starter = Resume(content="Paste your resume here...", version=1)
        db.session.add(starter)
        db.session.commit()

STAGES = ["Saved", "Applied", "Phone Screen", "Interview", "Offer", "Rejected"]

# --- DASHBOARD ---
@app.route("/")
def dashboard():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    resume = Resume.query.order_by(Resume.version.desc()).first()
    return render_template("dashboard.html", jobs=jobs, stages=STAGES, resume=resume)

# --- ADD JOB ---
@app.route("/add", methods=["POST"])
def add_job():
    job = Job(
        company=request.form["company"],
        role=request.form["role"],
        stage=request.form["stage"],
        date_applied=request.form["date_applied"],
        job_description=request.form["job_description"],
        notes=request.form["notes"]
    )
    db.session.add(job)
    db.session.commit()
    return redirect(url_for("dashboard"))

# --- UPDATE STAGE (drag or dropdown) ---
@app.route("/update_stage/<int:job_id>", methods=["POST"])
def update_stage(job_id):
    job = Job.query.get_or_404(job_id)
    job.stage = request.json["stage"]
    db.session.commit()
    return jsonify({"success": True})

# --- DELETE JOB ---
@app.route("/delete/<int:job_id>", methods=["POST"])
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    return redirect(url_for("dashboard"))

# --- SAVE RESUME ---
@app.route("/save_resume", methods=["POST"])
def save_resume():
    latest = Resume.query.order_by(Resume.version.desc()).first()
    new_resume = Resume(
        content=request.form["content"],
        version=latest.version + 1 if latest else 1
    )
    db.session.add(new_resume)
    db.session.commit()
    return redirect(url_for("dashboard"))

import pdfplumber
import docx2txt

# --- UPLOAD RESUME FILE ---
@app.route("/upload_resume", methods=["POST"])
def upload_resume():
    file = request.files["resume_file"]
    filename = file.filename

    if filename.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif filename.endswith(".docx"):
        text = docx2txt.process(file)
    else:
        text = file.read().decode("utf-8")

    # Save as new resume version
    latest = Resume.query.order_by(Resume.version.desc()).first()
    new_resume = Resume(
        content=text,
        version=latest.version + 1 if latest else 1
    )
    db.session.add(new_resume)
    db.session.commit()
    return jsonify({"text": text})

# --- AI: IMPROVE RESUME (streaming) ---
@app.route("/ai/improve_resume", methods=["POST"])
def improve_resume():
    resume_text = request.json["resume"]
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def generate():
        with client.messages.stream(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": f"You are a professional resume coach. Improve this resume for software engineering internship applications. Rewrite weak bullet points, add stronger action verbs, and quantify achievements where possible. Return only the improved resume text.\n\nRESUME:\n{resume_text}"
            }]
        ) as stream:
            for text in stream.text_stream:
                yield text

    return Response(stream_with_context(generate()), mimetype="text/plain")

# --- AI: MATCH SCORE (streaming) ---
@app.route("/ai/match_score", methods=["POST"])
def match_score():
    resume_text = request.json["resume"]
    job_description = request.json["job_description"]
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def generate():
        with client.messages.stream(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": f"You are a hiring manager. Score how well this resume matches the job description from 0-100. List: 3 strengths, 3 gaps, and 3 specific things to fix. Be direct.\n\nRESUME:\n{resume_text}\n\nJOB DESCRIPTION:\n{job_description}"
            }]
        ) as stream:
            for text in stream.text_stream:
                yield text

    return Response(stream_with_context(generate()), mimetype="text/plain")

@app.route("/ai/tailor_resume", methods=["POST"])
def tailor_resume():
    resume_text = request.json["resume"]
    job_description = request.json["job_description"]
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def generate():
        with client.messages.stream(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": f"You are a professional resume coach. Rewrite this resume to be tailored specifically for the job description below. Highlight relevant skills, reorder bullet points by relevance, and adjust language to match the job posting. Return only the improved resume text.\n\nRESUME:\n{resume_text}\n\nJOB DESCRIPTION:\n{job_description}"
            }]
        ) as stream:
            for text in stream.text_stream:
                yield text

    return Response(stream_with_context(generate()), mimetype="text/plain")


if __name__ == "__main__":
    app.run(debug=True)