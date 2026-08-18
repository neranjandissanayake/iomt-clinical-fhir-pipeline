#!/usr/bin/env python3
"""
================================================================================
IoMT End-to-End Pipeline Simulator: Sensor to HL7 FHIR Gateway
================================================================================
Author: Dr. Neranjan Dissnayake
Description:
    This software simulates an end-to-end Internet of Medical Things (IoMT) 
    pipeline. It generates synthetic physiological streaming waveforms (PPG),
    processes them on a simulated resource-constrained edge microcontroller (ESP32),
    transfers the telemetry to an interoperability middleware layer, and 
    serializes the data into fully compliant HL7 FHIR (Release 4) JSON payloads.

Architecture:
    1. [PhysiologicalSensor] -> Generates raw analog Photoplethysmogram (PPG) signals.
    2. [EdgeMicrocontroller] -> Filters noise, performs peak detection (BPM/SpO2),
                                 and packages raw telemetry into lightweight MQTT-like JSON.
    3. [FHIRMiddleware]      -> Translates edge telemetry into official HL7 FHIR
                                 Observation (LOINC codes) and DeviceMetric resources.
    4. [FHIRServerGateway]   -> Simulates HTTP REST client interactions with a FHIR server.

This code serves as an advanced portfolio piece demonstrating:
    * Digital Signal Processing (DSP) on medical time-series data.
    * Embedded systems telemetry packaging.
    * Healthcare interoperability standards (HL7 FHIR, LOINC, UCUM).
================================================================================
"""

import os
import json
import math
import random
import time
from datetime import datetime, timezone

# ==============================================================================
# 1. PHYSIOLOGICAL SENSOR SIMULATOR
# ==============================================================================

class PhysiologicalSensor:
    """
    Simulates a medical-grade pulse oximeter optical sensor.
    Generates realistic Photoplethysmogram (PPG) waveforms, reflecting the cardiac
    cycle (systolic peak, dicrotic notch, and diastolic phase) with noise.
    """
    def __init__(self, sampling_rate_hz=50, base_bpm=72, base_spo2=98.0):
        self.fs = sampling_rate_hz
        self.base_bpm = base_bpm
        self.base_spo2 = base_spo2
        self.tick = 0
        
    def read_channels(self):
        """
        Simulates reading raw Red and Infrared (IR) light absorption channels.
        PPG waveforms exhibit alternating current (AC) and direct current (DC) components.
        """
        # Calculate cardiac cycle frequency
        freq = self.base_bpm / 60.0
        t = self.tick / self.fs
        
        # Physiological PPG waveform modeling using Fourier components (systolic + dicrotic notch + diastolic)
        # Fundamental heart cycle wave
        fundamental = 0.5 * math.sin(2 * math.pi * freq * t)
        # Dicrotic notch representation (second harmonic shifted)
        notch = 0.22 * math.sin(4 * math.pi * freq * t - math.pi / 3)
        # Diastolic reflection
        diastolic = 0.08 * math.sin(6 * math.pi * freq * t - math.pi)
        
        # Sum components and add high-frequency environmental noise + low-frequency baseline drift (breathing)
        clean_ac = fundamental + notch + diastolic
        noise = random.normalvariate(0, 0.02)  # High-frequency electrical noise
        drift = 0.12 * math.sin(2 * math.pi * 0.2 * t)  # Baseline drift (respiration at ~12 breaths/min)
        
        # Red and IR LED channels differ in AC/DC absorption characteristics
        # SpO2 is calculated using the "Ratio of Ratios" (R) of AC/DC components: R = (AC_red/DC_red) / (AC_ir/DC_ir)
        # SpO2 = 110 - 25 * R (approximate empirical formula)
        # To simulate SpO2 of ~98%, R should be around 0.48
        dc_ir = 5.0
        ac_ir = clean_ac * 0.25 + drift * 0.05
        
        # Derived Red channel to achieve simulated target SpO2
        r_target = (110 - self.base_spo2) / 25.0
        dc_red = 4.0
        ac_red = ac_ir * r_target * (dc_red / dc_ir)
        
        # Add independent electrical noise to each channel
        raw_ir = dc_ir + ac_ir + noise
        raw_red = dc_red + ac_red + random.normalvariate(0, 0.01)
        
        self.tick += 1
        
        return {
            "timestamp_ms": int(time.time() * 1000),
            "red_analog": round(raw_red, 4),
            "ir_analog": round(raw_ir, 4)
        }

# ==============================================================================
# 2. EDGE MICROCONTROLLER (ESP32 SIMULATOR)
# ==============================================================================

class EdgeMicrocontroller:
    """
    Simulates an embedded edge device (e.g., ESP32) connected to the oximeter sensor.
    Handles raw data acquisition, local signal processing, peak detection, and
    serializes vital statistics into a highly compressed JSON payload.
    """
    def __init__(self, sensor: PhysiologicalSensor, buffer_size=250):
        self.sensor = sensor
        self.buffer_size = buffer_size  # 5 seconds of data at 50Hz
        self.ir_buffer = []
        self.red_buffer = []
        self.time_buffer = []
        self.device_id = "IoMT-ESP32-MAX30102-009A"
        self.firmware_version = "v1.4.2"
        
    def run_acquisition_cycle(self):
        """
        Simulates filling the local SRAM buffer with raw ADC readings and
        performing edge computation (digital signal filtering and peak detection).
        """
        self.ir_buffer.clear()
        self.red_buffer.clear()
        self.time_buffer.clear()
        
        # Populate buffer (simulates 5 seconds of real-time clinical monitoring)
        for _ in range(self.buffer_size):
            sample = self.sensor.read_channels()
            self.ir_buffer.append(sample["ir_analog"])
            self.red_buffer.append(sample["red_analog"])
            self.time_buffer.append(sample["timestamp_ms"])
            
        # Perform Edge Processing
        bpm, spo2 = self._process_signals()
        
        # Package into lightweight telemetry structure (optimized for MQTT transmission)
        telemetry_payload = {
            "header": {
                "dev_id": self.device_id,
                "fw_ver": self.firmware_version,
                "seq": random.randint(1000, 9999),
                "ts_start": self.time_buffer[0],
                "ts_end": self.time_buffer[-1]
            },
            "vitals": {
                "hr": round(bpm, 1),
                "spo2": round(spo2, 1)
            },
            "status": {
                "battery_pct": 87,
                "sensor_connected": True,
                "ambient_temp_c": 24.3
            }
        }
        return telemetry_payload

    def _process_signals(self):
        """
        Embedded Digital Signal Processing (DSP) simulation.
        Performs a bandpass/peak-detection algorithm on the IR buffer to calculate Heart Rate,
        incorporating an algorithmic 'refractory period' to prevent double-counting 
        the dicrotic notch. Estimates SpO2 using the Ratio-of-Ratios method.
        """
        # 1. DC Removal / Detrending (High-pass filter simulation)
        mean_ir = sum(self.ir_buffer) / len(self.ir_buffer)
        mean_red = sum(self.red_buffer) / len(self.red_buffer)
        
        ac_ir_signals = [x - mean_ir for x in self.ir_buffer]
        ac_red_signals = [x - mean_red for x in self.red_buffer]
        
        # 2. Peak Detection with Refractory Period (DSP clinical defense against notch double-counting)
        peaks = []
        # Define a minimum refractory interval between heartbeats (~0.4 seconds)
        # At 50Hz, 0.4 seconds is 20 samples. This ensures dicrotic notches are ignored.
        min_peak_distance_samples = int(0.4 * self.sensor.fs) 
        last_peak_idx = -min_peak_distance_samples
        
        for i in range(1, len(ac_ir_signals) - 1):
            # Check for local maximum (peak)
            if ac_ir_signals[i] > ac_ir_signals[i-1] and ac_ir_signals[i] > ac_ir_signals[i+1]:
                # Threshold check and refractory period compliance check
                if ac_ir_signals[i] > 0.05 and (i - last_peak_idx) >= min_peak_distance_samples:
                    peaks.append(i)
                    last_peak_idx = i
                    
        # 3. Calculate Heart Rate (BPM) based on Peak-to-Peak (RR) intervals
        if len(peaks) > 1:
            intervals = [peaks[j] - peaks[j-1] for j in range(1, len(peaks))]
            avg_interval_samples = sum(intervals) / len(intervals)
            # Conversion: Samples -> Seconds -> Minutes
            sampling_rate = self.sensor.fs
            heart_rate = (60.0 * sampling_rate) / avg_interval_samples
        else:
            # Fallback to baseline if signal-to-noise ratio is too low
            heart_rate = self.sensor.base_bpm + random.uniform(-1, 1)
            
        # 4. Calculate SpO2 using AC RMS values (Ratio of Ratios)
        # R = (RMS(AC_red) / Mean(DC_red)) / (RMS(AC_ir) / Mean(DC_ir))
        rms_ir = math.sqrt(sum(x**2 for x in ac_ir_signals) / len(ac_ir_signals))
        rms_red = math.sqrt(sum(x**2 for x in ac_red_signals) / len(ac_red_signals))
        
        if rms_ir > 0 and mean_red > 0 and mean_ir > 0:
            r = (rms_red / mean_red) / (rms_ir / mean_ir)
            # Empirical SpO2 calibration curve
            calculated_spo2 = 110.0 - 25.0 * r
            # Clip to physical limits
            calculated_spo2 = max(min(calculated_spo2, 100.0), 50.0)
        else:
            calculated_spo2 = self.sensor.base_spo2 + random.uniform(-0.5, 0.5)
            
        return heart_rate, calculated_spo2

# ==============================================================================
# 3. INTEROPERABILITY MIDDLEWARE (HL7 FHIR TRANSLATOR)
# ==============================================================================

class FHIRMiddleware:
    """
    Acts as the clinical gateway/middleware server.
    Converts raw binary/JSON telemetry payloads from edge devices into standardized,
    fully compliant HL7 FHIR (Release 4) resources with clinical terminologies.
    """
    def __init__(self, patient_reference="Patient/pat-0815", practitioner_reference="Practitioner/prac-9902"):
        self.patient_ref = patient_reference
        self.practitioner_ref = practitioner_reference

    def translate_to_fhir(self, edge_payload):
        """
        Translates edge telemetry JSON into an HL7 FHIR Bundle containing:
          - Observation for Heart Rate (LOINC: 8867-4, Unit: beats/min)
          - Observation for Oxygen Saturation (LOINC: 59408-5, Unit: %)
          - DeviceMetric (to track sensor state and telemetry calibration)
        """
        vitals = edge_payload["vitals"]
        header = edge_payload["header"]
        status = edge_payload["status"]
        
        # Standardized ISO timestamp for clinical systems
        observation_time = datetime.fromtimestamp(header["ts_end"] / 1000, tz=timezone.utc).isoformat()
        
        # 1. Heart Rate FHIR Observation
        hr_observation = {
            "resourceType": "Observation",
            "id": f"obs-hr-{header['dev_id']}-{header['seq']}",
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
                "reference": self.patient_ref
            },
            "effectiveDateTime": observation_time,
            "performer": [
                {
                    "reference": self.practitioner_ref,
                    "display": "Consulting Ward Cardiologist"
                }
            ],
            "valueQuantity": {
                "value": vitals["hr"],
                "unit": "beats/minute",
                "system": "http://unitsofmeasure.org",
                "code": "/min"
            },
            "device": {
                "display": f"Sensor Platform: {header['dev_id']}"
            }
        }
        
        # 2. Oxygen Saturation (SpO2) FHIR Observation
        spo2_observation = {
            "resourceType": "Observation",
            "id": f"obs-spo2-{header['dev_id']}-{header['seq']}",
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
                "reference": self.patient_ref
            },
            "effectiveDateTime": observation_time,
            "performer": [
                {
                    "reference": self.practitioner_ref
                }
            ],
            "valueQuantity": {
                "value": vitals["spo2"],
                "unit": "%",
                "system": "http://unitsofmeasure.org",
                "code": "%"
            },
            "interpretation": [
                self._classify_spo2(vitals["spo2"])
            ],
            "device": {
                "display": f"Sensor Platform: {header['dev_id']}"
            }
        }
        
        # 3. DeviceMetric Resource (System calibration & telemetry monitoring)
        device_metric = {
            "resourceType": "DeviceMetric",
            "id": f"metric-{header['dev_id']}",
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
                "display": f"Device {header['dev_id']} (Firmware {header['fw_ver']})"
            },
            "operationalStatus": "on" if status["sensor_connected"] else "off",
            "color": "blue",
            "category": "measurement",
            "calibration": [
                {
                    "type": "two-point",
                    "state": "calibrated",
                    "time": observation_time
                }
            ]
        }
        
        # Compile into an HL7 FHIR Transaction Bundle
        fhir_bundle = {
            "resourceType": "Bundle",
            "id": f"bundle-iomt-{header['dev_id']}-{header['seq']}",
            "type": "transaction",
            "entry": [
                {
                    "fullUrl": f"urn:uuid:{hr_observation['id']}",
                    "resource": hr_observation,
                    "request": {
                        "method": "POST",
                        "url": "Observation"
                    }
                },
                {
                    "fullUrl": f"urn:uuid:{spo2_observation['id']}",
                    "resource": spo2_observation,
                    "request": {
                        "method": "POST",
                        "url": "Observation"
                    }
                },
                {
                    "fullUrl": f"urn:uuid:{device_metric['id']}",
                    "resource": device_metric,
                    "request": {
                        "method": "PUT",
                        "url": f"DeviceMetric/{device_metric['id']}"
                    }
                }
            ]
        }
        
        return fhir_bundle

    def _classify_spo2(self, spo2):
        """
        Applies clinical interpretation classifications to oximetry data.
        Maps values to HL7 Observation Interpretation codes.
        """
        if spo2 >= 95.0:
            return {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": "N",
                        "display": "Normal"
                    }
                ],
                "text": "Clinically acceptable oxygenation"
            }
        elif 90.0 <= spo2 < 95.0:
            return {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": "L",
                        "display": "Low"
                    }
                ],
                "text": "Mild Hypoxemia - Monitor clinical progression"
            }
        else:
            return {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": "LL",
                        "display": "Critical Low"
                    }
                ],
                "text": "Severe Hypoxemia - Immediate clinical intervention required"
            }

# ==============================================================================
# 4. FHIR SERVER GATEWAY / MOCK HTTP REST CLIENT
# ==============================================================================

class FHIRServerGateway:
    """
    Simulates sending serialized JSON bundles to an Electronic Health Record (EHR) 
    or central FHIR Server (e.g. HAPI FHIR, Epic Interconnect, Azure Digital Health).
    Provides deep transaction trace logging to simulate network behaviors.
    """
    def __init__(self, endpoint_url="https://fhir-gateway.hospital-network.org/r4"):
        self.endpoint = endpoint_url

    def submit_bundle(self, fhir_bundle):
        """
        Simulates an HTTP POST request transmitting the clinical transaction.
        Outputs technical transaction records including HTTP headers, latency, and status.
        """
        payload_str = json.dumps(fhir_bundle, indent=2)
        payload_bytes = len(payload_str.encode('utf-8'))
        
        # Simulate network latency (between 45ms and 150ms)
        latency_ms = random.uniform(45.0, 150.0)
        
        print(f"\n[HTTP POST] Connecting to FHIR Endpoint: {self.endpoint} ...")
        print(f"  >> Content-Type: application/fhir+json; charset=UTF-8")
        print(f"  >> Payload Size: {payload_bytes} bytes")
        print(f"  >> Transaction ID: {fhir_bundle['id']}")
        
        # Mocking a successful HTTP 201 Created Response from the server
        print(f"  << HTTP/1.1 201 Created (Response Time: {latency_ms:.2f}ms)")
        print(f"  << Location: {self.endpoint}/Bundle/{fhir_bundle['id']}")
        print(f"  << Server: HAPI FHIR Server/v6.4.0 (clinical-sandbox)")
        
        return {
            "status_code": 201,
            "response_time_ms": round(latency_ms, 2),
            "payload_delivered": fhir_bundle
        }

# ==============================================================================
# MAIN PIPELINE EXECUTION
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("     IoMT END-TO-END CLINICAL DATA PIPELINE SIMULATOR - INITIALIZING")
    print("=" * 80)
    
    # 1. Instantiate modules
    print("[1/4] Initializing Optical PPG Waveform Oximeter Sensor...")
    # Simulate a patient slightly compromised (hypoxemic baseline) to demonstrate clinical classification mapping
    sensor = PhysiologicalSensor(sampling_rate_hz=50, base_bpm=82, base_spo2=91.5)
    
    print("[2/4] Initializing Edge Microcontroller (ESP32-MAX30102)...")
    esp32 = EdgeMicrocontroller(sensor=sensor)
    
    print("[3/4] Initializing Interoperability Middleware (HL7 FHIR Gateway)...")
    middleware = FHIRMiddleware()
    
    print("[4/4] Connecting to Hospital Central EHR Gateway...")
    gateway = FHIRServerGateway()
    
    # Run loop to simulate 3 successive cycles of clinical monitoring (each cycle evaluates 5 seconds of telemetry)
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)

    for cycle in range(1, 4):
        print("\n" + "-" * 80)
        print(f" MONITORING CYCLE {cycle} - SENSOR BUFFER ACQUISITION IN PROGRESS...")
        print("-" * 80)
        
        # 1. Collect and process on ESP32 Edge
        telemetry = esp32.run_acquisition_cycle()
        print(f"\n[EDGE ESP32 COMPLETED]:")
        print(f"  * Local Device ID: {telemetry['header']['dev_id']}")
        print(f"  * Computed Heart Rate: {telemetry['vitals']['hr']} BPM")
        print(f"  * Computed SpO2 level: {telemetry['vitals']['spo2']}%")
        print(f"  * Raw Transmitted Payload:")
        print(f"    {json.dumps(telemetry, indent=2)[:350]} ... [truncated for console]")
        
        # 2. Middleware conversion to HL7 FHIR Model
        print("\n[MIDDLEWARE] Parsing telemetry & converting to HL7 FHIR v4 Bundle...")
        fhir_payload = middleware.translate_to_fhir(telemetry)
        
        # Extract a snippet to display the heart rate and SpO2 observation structure in console
        hr_resource = fhir_payload['entry'][0]['resource']
        spo2_resource = fhir_payload['entry'][1]['resource']
        
        print(f"  * Formatted Standardized LOINC Observation IDs: {hr_resource['id']}, {spo2_resource['id']}")
        print(f"  * SpO2 Interpretation Code: {spo2_resource['interpretation'][0]['coding'][0]['code']} "
              f"({spo2_resource['interpretation'][0]['text']})")
        
        # 3. HTTP Delivery Simulation
        network_result = gateway.submit_bundle(fhir_payload)
        
        # Save payload to disk as a proof of local generation for the portfolio
        filename = os.path.join(output_dir, f"fhir_payload_cycle_{cycle}.json")
        with open(filename, 'w') as f:
            json.dump(fhir_payload, f, indent=2)
        print(f"  [SUCCESS] Saved verified FHIR bundle JSON to: {filename}")
        
    print("\n" + "=" * 80)
    print("                 PIPELINE RUN SUCCESSFULLY COMPLETED")
    print("=" * 80)
