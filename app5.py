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

    pdf_file = FileField(
        validators=[
            FileRequired(),
            FileAllowed(["pdf"], "Please Load Your Resume in PDF Format."),
        ],
        label="Browse To Select Your Resume",
    )
    #pdf_file = 'resume5.pdf'  # Load 'Resume1.pdf' automatically
    text_input1 = TextAreaField(label="Job Descriptions", default="Paste Job Description Here.")
    text_input = TextAreaField(label="Instructions", default="Summarize the job applicants fit for the job in bullet points. State the average skill match score, weaknesses and skills to improve for perfect match at the bottom")
    submit = SubmitField()


vertexai.init(project=os.environ["PROJECT_ID"], location="us-central1")

#model = GenerativeModel("gemini-1.0-pro-002")
model = GenerativeModel("gemini-1.5-pro-preview-0409")



generation_config = GenerationConfig(
    temperature=0.1,
    top_p=0.8,
    candidate_count=1,
    max_output_tokens=8192,
)


@app.route("/", methods=["GET", "POST"])
def index():
    """Route to display the input form and query the LLM."""
    form = UploadForm()
    if form.validate_on_submit():
        pdf_temp_filename = str(uuid.uuid4())
        form.pdf_file.data.save(pdf_temp_filename)
        #loader = PyPDFLoader('/Resume1.pdf')
        loader = PyPDFLoader(pdf_temp_filename)


        # # Load the PDF file automatically
        # #pdf_file_path = form.pdf_file.data  # Get the PDF file path
        # pdf_file_path = 'resume5.pdf'
        # # Load and parse the PDF
        # loader = PyPDFLoader(pdf_file_path)
        pages = loader.load_and_split()

        # Extract the text from the PDF pages
        combined_text = "\n\n".join([p.page_content for p in pages])

        # Calculate the word count
        word_count = len(combined_text.split())

        # Check if the text is too long for the model
        if word_count < 1000000:
            # Create the prompt
            prompt = f""" You are a Human Resources expert. Who is an expert at evaluating job applicants using their resume and job description
            Your additional instructions: {form.text_input.data}, 
            If there is no Job description, Use the resume alone to answer your additional instructions.
            Resume:{combined_text},
            Job Description applying for: {form.text_input1.data}, 

            Evaluate skills from the resume and the job description. and list them.
            Match each of the skills from the resume to job descriptions. 
            if there is a match assign 1 for perfect match
            If there is no match assign 0
            if there is a partial match assign a number between 1 and 0 which corresponds to the strength of the skills from the resume
            Now add all the numbers and average them.

            Here is an example.
            identified skills 4
            skill 1 full match therfore assigned 1
            skill 2 no match therefore assigned 0
            skill 3 is a strong match but not full therefore assiged 0.8
            skill 4 is a weak match therefore assigned a value of 0.2

            total numbner of skills = 4
            sum of all skills =1+0+0.8+0.2 = 2.0
            average of skills = 2.0/4 = 0.5
            converting to percent match = 0.5*100 = 50%
            skill match is 50%
            
            In your result answer how much the person is qualified for the job and also include the the skill match percent
            
            """
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
            os.remove(pdf_temp_filename)
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
