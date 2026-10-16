# Historical Signature Grant narrative

This document preserves the original 2026 proposal and purchase list. For the October 16 expanded plan, use [the research plan](docs/research_plan.md), [hardware/funding](docs/hardware_and_funding.md), and [implementation guide](docs/implementation_guide.md). The original NVIDIA list and historical prices are not the current AMD purchase quote. Local hosting is not automatically an air-gap or a complete security solution, and this study measures operational electricity rather than deriving a complete carbon footprint.

---

# Tab 1

### **Document 1: Biography / Artist Statement**

I am an undergraduate student at the University of Arkansas at Little Rock studying Computer Science / Cybersecurity. My academic and professional work focuses on the intersection of cybersecurity, artificial intelligence, and systems administration. Recently, I have been building offline research intelligence platforms and developing tools for the behavioral analysis of ransomware. I also actively participate in Capture The Flag (CTF) competitions, focusing on digital forensics, steganography, and cryptographic decoding.

My technical skill set includes Python, C++, Linux server configuration, and deploying local large language models (LLMs). After graduation, I plan to pursue a career in security infrastructure, building resilient systems that protect sensitive data while integrating modern machine learning capabilities. This Signature Experience project directly aligns with my goal of engineering computing solutions that are both technologically advanced and securely isolated.

### **Document 2: Project Description (Part 1 & 2\)**

**Part 1 – Project Goals / Purpose** As large language models (LLMs) are increasingly integrated into enterprise workflows, organisations face significant data privacy risks. Sending proprietary information or sensitive code to third-party cloud providers creates vulnerabilities regarding provider-side breaches and opaque data retention policies. Running these models locally acts as a physical air-gap, ensuring data sovereignty by keeping all processing on internal hardware.

The primary goal of this project is to quantify the operational cost of that privacy. While local inference solves the security problem, it shifts the power consumption burden from hyper-scale data centres to local hardware. This project will establish a measurable framework comparing the energy efficiency of local LLM inference against cloud-based APIs. By calculating the exact joules-per-token required to run models locally, and benchmarking that against the reported carbon metrics of cloud providers, I aim to provide a clear, data-driven analysis of the trade-offs between strict data sovereignty and energy consumption.

**Part 2 – Materials / Methods** The methodology relies on building a local test bench designed to capture exact hardware-level power telemetry. Every component was selected to eliminate variables that could skew the power metrics.

The primary engine is an NVIDIA RTX 5060 Ti (16GB VRAM). This specific memory capacity allows quantized 8-billion parameter models to run entirely in video memory, preventing power-draining data offloads to slower system RAM. An AMD Ryzen 9 5900XT CPU ensures background system processes do not bottleneck the inference pipeline. Because thermal throttling drastically alters a processor's power consumption, a dedicated liquid CPU cooler and high-airflow case fans are required to maintain a consistent temperature baseline during sustained testing. Finally, a hardware-level smart plug acts as the primary measurement instrument, logging exact wattage at the wall during both active generation and idle states.

I will run a standardized set of benchmark queries through locally hosted models, such as LLaMA 3, and record the energy consumed. I will then execute identical query payloads through commercial cloud APIs, extracting the attributable energy footprint from their telemetry dashboards. By triangulating the cloud data with published data centre overhead metrics, I can directly compare the energy cost of local data sovereignty against cloud infrastructure.

# Part List

PCPartPicker Part List: https://pcpartpicker.com/list/HptmCw

* CPU: AMD Ryzen 9 5900XT 3.3 GHz 16-Core Processor  ($281.29 @ Amazon)   
* CPU Cooler: Thermalright Aqua Elite V3 66.17 CFM Liquid CPU Cooler  ($33.89 @ Amazon)   
* Video Card: Asus DUAL OC GeForce RTX 5060 Ti 16 GB Video Card  ($564.00 @ Amazon)   
* Case Fan: Corsair RS120 72.8 CFM 120 mm Fans 3-Pack  ($29.99 @ Amazon)   
* Case Fan: Corsair RS120 72.8 CFM 120 mm Fans 3-Pack  ($29.99 @ Amazon)   
* Fan Controller: ARCTIC Case Fan Hub Fan Controller  ($14.61 @ Amazon)   
* Custom: Shelly Smart Plug UL, WiFi, Bluetooth, Zigbee, Matter Outlet with Power Metering, Works with HomeKit, Google Home, Alexa, Home Assistant, Smart Socket, Easy Setup, Remote Control, Plug US Gen  ($24.99 @ Amazon) 

Total: $978.76  
Prices include shipping, taxes, and discounts when available  
Generated by PCPartPicker 2026-07-08 10:33 EDT-0400  
