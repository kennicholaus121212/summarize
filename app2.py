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
            prompt = f"{form.text_input.data} The PDF data contains Kenneth Nicholaus resume. He is interested in a GenAI Application Lead position at Accenture. You should respond in a professional way emphasizing his generative AI skills, AI, machine learning, domain and consuling experience. Use information only from the PDF to respond.\n\nPDF:\n{combined_text}"

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
