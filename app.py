from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

app = Flask(__name__)
app.secret_key = "any-random-text-you-like"   # needed for flash messages
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024   # 10 MB upload limit

# ---- CHANGE THESE TWO VALUES ----
BUCKET_NAME = "your-bucket-name-here"
REGION = "ap-south-1"
# ---------------------------------

# No access keys here. boto3 automatically uses the EC2 IAM role.
s3 = boto3.client("s3", region_name=REGION)


def get_uploaded_files():
    """Return a list of filenames stored in the S3 bucket."""
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME)
        return [item["Key"] for item in response.get("Contents", [])]
    except (ClientError, NoCredentialsError) as e:
        print("Error listing files:", e)
        return None


@app.route("/")
def index():
    files = get_uploaded_files()
    if files is None:
        flash("Could not read the file list from S3. Check the server logs.", "error")
        files = []
    return render_template("index.html", files=files)


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")

    if file is None or file.filename == "":
        flash("Please select a file first.", "error")
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    if filename == "":
        flash("Invalid file name. Please rename the file and try again.", "error")
        return redirect(url_for("index"))

    try:
        s3.upload_fileobj(file, BUCKET_NAME, filename)
        flash(f"Success! '{filename}' was uploaded to S3.", "success")
    except (ClientError, NoCredentialsError) as e:
        print("Upload error:", e)
        flash("Upload failed. Check the bucket name, region and IAM role.", "error")

    return redirect(url_for("index"))


@app.errorhandler(413)
def file_too_large(e):
    flash("File is too large. Maximum size is 10 MB.", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)