# ArabPoet: MLOps & AI Architecture Pipeline

## Overview
ArabPoet is an advanced, production-grade AI system engineered to tackle the complex computational problem of analyzing classical and modern Arabic poetry. This project demonstrates end-to-end MLOps capabilities, bridging the gap between deep learning research and scalable production deployment.

The core of the system is a State-Of-The-Art (SOTA) Multi-Task Learning (MTL) architecture that simultaneously predicts metrical structures (البحر), rhyme schemes (القافية), and detects metrical anomalies (الكسر العروضي).

## AI Problem-Solving & Data Engineering
Analyzing Arabic poetry computationally requires extreme sensitivity to phonetic structures, diacritics (Tashkeel), and rhythmic anomalies. 
- **Character-Level Representation:** Transitioned from pure word embeddings to a character-level bifurcated encoding strategy that inherently captures the morphological and phonetic nuances of the Arabic language.
- **Deep Cleansing & Deduplication:** Developed robust text normalization pipelines utilizing regular expressions to remove Tatweel (Kashida) and external noise while preserving critical diacritics.
- **Capped Stratified Sampling:** Handled severe class imbalances across different poetic meters using capped sampling techniques, ensuring the model doesn't overfit to majority classes (e.g., الطويل).
- **Synthetic Anomaly Injection:** Engineered a novel data augmentation pipeline that intelligently mutates diacritics and characters to simulate natural rhythmic breaks, creating robust training data for the anomaly detection branch.

## Model Architecture
The AI engine leverages a highly specialized Dual-Branch Architecture optimized for MTL:
- **Shared Encoder Foundation:** Employs AraBERT v02 to extract dense contextual embeddings, dynamically capturing semantic and structural relationships within the verse.
- **Meter Classification Branch (Sequential + Attention):** Utilizes Bi-LSTMs combined with Attention Mechanisms to model the sequential rhythm of the poem, accurately classifying it into one of the standard Khalil meters.
- **Anomaly Detection Branch (CNN + LSTM):** A parallel pathway designed for anomaly detection. It uses Conv1D layers to capture local phonetic deviations followed by an LSTM layer to identify structural breaks indicative of a metrical error.
- **Rhyme Classification Branch:** A dedicated Convolutional head focused purely on the tail characters of the verse, optimized to predict the specific rhyme scheme.

## Advanced Training Dynamics
To ensure the MTL heads do not destructively interfere, the system incorporates advanced optimization strategies:
- **Projecting Conflicting Gradients (PCGrad):** Wraps the optimizer to prevent gradient interference between the three distinct tasks, forcing orthogonal gradient updates.
- **Dynamic MTL Focal Loss:** Combines Homoscedastic Uncertainty weighting with Focal Loss to dynamically balance the loss contribution of meter classification, rhyme prediction, and error detection based on task difficulty.
- **Multi-GPU Parallelization:** Implemented `torch.nn.DataParallel` and optimized DataLoader pipelines (`pin_memory`, `prefetch_factor`) to break I/O bottlenecks and scale training across multiple GPUs seamlessly.

## End-to-End Operational Pipelines
Beyond the model, this repository showcases a complete operationalization strategy. The backend components are framed strictly as mechanisms to serve and scale the AI model in production:
- **Inference Microservice (FastAPI):** A high-throughput, low-latency operational pipeline designed to serve inference requests. It elegantly wraps the PyTorch models and incorporates fallback mechanisms (e.g., LLMs via RAG/Gemini) for highly ambiguous inputs.
- **Deployment Interface (Gradio):** An interactive UI layer built to stream predictions and visualize the AI's structural reasoning, serving as the client-facing proof-of-concept for the backend microservice.
- **Scalable Architecture:** Designed with dependency injection and asynchronous request handling to seamlessly integrate into Dockerized environments and Kubernetes clusters.

## Getting Started

### Prerequisites
- Python 3.10+
- PyTorch & Transformers
- FastAPI & Uvicorn

### ⚠️ Acquiring Weights & Data (Smart Artifact Handling)
To keep this repository lightweight and adhere to Git best practices, **heavy model weights and datasets are NOT included in this repository**. You must manually acquire them before running the inference pipelines:

1. **ArabPoet SOTA Weights:**
   - Download `hybrid_mtl_best_sota.pt` [from the release page/Kaggle]
   - Place the file exactly at: `/arab_poet_microservice/weights/hybrid_mtl_best_sota.pt`

2. **BGE-M3 Embedding Models:**
   - Download the BGE-M3 model files (ONNX/BIN weights)
   - Place them inside the `/arab_poet_microservice/models/bge-m3/` directory.

### Initialization
Once you have acquired the necessary weights:

1. Clone the repository and install the operational dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. **Launch the AI Microservice Pipeline:**
   ```bash
   cd arab_poet_microservice/app
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
3. **Initialize the Deployment Interface:**
   ```bash
   python gradio_app.py
   ```
   Access the ML analysis dashboard at `http://localhost:7860`.

## License
MIT License
