<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:16A34A,50:0EA5E9,100:F59E0B&height=200&section=header&text=RenewStation&fontSize=60&fontColor=ffffff&fontAlignY=38&desc=AI-powered%20renewable%20energy%20forecasting%20and%20optimization&descAlignY=58&descSize=18" width="100%"/>

<!-- Competition -->
<p>
<img src="https://img.shields.io/badge/Huawei%20Developer%20Competition%20North%20Africa-4th%20Place%20Innovation%20Award-C7000B?style=for-the-badge&logo=huawei&logoColor=white"/>
</p>

</div>

<div align="center">

<!-- Skills -->
<p>
<img src="https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Apache%20Airflow-2.10-017CEE?style=flat-square&logo=apacheairflow&logoColor=white"/>
<img src="https://img.shields.io/badge/scikit--learn-RandomForest-F7931E?style=flat-square&logo=scikitlearn&logoColor=white"/>
<img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white"/>
<img src="https://img.shields.io/badge/Node.js-Express-339933?style=flat-square&logo=nodedotjs&logoColor=white"/>
<img src="https://img.shields.io/badge/React-Vite-61DAFB?style=flat-square&logo=react&logoColor=black"/>
<img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white"/>
</p>

</div>

<br>

### $\color{red}{\textbf{\textsf{⛔Usage Notice ⛔}}}$

> This project is **not licensed** and is **not intended for commercial use**. It is shared for **educational and portfolio purposes only**. You may read the code and learn from it, but you may not copy, redistribute or use it in commercial products without permission from the team.

<br>

## **$\color{#DC2626}{\textbf{\textsf{About}}}$** 

RenewStation was built by **Team NeoGen** for the **Huawei Developer Competition – Spark Infinity**, organized by **HCDG Northern Africa** (Egypt, remote, December 2025).

<div align="center">

| Member | Role | GitHub |
|---|---|---|
| **BENSBEH CHAIMAE** | Machine learning model training | [@YOUR_GITHUB](https://github.com/chaibs00) |
| **BJIBJI HAMZA** | ROLE | [@Bjibjihamza](https://github.com/Bjibjihamza) |
| **SGHIOUAR IMANE** | ROLE | [@GITHUB_3](https://github.com/imanesghiouar) |
| **EL AKRAMINE YASSIR SALIM** | ROLE | [@GITHUB_4](https://github.com/SalimYs) |
| **ECHAHLAOUI YOUSSEF** | ROLE | [@GITHUB_5](https://github.com/Yussef31) |

</div>


<div align="center">
<a href="https://www.youtube.com/watch?v=DmIECEjYKoY">
<img src="./docs/first.png" width="75%" alt="RenewStation demo video"/>
</a>
<br/>
<sub>Click the image to watch the demo on YouTube</sub>
</div>


<br>

## $\color{#EA580C}{\textbf{\textsf{Problem Definition}}}$

Today, the challenge is no longer just generating renewable energy, but `managing its unpredictability` and `balancing production with energy demand`.

For instance, **Solar energy production** depends on sunlight and weather conditions, while consumption varies with people's needs, buildings activity. This mismatch makes it difficult to plan energy usage in advance.

Without accurate forecasting, operators cannot anticipate :
- when the batteries will run empty ?
- how much energy must be bought from the grid ?
- when surplus solar energy will be wasted ?



<br>

## $\color{#16A34A}{\textbf{\textsf{Overview}}}$

**RenewStation** is an **AI-powered platform for renewable energy optimization**. It **monitors**, **forecasts** and **plans** the energy of a district powered by solar panels and batteries, so operators know in advance how much energy will be **consumed**, **produced** and **stored** over the next **`7 days`**.

The platform combines **real weather data**, a **machine learning model** for consumption, a **physical model** for solar production and a **battery simulation**. 


### $\color{orange}{\textsf{Simulation Setup}}$

For the competition, we built a **simulation of a smart-city district in Casablanca, Morocco**: **`17 virtual buildings`** powered by a **`800 kWp`** solar station with battery storage and connected to the grid. The buildings' consumption is **simulated** from their type, equipment and occupancy, combined with **real weather data**, to reproduce how a real district behaves.

<div align="center">
<img src="./docs/Overview.png" width="95%" alt="RenewStation district overview"/>

<br>

| Component | Details |
|---|---|
| **Buildings** | 17 buildings: 1 hospital, 10 houses, 3 offices, 2 industrial sites, 1 school |
| **Solar station** | 800 kWp: 1,455 panels of 550 W, 3,754 m², 22.5% module efficiency |
| **Storage** | Main battery 3,000 kWh + backup battery 1,000 kWh |
| **Grid** | Imports when solar and batteries fall short, exports surplus |

</div>


### $\color{orange}{\textsf{Daily Workflow}}$

Every day at midnight, the platform:

1. Pulls **real weather data** and a **7-day forecast**.
2. Forecasts the **hourly energy consumption** of each building for the next **`168 hours`**.
3. Estimates **solar production** from the weather forecast with a physical PV model.
4. Simulates the **battery state of charge** and **grid import/export** hour by hour.
5. Updates the **live dashboard** with all forecasts.

<br>


## $\color{#16A34A}{\textbf{\textsf{System Architecture}}}$

<div align="center">

<img src="./docs/A2.jpeg" width="95%" alt="System Architecture"/>

<br>

| Component | Role |
|---|---|
| **Airflow** | Orchestrates ingestion, simulation, training and daily predictions |
| **PostgreSQL** | Stores history, live data and 7-day predictions (silver layer) |
| **Node.js API** | Read-only REST API serving the dashboard |
| **React dashboard** | Visualizes consumption, production, battery state and weather |
| **Huawei Cloud (design)** | Designed for ECS, GaussDB and OBS; runs locally with Docker Compose |

</div>



<br>

## $\color{#16A34A}{\textbf{\textsf{Data}}}$

> ⛔
> For **privacy and confidentiality** reasons, **no real-world consumption data** was used in this project. Real data reveals sensitive information about people and buildings (presence, habits, activity), so it could not be shared during the competition.
>
> Instead, **synthetic data** was generated to reproduce how a real district behaves. The **only real data** is the **weather** from **`Open-Meteo`**, and it drives the simulation. All results should be read with this in mind.

### $\color{orange}{\textsf{Data Flow}}$

<div align="center">
<img src="./docs/data_flow.png" width="95%" alt="RenewStation data flow"/>
</div>

<br>

<div align="center">

| Source | Type | Description |
|---|---|---|
| **Weather** | `Real` | Hourly temperature, humidity, cloud cover and solar radiation from [Open-Meteo](https://open-meteo.com/) for Casablanca |
| **Building consumption** | `Synthetic` | Hourly load per building, generated from building type, equipment (HVAC, lighting, special equipment), occupancy, holidays and real weather |
| **Solar production** | `Computed` | Physical PV model: radiation, panel area, efficiency, temperature losses, inverter efficiency |
| **Battery state** | `Simulated` | Hour-by-hour charge and discharge with capacity and power limits |

**Dataset size:** about **`278,000` hourly records** (`17` buildings × hourly data since January 2024).

</div>


<br>

## $\color{#16A34A}{\textbf{\textsf{Forecasting}}}$



<div align="center">

| Task | Target |
|---|---|
| **Consumption forecasting** | Energy consumed by each of the `17` buildings (kW) | 
| **Production forecasting** | Energy produced by the `800 kWp` solar station (kWh) | 

</div>

<br>

### $\color{orange}{\textsf{Consumption Forecasting}}$

<div align="center">

| | |
|---|---|
| **Model** | `RandomForestRegressor` (500 trees), `scikit-learn` pipeline |
| **Weather features** | Temperature, humidity, cloud cover, solar radiation |
| **Time features** | Hour, day of week, month, day of year, weekend, holiday, peak hour, season |
| **Building feature** | Building name (one-hot encoded) |
| **Preprocessing** | `StandardScaler` on numeric features, `OneHotEncoder` on building |
| **Retraining** | Daily, through the `retrain_model` Airflow DAG |

</div>

<br>

### $\color{orange}{\textsf{Production Forecasting}}$

Solar output is computed directly from the **7-day weather forecast** :

<div align="center">

| | |
|---|---|
| **Input** | Forecast solar radiation (W/m²) and temperature |
| **Panels** | `3,754 m²`, `22.5%` module efficiency, `800 kWp` peak |
| **Losses** | Cell temperature (NOCT `45°C`, `-0.4%/°C`), inverter efficiency `97%` |
| **Output** | Hourly production (kWh), capped at peak power |

</div>


<br>

## $\color{#16A34A}{\textbf{\textsf{Results}}}$

Results of the consumption model, as presented at the competition:

<div align="center">

| Metric | Value |
|---|---|
| **MAE** | `0.149 kW` |
| **RMSE** | `0.285 kW` |
| **R²** | `0.998` |
| **Training data** | `~278,000` hourly records, `17` buildings |
| **Split** | Random 80/20 train/test |

</div>

### $\color{orange}{\textsf{Interpretation}}$

- **MAE `0.149 kW`:** on average, each hourly prediction is off by about **150 W**, roughly the consumption of **a few light bulbs**. That's small next to buildings that consume several kW per hour.
- **RMSE `0.285 kW`:** RMSE is about **twice the MAE**, so most errors are small but a few hours have **larger errors**, most likely during **consumption peaks** (sudden HVAC or industrial loads).
- **R² `0.998`:** the model explains **99.8%** of the variation in consumption. It has learned the main patterns well: **daily cycles**, **weekends and holidays**, **building type** and the **effect of the weather**.

<br>


## $\color{#0284C7}{\textsf{Pipelines}}$

<div align="center">

| DAG | Schedule | What it does |
|---|---|---|
| `initialization` | Manual, run once | Loads weather history, generates consumption history, sets batteries to 100% |
| `daily_prediction` | Daily, 00:00 | Archives yesterday, updates real battery state, fetches 7-day weather, predicts consumption, solar and battery for 7 days |
| `retrain_model` | Daily, 00:00 | Retrains the consumption model on the latest data |

</div>


<br>



## $\color{red}{\textbf{\textsf{Credits}}}$

All credit goes to **Team NeoGen**, who designed and built RenewStation for the **Huawei Developer Competition – Spark Infinity** (HCDG Northern Africa, 2025), where it won the **4th place Innovation Award**. 

- **Weather data:** [Open-Meteo](https://open-meteo.com/)


<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:F59E0B,50:0EA5E9,100:16A34A&height=100&section=footer" width="100%"/>
</div>