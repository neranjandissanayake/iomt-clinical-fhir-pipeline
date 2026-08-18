# IoMT Clinical FHIR Pipeline Simulator

This project models an end-to-end Internet of Medical Things (IoMT) monitoring pipeline that converts physiological sensor data into HL7 FHIR Release 4 resources suitable for transmission into a hospital or EHR integration layer. The simulator is designed to demonstrate how edge device telemetry, signal processing, and clinical interoperability standards can be combined in a single workflow.

## Clinical and technical architecture

The system follows a four-stage architecture:

1. Physiological sensor layer
2. Edge microcontroller layer
3. Interoperability middleware
4. FHIR server gateway

### 1. Physiological sensor layer

The `PhysiologicalSensor` class simulates a pulse oximeter using photoplethysmography (PPG). It models the red and infrared light channels captured by a wearable or bedside monitor. The waveform is built from a cardiac cycle signal with harmonic components that represent:

- systolic peaks
- dicrotic notch behavior
- diastolic reflection
- low-frequency drift from respiration
- sensor noise from electrical interference

This design is medically realistic because pulse oximetry depends on changes in optical absorption from arterial blood flow. The simulator produces time-series values for red and infrared analog signals, which are then used to estimate oxygenation and heart rate.

### 2. Edge microcontroller layer

The `EdgeMicrocontroller` class represents an embedded processing node such as an ESP32 running local signal analysis close to the patient. It collects a short buffer of sensor samples, removes baseline drift, and performs peak detection on the infrared waveform.

Key processing steps include:

- DC detrending of the PPG signal
- local maximum detection for heartbeats
- refractory period logic to avoid false double-counting from the dicrotic notch
- calculation of heart rate in beats per minute
- ratio-of-ratios estimation for oxygen saturation

This stage is important clinically because it keeps the device lightweight and reduces latency by processing at the edge before sending data upstream. In a real deployment, this is the sort of computation that would run on a battery-powered medical edge device with strict resource limits.

### 3. Interoperability middleware

The `FHIRMiddleware` class converts the device telemetry into HL7 FHIR Observation resources and a DeviceMetric resource. This translation layer ensures that raw device measurements are expressed using recognized clinical codes and units rather than custom JSON structures.

The generated resources map to medically standard concepts:

- Heart rate: LOINC 8867-4, unit beats/minute
- Oxygen saturation: LOINC 59408-5, unit %
- Observation interpretation: HL7 v3 interpretation codes for normal, low, and critical low values
- Device status: FHIR DeviceMetric resource for sensor connectivity and calibration

The simulated bundle is a `transaction` bundle, which is a standard FHIR pattern for sending multiple resources as a single clinical payload. Each entry includes a clinical resource plus an HTTP request specification, which mirrors how a real FHIR server would receive updates.

### 4. FHIR server gateway

The `FHIRServerGateway` simulates an HTTP client that sends the FHIR transaction bundle to a hospital or EHR integration endpoint. In the code, the result is modeled as a successful clinical request with a simulated `201 Created` response and an application/fhir+json payload. This models the final handoff from device and middleware into enterprise clinical systems.

## Standards implemented

The pipeline intentionally follows common medical interoperability conventions:

- HL7 FHIR Release 4
- LOINC for vital-sign coding
- UCUM units for quantity encoding
- ISO 8601 timestamps for clinical observation time
- FHIR transaction bundles for grouped data submission

This combination makes the output appropriate for interoperability with EHR, analytics, and clinical decision-support systems.

## Example generated FHIR bundle output

This output is taken from `simulated-fhir-bundle.json` and demonstrates the actual JSON produced by the simulator. It shows a valid medical transaction payload containing two critical observations and a device metric entry.

```json
{
  "resourceType": "Bundle",
  "id": "bundle-iomt-IoMT-ESP32-MAX30102-009A-9095",
  "type": "transaction",
  "entry": [
    {
      "fullUrl": "urn:uuid:obs-hr-IoMT-ESP32-MAX30102-009A-9095",
      "resource": {
        "resourceType": "Observation",
        "id": "obs-hr-IoMT-ESP32-MAX30102-009A-9095",
        "status": "final",
        "category": [
          {
            "coding": [
              {
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
              }
            ]
          }
        ],
        "code": {
          "coding": [
            {
              "system": "http://loinc.org",
              "code": "8867-4",
              "display": "Heart rate"
            }
          ],
          "text": "Heart Rate"
        },
        "subject": {
          "reference": "Patient/pat-0815"
        },
        "effectiveDateTime": "2026-08-18T18:48:38.473000+00:00",
        "performer": [
          {
            "reference": "Practitioner/prac-9902",
            "display": "Consulting Ward Cardiologist"
          }
        ],
        "valueQuantity": {
          "value": 81.8,
          "unit": "beats/minute",
          "system": "http://unitsofmeasure.org",
          "code": "/min"
        },
        "device": {
          "display": "Sensor Platform: IoMT-ESP32-MAX30102-009A"
        }
      },
      "request": {
        "method": "POST",
        "url": "Observation"
      }
    },
    {
      "fullUrl": "urn:uuid:obs-spo2-IoMT-ESP32-MAX30102-009A-9095",
      "resource": {
        "resourceType": "Observation",
        "id": "obs-spo2-IoMT-ESP32-MAX30102-009A-9095",
        "status": "final",
        "category": [
          {
            "coding": [
              {
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
              }
            ]
          }
        ],
        "code": {
          "coding": [
            {
              "system": "http://loinc.org",
              "code": "59408-5",
              "display": "Oxygen saturation in Arterial blood by Pulse oximetry"
            }
          ],
          "text": "Oxygen Saturation (SpO2)"
        },
        "subject": {
          "reference": "Patient/pat-0815"
        },
        "effectiveDateTime": "2026-08-18T18:48:38.473000+00:00",
        "performer": [
          {
            "reference": "Practitioner/prac-9902"
          }
        ],
        "valueQuantity": {
          "value": 91.5,
          "unit": "%",
          "system": "http://unitsofmeasure.org",
          "code": "%"
        },
        "interpretation": [
          {
            "coding": [
              {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "L",
                "display": "Low"
              }
            ],
            "text": "Mild Hypoxemia - Monitor clinical progression"
          }
        ],
        "device": {
          "display": "Sensor Platform: IoMT-ESP32-MAX30102-009A"
        }
      },
      "request": {
        "method": "POST",
        "url": "Observation"
      }
    },
    {
      "fullUrl": "urn:uuid:metric-IoMT-ESP32-MAX30102-009A",
      "resource": {
        "resourceType": "DeviceMetric",
        "id": "metric-IoMT-ESP32-MAX30102-009A",
        "type": {
          "coding": [
            {
              "system": "http://loinc.org",
              "code": "61016-2",
              "display": "Pulse oximeter sensor status"
            }
          ]
        },
        "unit": {
          "coding": [
            {
              "system": "http://unitsofmeasure.org",
              "code": "1",
              "display": "dimensionless"
            }
          ]
        },
        "source": {
          "display": "Device IoMT-ESP32-MAX30102-009A (Firmware v1.4.2)"
        },
        "operationalStatus": "on",
        "color": "blue",
        "category": "measurement",
        "calibration": [
          {
            "type": "two-point",
            "state": "calibrated",
            "time": "2026-08-18T18:48:38.473000+00:00"
          }
        ]
      },
      "request": {
        "method": "PUT",
        "url": "DeviceMetric/metric-IoMT-ESP32-MAX30102-009A"
      }
    }
  ]
}
```

This example confirms the simulator emits valid HL7 FHIR-style payloads with standard resource types, terminology-coded observations, and clinical timestamps. It is a strong demonstration of how IoMT biomedical sensor data can be transformed into interoperable medical data suitable for downstream EHR or analytics systems.

## Summary

The system demonstrates a realistic clinical data path from patient signal acquisition through edge processing and FHIR interoperability. It is useful for portfolio work, medical device prototyping, and educational demonstrations of how embedded monitoring data can be transformed into standards-based care records.
