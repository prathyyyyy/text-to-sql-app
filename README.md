# 🧠 Natural Language to Databricks SQL

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![AWS EC2](https://img.shields.io/badge/Deployed%20on-AWS%20EC2-orange)](#)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-red)](#)
[![LangChain](https://img.shields.io/badge/Powered%20by-LangChain-green)](#)
[![ChatGPT-5](https://img.shields.io/badge/AI-ChatGPT--5-purple)](#)

## 🚀 Project Overview

A **production-ready application** for Product Managers (PMs) and core teams that transforms  
**plain-English questions into safe, optimized Databricks SQL queries** using **ChatGPT-5 + LangChain**,  
deployed on **AWS EC2** with a **Streamlit UI**.

---

## 🔑 Key Features

- **Natural Language to SQL**  
  Convert plain-English business questions into Databricks SQL queries, optimized for performance and safety.

- **Schema-Aware & Error-Resilient**  
  Developed the **Entity Relationship Diagram (ERD)** with ChatGPT-5 and enforced schema-aware validation checks to prevent malformed queries.

- **Safe Query Execution**  
  - Built-in **validation & dry-run checks** before execution  
  - **Row limits & guardrails** to prevent heavy/unsafe queries  

- **LangChain Orchestration**  
  Handles reasoning, prompt engineering, and context injection for reliable SQL generation.

- **Streamlit UI**  
  Lightweight, interactive web app that empowers PMs & teams to query Databricks without writing SQL.

- **AWS Deployment**  
  Hosted on **AWS EC2** for scalability and enterprise-grade availability.

---

## 🛡 Benefits

- Empowers PMs with **self-serve analytics** using natural language  
- Reduces reliance on data engineering teams for day-to-day queries  
- Enhances **reliability** of AI-generated SQL by minimizing malformed queries  
- Accelerates decision-making with **faster insights**

---

## 📸 Screenshots

- ## 1. Login Page: <img width="1681" height="752" alt="chrome-capture-2025-08-21" src="https://github.com/user-attachments/assets/38a44c6d-4db5-4f28-9ecc-5065c453cb57" />
<img width="1812" height="528" alt="chrome-capture-2025-08-21 (1)" src="https://github.com/user-attachments/assets/3c163663-186b-4fc8-985d-23f90e78d9de" />


- ## 2. ERD Diagram Generation: <img width="1910" height="1863" alt="SQLGenPro" src="https://github.com/user-attachments/assets/ac578e50-7f3c-4a9e-bc83-de67ae7fddc4" />

<img width="943" height="737" alt="erd" src="https://github.com/user-attachments/assets/c8a30726-8f71-48ad-9d0d-9f6b8bec388c" />


- ## 3. Main Page - Text to Sql Converter, Retrive Favourites, Quick Analysis: 
<img width="1909" height="1076" alt="chrome-capture-2025-08-21 (2)" src="https://github.com/user-attachments/assets/1522607d-1805-463f-975c-265f9ca4b637" />
<img width="1909" height="2085" alt="chrome-capture-2025-08-21 (3)" src="https://github.com/user-attachments/assets/dae17857-b425-4634-8d05-a4f941066a82" />
<img width="1909" height="1973" alt="chrome-capture-2025-08-21 (6)" src="https://github.com/user-attachments/assets/a77187bf-6d1f-4fca-b0e2-d4d22408d645" />
<img width="1909" height="2823" alt="chrome-capture-2025-08-21 (7)" src="https://github.com/user-attachments/assets/70c55bfa-50cc-4765-9fea-9ceef5abd737" />
<img width="1401" height="765" alt="chrome-capture-2025-08-21 (8)" src="https://github.com/user-attachments/assets/7d74181c-3db5-4979-ab47-731f80c7a78d" />
<img width="1909" height="2823" alt="chrome-capture-2025-08-21 (9)" src="https://github.com/user-attachments/assets/7fc2a1b8-4a42-4962-9caf-2650ab3fac5b" />



- ## 4. Cloud Section - EC2 Deployment and Databricks Catalog: 

<img width="1283" height="833" alt="Screenshot 2025-08-21 214150" src="https://github.com/user-attachments/assets/8a0de150-a5a7-4263-90d5-59d12ee7b24e" />

<img width="1842" height="420" alt="Screenshot 2025-08-21 235912" src="https://github.com/user-attachments/assets/b993b0b0-ac83-404b-b3de-56e9cf63ac80" />


---

## ⚙️ Tech Stack

- **AI & Orchestration**: ChatGPT-5, LangChain  
- **Frontend**: Streamlit  
- **Backend/Infra**: Python, AWS EC2  
- **Database**: Databricks SQL  
- **DevOps**: Docker, GitHub Actions (optional)  

---

## 🚦 Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/your-username/nl-to-databricks-sql.git
cd nl-to-databricks-sql




