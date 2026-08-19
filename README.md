# Clinical-to-FHIR: End-to-End IoMT Data Pipeline Simulator

An end-to-end clinical data pipeline simulator written in Python that bridges real physiological sensor telemetry with global healthcare interoperability standards (HL7 FHIR R4). Designed and developed from the perspective of a clinical-programmer to demonstrate how hardware telemetry can be processed and seamlessly integrated into hospital Electronic Health Record (EHR) networks.

---

## 📌 Project Overview & Architecture

This repository contains a modular, object-oriented Python simulator (`iomt-pipeline-simulator.py`) that models the entire lifecycle of an Internet of Medical Things (IoMT) wearable device—from physiological wave generation to hospital database integration.

```
+---------------------------+
|    Physiological Sensor   | <-- Synthesizes raw 50Hz analog PPG wave (Fourier-series modeling)
+---------------------------+
              | (Raw wave stream)
              v
+---------------------------+
|    Edge Microcontroller   | <-- Filters noise, runs peak detection, computes HR & SpO2
+---------------------------+
              | (Lightweight JSON telemetry)
              v
+---------------------------+
|    Interoperability Gw    | <-- Translates telemetry to HL7 FHIR (R4) using LOINC/UCUM
+---------------------------+
              | (Structured FHIR Transaction Bundle)
              v
+---------------------------+
|    Hospital EHR Server    | <-- Simulates secure HTTP POST to central HAPI FHIR gateway
+---------------------------+
```

---

## 🩺 Clinical-Engineering Design Principles

This project is built explicitly to solve real-world clinical and engineering challenges that typically divide hardware developers and hospital clinicians.

### 1. Mathematically Accurate Waveform Synthesis (`PhysiologicalSensor`)
Instead of utilizing generic random number generation, the sensor class synthesizes a realistic **analog Photoplethysmogram (PPG)** optical waveform.
* **Cardiac Physics:** The wave is modeled using superimposed sine waves (Fourier-series mathematics) to depict distinct cardiovascular phases: the **systolic peak**, the **dicrotic notch** (representing the transient closure of the aortic valve), and the **diastolic decay**.
* **Clinical Realism:** The simulator overlays high-frequency electrical sensor noise and low-frequency baseline drift (simulating the physical rise and fall of the patient's chest during respiration).

### 2. Edge Signal Processing & Peak Filtering (`EdgeMicrocontroller`)
Standard peak-detection algorithms frequently suffer from "double-counting" errors in clinical settings, mistaking the dicrotic notch for an independent heartbeat and artificially doubling the heart rate.
* **Refractory Period Filter:** To solve this, the microcontroller class implements a physiological refractory window. It filters out peaks that occur too close together (based on the oximeter's 50Hz sampling rate), ensuring heart rate calculations remain clinically accurate.
* **Ratio-of-Ratios SpO2:** It simulates a dual-wavelength oximeter calculation, comparing Red and Infrared LED absorption ratios to compute blood oxygenation levels.

### 3. Semantic Interoperability & Medical Standards (`FHIRMiddleware`)
Hospital Electronic Health Records (EHRs) cannot ingest raw serial data or arbitrary JSON streams. This middleware acts as a translator, mapping telemetry into standard clinical terminologies:
* **HL7 FHIR (Release 4):** Standardizes data into an official FHIR `Bundle` containing individual `Observation` resources.
* **LOINC Coding:** Maps heart rate to code `8867-4` (Heart rate) and SpO2 to code `59408-5` (Oxygen saturation).
* **UCUM Units:** Standardizes clinical units to `/min` and `%`.
* **Clinical Triage Logic:** Automatically evaluates clinical thresholds to assign official HL7 interpretation codes (e.g., automatically inserting a low status code `L` if SpO2 falls below 92%).

---

## 📂 File Directory

*   **`iomt-pipeline-simulator.py`**: The primary executable pipeline script containing the sensor simulation, edge filtering, FHIR translation, and HTTP network simulation.
*   **`simulated-fhir-bundle.json`**: A sample, production-ready multi-resource transaction payload exported directly by the script.

---

## 🚀 How to Run the Pipeline

### Prerequisites
*   Python 3.8 or higher.
*   No external libraries required (uses pure standard libraries for maximum portability).

### Execution
Clone this repository and run the simulator from your terminal:

```bash
git clone https://github.com/neranjandissanayake/iomt-clinical-fhir-pipeline.git
cd iomt-clinical-fhir-pipeline
python3 iomt-pipeline-simulator.py
```

### Expected Output
The script will initialize the components, simulate real-time patient monitoring cycles, and output clean console logs depicting the processing stages:

```text
================================================================================
     IoMT END-TO-END CLINICAL DATA PIPELINE SIMULATOR - INITIALIZING
================================================================================
[1/4] Initializing Optical PPG Waveform Oximeter Sensor...
[2/4] Initializing Edge Microcontroller (ESP32-MAX30102)...
[3/4] Initializing Interoperability Middleware (HL7 FHIR Gateway)...
[4/4] Connecting to Hospital Central EHR Gateway...

--------------------------------------------------------------------------------
 MONITORING CYCLE 1 - SENSOR BUFFER ACQUISITION IN PROGRESS...
--------------------------------------------------------------------------------

[EDGE ESP32 COMPLETED]:
  * Local Device ID: IoMT-ESP32-MAX30102-009A
  * Computed Heart Rate: 72.4 BPM
  * Computed SpO2 level: 98.2%
  * Raw Transmitted Payload:
    { "vitals": { "hr": 72.4, "spo2": 98.2 } ... }

[MIDDLEWARE] Parsing telemetry & converting to HL7 FHIR v4 Bundle...
  * Formatted Standardized LOINC Observation IDs: obs-hr-ESP32-5567, obs-spo2-ESP32-5567

[HTTP POST] Connecting to FHIR Endpoint: https://fhir-gateway.hospital-network.org/r4 ...
  >> Content-Type: application/fhir+json; charset=UTF-8
  << HTTP/1.1 201 Created (Response Time: 65ms)
  << Location: https://fhir-gateway.hospital-network.org/r4/Bundle/bundle-iomt-ESP32-5567
  [SUCCESS] Saved verified FHIR bundle JSON to: simulated-fhir-bundle.json
```

---

## 🧠 Future Hardware Roadmap

This software pipeline is architected to transition seamlessly to physical hardware. In a physical implementation:
1.  The `PhysiologicalSensor` class is replaced by a physical **MAX30102 PPG sensor** connected to an **ESP32 microcontroller** via I2C wires.
2.  The ESP32 runs a local firmware script (C++ or MicroPython) to read the sensor registries and transmit lightweight JSON via Wi-Fi.
3.  The `FHIRMiddleware` script is hosted as a lightweight gateway receiver (using Flask or FastAPI) on a local server, transforming the physical ESP32 Wi-Fi packets into HL7 FHIR bundles in real-time.
