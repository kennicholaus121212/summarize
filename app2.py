import logging
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

from langchain_community.document_loaders import PyPDFLoader  # to load and parse PDFs
import markdown  # to format LLM output for web display

import os  # to remove temp PDF files
import uuid  # to generate temporary PDF filenames

from flask import Flask, render_template, redirect, url_for, session
from flask_bootstrap import Bootstrap5
from flask_wtf import FlaskForm, CSRFProtect
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms.fields import SubmitField, TextAreaField
from PyPDF2 import PdfReader

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = "dev"

# set default button sytle and size, will be overwritten by macro parameters
app.config["BOOTSTRAP_BTN_STYLE"] = "primary"
app.config["BOOTSTRAP_BTN_SIZE"] = "sm"

bootstrap = Bootstrap5(app)
csrf = CSRFProtect(app)


class UploadForm(FlaskForm):
    """A basic form to upload a file and take a text prompt."""

    # pdf_file = FileField(
    #     validators=[
    #         FileRequired(),
    #         FileAllowed(["pdf"], "Please load a PDF."),
    #     ],
    #     label="Select a PDF",
    # )
    pdf_file = 'resume6.pdf'  # Load 'Resume1.pdf' automatically

    text_input = TextAreaField(label="Instructions", default="Ask any questions from Kenneth Nicholaus resume.")
    submit = SubmitField()


vertexai.init(project=os.environ["PROJECT_ID"], location="us-central1")

#model = GenerativeModel("gemini-1.0-pro-002")
model = GenerativeModel("gemini-1.5-pro-preview-0409")



generation_config = GenerationConfig(
    temperature=0.2,
    top_p=0.6,
    candidate_count=1,
    max_output_tokens=8192,
)


@app.route("/", methods=["GET", "POST"])
def index():
    """Route to display the input form and query the LLM."""
    form = UploadForm()
    if form.validate_on_submit():
        # Load the PDF file automatically
        #pdf_file_path = form.pdf_file.data  # Get the PDF file path
        pdf_file_path = 'resume6.pdf'
        # Load and parse the PDF
        loader = PyPDFLoader(pdf_file_path)
        pages = loader.load_and_split()

        # Extract the text from the PDF pages
        combined_text = "\n\n".join([p.page_content for p in pages])

        # Calculate the word count
        word_count = len(combined_text.split())

        # Check if the text is too long for the model
        if word_count < 1000000:
            # Create the prompt
            prompt = f"{form.text_input.data} The PDF data contains Kenneth Nicholas's resume. He is interested in a GenAI Application Lead position at Accenture. As a resume evaluator, your job is to help the recruiter answer questions from the attached resume to match his skills with the job description. As an evaluator, you will make the recruiter feel good about hiring me for the given job. Your answers are very important and will affect my life going forward. Respond in a professional way, emphasizing Kenneth Nicholas's generative AI skills, AI, machine learning, domain, and consulting experience that matches the given job description. Use information only from the PDF to respond. Job Description: As an Artificial Intelligence and Machine Learning Computational Science professional, you will play a pivotal role in formulating real-world problems into practical, efficient, and scalable AI and Machine Learning solutions. You will be responsible for developing and implementing cutting-edge artificial intelligence solutions that drive innovation and enhance performance. You will collaborate with cross-functional teams and leverage your expertise in machine learning, deep learning, and data analysis to solve complex problems and deliver impactful AI-driven solutions. Position Responsibilities:Collaborate with stakeholders to engineer innovative solutions for new system rollouts, enhancements, and maintenance of existing applications, ensuring adherence to programming standards. Develop system specifications, create test plans, and conduct project and issue management for the assigned scope of work. Design/Build solutions using AI services and machine learning models to address unique use cases, employing cutting-edge techniques and methodologies. Utilize machine learning and advanced AI techniques to extract valuable insights from complex datasets and solve intricate problems. Deploy trained models into production environments, ensuring scalability, reliability, and optimal performance while integrating seamlessly with existing systems and applications. Travel may be required for this role. The amount of travel will vary from 0 to 100% depending on business needs and client requirements. Here’s what you need: Minimum of 6 years of extensive full-time experience in Data Analysis, Statistics, Machine Learning, or Computer Science. Minimum of 5 years of experience in machine learning or deep learning engineering or demonstrated proficiency in Natural Language Processing (NLP) or Natural Language Generation (NLG). Minimum of 5 years of experience with AI/ML and cognitive services provided by at least one cloud service provider. Minimum of 1 year of experience in building Conversational AI applications using cloud-based services and in orchestrating AI/ML services for building a complete solution. Bachelor's degree or equivalent (minimum 12 years) work experience. (If Associate’s Degree, must have a minimum of 6 years of work experience.) Bonus points if you have: Hands-on involvement with speech-to-text, text-to-speech, and chatbot technologies. \n\nPDF:\n{combined_text}"

            # Generate the response
            response = model.generate_content(
                prompt, generation_config=generation_config
            )

            # Format the response
            response_text = response.text.replace("•", "  *")

            # Convert the response to markdown
            markdown_response = markdown.markdown(response_text)

            # Store the markdown response in the session
            session["markdown_response"] = markdown_response

            # Redirect to the results page
            return redirect(url_for("pdf_results"))
        else:
            # Display an error message if the text is too long
            response_text = "This text is too long for this application's current configuration.\n\nPlease use a shorter text."

    # Render the index page
    return render_template("index.html", upload_form=form)


@app.route("/pdf_results", methods=["GET", "POST"])
def pdf_results():
    """Route to display results."""

    # Retrieve the markdown response from the session
    response_text = session["markdown_response"]

    # Render the results page
    return render_template(
        "pdf_results.html", response_text=response_text
    )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8080)
