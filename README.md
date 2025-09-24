---

# 🐱 AsKitty – AI-Powered Internal Document Chatbot

AsKitty is an innovative **AI chatbot** designed to transform the way employees and teams search, retrieve, and understand internal documents. With a seamless conversational interface, users can ask questions in natural language and quickly get concise answers from large or complex files stored within the company.

---

## 🚀 Features

* **Conversational Search** – Ask questions naturally and get clear answers.
* **Document Understanding** – Handles large files with many pages or technical content.
* **Summarization** – Delivers concise summaries for faster decision-making.
* **Cost-Efficient** – Optimized AWS architecture with costs **below \$50/month**.
* **Scalable & Lightweight** – Supports multiple users without heavy infrastructure.
* **Friendly UI/UX** – Easy to use, even for non-technical employees.

---

## 🏗️ Architecture Overview

AsKitty is built on **Amazon Web Services (AWS)** for scalability, affordability, and speed.

<img width="480" height="542" alt="image" src="https://github.com/user-attachments/assets/00fe75ea-37dc-48ae-b95b-2fba8ede1996" />


### Key Components:

* **Amazon CloudFront** – Delivers the web application securely and at low latency.
* **Amazon Cognito** – Handles secure user login and authentication.
* **Amazon S3 (Web Bucket & Docs Bucket)** – Stores frontend assets and uploaded documents.
* **AWS Lambda** – Powers ingestion, presigning, and query logic.
* **Amazon DynamoDB** – Stores metadata for document queries.
* **Amazon Bedrock**

  * **Titan Embedding v2** – Creates semantic text embeddings for accurate search.
  * **Nova Micro** – Hosts and runs the conversational AI model.
* **Amazon API Gateway** – Provides a secure API layer for communication between services.

---

## ⚙️ Workflow

1. **User Login** – Handled via Cognito and CloudFront.
2. **Document Upload** – Files are stored in the Docs Bucket.
3. **Ingestion** – AWS Lambda extracts, embeds, and stores semantic representations.
4. **Querying** – Users ask questions via the chatbot interface.
5. **AI Processing** – Titan Embedding + Nova Micro retrieve and generate relevant answers.
6. **Response** – Clear, summarized answers are returned to the user.

---

## 🛠️ Tech Stack

* **Frontend**: Web App served via Amazon CloudFront
* **Backend**: AWS Lambda, API Gateway
* **Database**: Amazon DynamoDB
* **AI Models**: Amazon Bedrock (Titan Embedding v2 + Nova Micro)
* **Storage**: Amazon S3 (Web & Docs Buckets)
* **Authentication**: Amazon Cognito

---

## 🌟 Why AsKitty?

* Saves employees time by reducing manual document searching.
* Improves knowledge sharing across teams and departments.
* Makes internal policies and technical manuals easy to understand.
* Provides an **affordable AI-powered solution** without enterprise-level costs.

---

## 📦 Getting Started

### Prerequisites

* AWS Account
* Node.js (for frontend if applicable)
* IAM permissions for S3, DynamoDB, Lambda, API Gateway, and Bedrock

### Setup

1. Clone this repo:

   ```bash
   git clone https://github.com/your-username/askitty.git
   cd askitty
   ```
2. Deploy frontend assets to S3 (Web Bucket).
3. Set up Cognito for authentication.
4. Configure API Gateway + Lambda functions for:

   * Upload
   * Ingest
   * Query
5. Connect DynamoDB and Bedrock models.
6. Serve the app via CloudFront.

---

## 💡 Example Use Case

* Upload a **50-page technical manual**.
* Ask: *“What are the safety procedures for equipment shutdown?”*
* AsKitty responds with a **concise summary** extracted directly from the manual.

---

## 📊 Cost Efficiency

By leveraging serverless AWS services and optimized Bedrock usage, AsKitty runs for **under \$50/month**, making it suitable for startups and SMEs.

---

## 🤝 Contributing

Contributions are welcome! Please fork the repo and submit a pull request with improvements.

---

## 📜 License

This project is licensed under the MIT License.

---

