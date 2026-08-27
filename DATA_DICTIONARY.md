# 📖 Enterprise Data Dictionary & Data Contract Specification

This document defines the formal data contract, schema definitions, validation constraints, and Power BI semantic layer definitions for **Apex BI Studio**.

---

## 1. 📋 Telemetry Data Contract Schema

All incoming telemetry dataset streams (CSV, Excel, JSON API) are standardized against the following strict contract schema prior to ingestion:

| Attribute Key | Canonical Display Name | Data Type | Base SI Unit | Valid Range Bounds | Null Imputation | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Timestamp [Sec]` | Time Vector | `float64` | `Seconds (s)` | $[0.0, \infty)$ | Forward-fill | Relative execution timestamp vector for telemetry sample. |
| `Rectified Power [W]` | Rectified Power | `float64` | `Watts (W)` | $[0.0, 100.0]$ | `0.0` | Output DC rectified power measurement. |
| `Received Power [W]` | Received Power | `float64` | `Watts (W)` | $[0.0, 100.0]$ | `0.0` | Input RF received power measurement. |
| `PFO [mW]` | PFO Metric | `float64` | `Milliwatts (mW)` | $[0.0, 1000.0]$ | `0.0` | Peak Power Offset metric. |
| `Board` | Asset / Board | `string` | N/A | Text | `'N/A'` | Identifier for hardware test board under test. |
| `DUT` | Device Under Test | `string` | N/A | Text | `'N/A'` | Specific silicon device instance identifier. |
| `RUN` | Execution Run | `string` | N/A | Text | `'N/A'` | Automated test suite execution run ID. |
| `CRX` | Receiver Channel | `string` | N/A | Text | `'N/A'` | Channel receiver instance identifier. |
| `Position` | Spatial Position | `string` | N/A | Text | `'N/A'` | Physical position index on test fixture. |
| `PowerMode` | Power Mode | `string` | N/A | Categorical | `'Nominal'` | Operating state (`Active`, `Nominal`, `LowPower`). |
| `Power` | Nominal Power State | `string` | N/A | Categorical | `'Online'` | Board power status (`Online`, `Offline`, `Standby`). |
| `_is_outlier` | Anomaly Flag | `boolean` | N/A | `{True, False}` | `False` | Outlier detection flag assigned by IQR / Z-Score engine. |

---

## 2. 📊 Power BI Semantic Layer (DAX Formulations)

The following calculated measures are defined in the backend analytical service layer and exposed directly for Power BI report consumption:

### ⚡ Average Rectified Power
```dax
AvgRectifiedPower = AVERAGE('Telemetry'[Rectified Power [W]])
```

### 📈 Peak PFO Metric
```dax
MaxPFO = MAX('Telemetry'[PFO [mW]])
```

### ⚠️ Total Outlier Count
```dax
OutlierCount = COUNTROWS(FILTER('Telemetry', 'Telemetry'[_is_outlier] = TRUE()))
```

### 📊 Anomaly Rate Percentage
```dax
AnomalyRate = DIVIDE([OutlierCount], COUNTROWS('Telemetry'), 0) * 100
```

---

## 3. 🛡️ Data Quality & Outlier Rules

- **IQR Rule**: Points exceeding $Q3 + 1.5 \times \text{IQR}$ or below $Q1 - 1.5 \times \text{IQR}$ are flagged as outliers.
- **Z-Score Rule**: Points with $|Z| > 3.0$ standard deviations are marked for validation.
- **Modified MAD**: Median Absolute Deviation rule for non-normally distributed telemetry clusters.
