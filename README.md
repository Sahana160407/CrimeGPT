# CrimeGPT – AI-Powered Crime Investigation & Intelligence Platform

<p align="center">
  <img src="assets/crimegpt.png" width="180">
</p>

<h2 align="center">AI-Powered Crime Investigation & Intelligence Platform</h2>

<p align="center">
  A centralized platform for crime data exploration, AI-assisted investigation,
  document summarization, reporting, and secure information access.
</p>

---

## About the Project

CrimeGPT is an AI-assisted crime investigation and intelligence platform designed
to help authorized personnel organize, explore, retrieve, and summarize
crime-related information through a centralized interface.

The system brings multiple investigation-support activities into one platform,
including crime data visualization, case exploration, AI-assisted interaction,
document processing, report management, and authorized personnel management.

The current version focuses on **information retrieval, visualization,
AI-assisted queries, and document summarization**. Automated crime pattern
matching and crime prediction are **not implemented in the current version**
and are considered future enhancements.

---

## Problem Statement

Crime-related information can be maintained across different records,
spreadsheets, reports, and documents. Manually searching and reviewing this
information can be time-consuming and may make it difficult for investigators
to quickly access relevant case information.

There is a need for a centralized system that can organize crime information,
provide easier case exploration, assist with document understanding, and
present relevant information through a structured interface.

---

## Proposed Solution

CrimeGPT provides a centralized investigation-support platform where authorized
users can:

- View crime-related information through a dashboard
- Search and explore individual cases
- Interact with an AI-assisted investigation assistant
- Upload and summarize supported documents
- Manage investigation reports
- Manage authorization requests and authorized personnel
- Access information according to their assigned role and location

The system is designed to **assist investigators rather than replace human
decision-making**.

---

## Key Features

### Crime Intelligence Dashboard

Provides an overview of available crime information using:

- Key performance indicators
- Crime-related statistics
- Trend visualizations
- Category-based information
- Location-related information

### AI Assistant

Provides an AI-assisted natural-language interface that allows authorized
users to ask questions and obtain information from the available data.

### Case Explorer

Allows users to:

- Search cases
- Filter available records
- View case information
- Examine individual case details

### Document Summarization

Users can upload supported investigation documents and obtain
AI-assisted summaries.

The original document can be retained for verification while the generated
summary provides a concise overview.

### Reports

Provides functionality for managing uploaded documents and
AI-assisted report summaries.

### Administration

Provides administrative functionality for:

- Reviewing authorization requests
- Approving users
- Managing authorized personnel
- Viewing personnel profiles
- Managing access-related information

### Location-Based Access

The system records the user's assigned office location during registration.
The location can then be used to determine which information should be
available to the user.

### Role-Based Access

Different users can have different permissions based on their assigned role.
Administrative functions are restricted to authorized administrative users.

---

## AI / ML Usage

The current version of CrimeGPT uses AI primarily for:

- Natural-language interaction
- Understanding user queries
- AI-assisted document summarization
- Text-based information processing

### Current Limitation

The current version **does not implement a dedicated Machine Learning model
for automated crime pattern matching or crime prediction**.

The system currently focuses on retrieving, organizing, visualizing, and
summarizing available crime information.

Advanced ML-based crime pattern detection and prediction are planned as
future enhancements.

---

## Technology Stack

| Technology | Purpose |
|---|---|
| React.js | Frontend development |
| HTML | Application structure |
| CSS | User interface design |
| JavaScript | Application functionality |
| Node.js | Backend runtime |
| Express.js | Backend API development |
| MongoDB | Database |
| Artificial Intelligence | AI-assisted interaction and processing |
| Natural Language Processing | Text and query processing |
| Git & GitHub | Version control |

---

## System Workflow

```text
User Registration
       ↓
Admin Approval
       ↓
Secure Login
       ↓
Role & Location Verification
       ↓
Crime Intelligence Dashboard
       ↓
 ┌───────────────┬────────────────┬
 ↓               ↓                ↓
Case Explorer   AI Assistant     Reports
                                   ↓
                          Document Summarization
