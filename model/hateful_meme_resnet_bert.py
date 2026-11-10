#!/usr/bin/env python3
"""
Hateful Meme Detector (ResNet + BERT) - FIXED
--------------------------------------------
Fixes image-path issue where json has 'img/...' leading to
hateful_memes/img/img/xxxxx.png lookup. Also filters out
rows whose image files are missing before training.

Usage:
    python hateful_meme_resnet_bert_fixed.py
"""

import os
import json
from pathlib import Path
from tqdm import tqdm
import numpy as np
import pandas as pd
from PIL import Image

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from transformers import BertTokenizer, BertModel
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

# ------------------ CONFIG ------------------
DATA_DIR = Path("hateful_memes")
IMG_DIR = DATA_DIR / "img"
TRAIN_JSONL = DATA_DIR / "train.jsonl"
MODEL_SAVE_PATH = Path("hateful_meme_resnet_bert_fixed.pth")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE = 8
EPOCHS = 3
LR = 2e-5
# --------------------------------------------


def read_jsonl(path):
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            data.append(json.loads(line))
    return pd.DataFrame(data)


# ---------------- DATASET ----------------
class HatefulMemeDataset(Dataset):
    def __init__(self, df, tokenizer, transform):
        self.df = df.reset_index(drop=True)
        self.tokenizer = tokenizer
        self.transform = transform

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        # Remove any directory prefix and use only the filename → prevents double 'img/img' problem
        img_filename = os.path.basename(row["img"])
        img_path = IMG_DIR / img_filename

        # If image still missing, raise clear error (shouldn't happen because we pre-filter)
        if not img_path.exists():
            raise FileNotFoundError(f"Image not found: {img_path}")

        image = Image.open(img_path).convert("RGB")
        image = self.transform(image)

        text = row.get("text", "") or ""
        inputs = self.tokenizer(
            text,
            max_length=50,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )

        label = torch.tensor(row["label"], dtype=torch.float)
        return image, inputs["input_ids"].squeeze(0), inputs["attention_mask"].squeeze(0), label


# ---------------- MODEL ----------------
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


# ---------------- TRAINING ----------------
def train_model(model, train_loader, val_loader, optimizer, criterion):
    best_auc = 0.0
    for epoch in range(EPOCHS):
        model.train()
        train_loss = 0.0
        for img, ids, mask, labels in tqdm(train_loader, desc=f"Epoch {epoch+1}/{EPOCHS}"):
            img, ids, mask, labels = img.to(DEVICE), ids.to(DEVICE), mask.to(DEVICE), labels.to(DEVICE)

            optimizer.zero_grad()
            outputs = model(img, ids, mask).squeeze()
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        avg_train_loss = train_loss / len(train_loader)
        print(f"\nEpoch {epoch+1} Training Loss: {avg_train_loss:.4f}")

        # Validation
        model.eval()
        y_true, y_pred = [], []
        with torch.no_grad():
            for img, ids, mask, labels in val_loader:
                img, ids, mask = img.to(DEVICE), ids.to(DEVICE), mask.to(DEVICE)
                outputs = model(img, ids, mask).squeeze().cpu().numpy()
                y_pred.extend(outputs.tolist())
                y_true.extend(labels.numpy().tolist())

        y_pred_arr = np.array(y_pred)
        y_pred_bin = (y_pred_arr >= 0.5).astype(int)
        acc = accuracy_score(y_true, y_pred_bin)
        f1 = f1_score(y_true, y_pred_bin)
        auc = roc_auc_score(y_true, y_pred_arr)
        print(f"Validation: Acc={acc:.4f} | F1={f1:.4f} | AUC={auc:.4f}")

        if auc > best_auc:
            best_auc = auc
            torch.save(model.state_dict(), MODEL_SAVE_PATH)
            print(f"✅ Model saved to {MODEL_SAVE_PATH}")


# ---------------- PREDICTION ----------------
def predict_single(image_path, text):
    from transformers import BertTokenizer  # local import to avoid top-level heavy import duplication
    tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    # allow user to pass file with full path or just filename
    img_filename = os.path.basename(image_path)
    resolved_path = Path(image_path) if Path(image_path).exists() else IMG_DIR / img_filename

    if not resolved_path.exists():
        print(f"Image not found: {resolved_path}")
        return

    img = Image.open(resolved_path).convert("RGB")
    img = transform(img).unsqueeze(0).to(DEVICE)
    inputs = tokenizer(text or "", return_tensors="pt", padding=True, truncation=True).to(DEVICE)

    model = MultiModalModel().to(DEVICE)
    model.load_state_dict(torch.load(MODEL_SAVE_PATH, map_location=DEVICE))
    model.eval()

    with torch.no_grad():
        prob = model(img, inputs["input_ids"], inputs["attention_mask"]).item()
    label = "🔥 HATEFUL" if prob >= 0.5 else "😊 NON-HATEFUL"
    print(f"\n🧠 Prediction for: {resolved_path.name}")
    print(f"Text: {text if text else '(none)'}")
    print(f"→ Result: {label} ({prob*100:.2f}% hateful)\n")


# ---------------- MAIN ----------------
def main():
    print("\n🚀 Loading dataset...")
    df = read_jsonl(TRAIN_JSONL)

    # Ensure column 'img' exists and is string; fix if some rows have dict etc.
    df["img"] = df["img"].astype(str)

    # Filter rows to only those with an existing image file (use basename to avoid 'img/img' mismatch)
    def image_exists(row_img):
        fname = os.path.basename(row_img)
        return (IMG_DIR / fname).exists()

    df["__img_exists"] = df["img"].apply(image_exists)
    missing_count = (~df["__img_exists"]).sum()
    if missing_count > 0:
        print(f"⚠️ {missing_count} rows in JSONL reference missing images. They will be skipped.")
    df = df[df["__img_exists"]].drop(columns="__img_exists").reset_index(drop=True)

    print(f"Using {len(df)} samples for training/validation after filtering missing images.")

    train_df, val_df = train_test_split(df, test_size=0.15, stratify=df["label"], random_state=42)

    from transformers import BertTokenizer  # local import here
    tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
    global transforms
    from torchvision import transforms as T  # alias locally
    transforms = T

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    train_loader = DataLoader(HatefulMemeDataset(train_df, tokenizer, transform),
                              batch_size=BATCH_SIZE, shuffle=True, num_workers=2, pin_memory=True)
    val_loader = DataLoader(HatefulMemeDataset(val_df, tokenizer, transform),
                            batch_size=BATCH_SIZE, shuffle=False, num_workers=2, pin_memory=True)

    model = MultiModalModel().to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR)
    criterion = nn.BCELoss()

    train_model(model, train_loader, val_loader, optimizer, criterion)

    # After training, ask for a test image path (or filename)
    image_path = input("\n Enter image path or filename to test: ").strip()
    text = input("💬 Enter meme text (optional): ").strip()
    predict_single(image_path, text)


if __name__ == "__main__":
    main()
