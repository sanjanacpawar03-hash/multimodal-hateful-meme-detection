# Multimodal Hateful Meme Detection Using ResNet-50 and BERT

## Project Overview

This project is a web-based AI application that detects hateful and non-hateful memes by analyzing both image and text content.

It combines ResNet-50 for visual feature extraction and BERT for text understanding. The extracted features are fused and passed through a classification network to predict whether a meme is hateful or non-hateful.

## Technologies Used

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python, Flask
- **Database:** MySQL
- **Database Environment:** XAMPP
- **Deep Learning:** PyTorch
- **Image Processing:** ResNet-50, Pillow, Torchvision
- **Natural Language Processing:** BERT, Transformers
- **Data Processing:** NumPy, Pandas
- **Machine Learning:** Scikit-learn

## Model Architecture

1. **Image Processing:** ResNet-50 extracts visual features and produces a 512-dimensional feature vector.
2. **Text Processing:** BERT extracts semantic text features, which are projected into a 512-dimensional vector.
3. **Feature Fusion:** Image and text features are concatenated into a 1,024-dimensional vector.
4. **Classification:** Fully connected layers, ReLU activation, dropout, and sigmoid activation generate the prediction.

## Application Features

### User Module
- User registration and login.
- Upload memes with text for detection.
- View hateful or non-hateful predictions.
- Access frequently asked questions.
- Submit queries to the administrator.
- View administrator responses.

### Admin Module
- Administrator login.
- View and manage registered users.
- Add and delete FAQs.
- View user queries and respond to them.

## Model Evaluation

The project uses the following evaluation metrics:

- Accuracy
- F1-score
- ROC-AUC

## Project Workflow

1. Dataset collection and preprocessing.
2. Image preprocessing and BERT tokenization.
3. Feature extraction using ResNet-50 and BERT.
4. Multimodal feature concatenation.
5. Model training and validation.
6. Meme prediction through the Flask application.

## Project Structure

```text
multimodal-hateful-meme-detection/
│
├── model/
│   ├── hateful_meme_resnet_bert.py
│   ├── accuracy.docx
│   └── README.md
│
├── static/
│   ├── css/
│   ├── images/
│   └── README.md
│
├── templates/
│   ├── Admin/
│   ├── User/
│   └── README.md
│
├── app.py
├── database.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/sanjanacpaw ar03-hash/multimodal-hateful-meme-detection.git
cd multimodal-hateful-meme-detection
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure MySQL

- Install and start XAMPP.
- Start the MySQL service.
- Create and configure the required database.
- Configure the database connection according to your local environment.
